import discord
from discord.ext import commands
from belphegor import utils
from belphegor.utils import token, config, context
import asyncio
import aiohttp
import psutil
import os
import time
from motor import motor_asyncio

#==================================================================================================================================================

class Belphegor(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(None, **kwargs)
        self.default_prefix = kwargs.get("default_prefix", (">>",))
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.process = psutil.Process(os.getpid())
        self.cpu_count = psutil.cpu_count()
        self.process.cpu_percent(None)
        self.start_time = utils.now_time()
        self.loop.create_task(self.load())
        self.mongo_client = motor_asyncio.AsyncIOMotorClient()
        self.db = self.mongo_client.belphydb

    async def get_prefix(self, message):
        prefixes = {f"<@{self.user.id}> ", f"<@!{self.user.id}> "}
        guild_prefixes = self.default_prefix
        if message.guild:
            prefix_data = await self.db.guild_data.find_one({"guild_id": message.guild.id}, projection={"_id": -1, "prefixes": 1})
            if prefix_data:
                guild_prefixes = prefix_data.get("prefixes", guild_prefixes)
        prefixes.update(guild_prefixes)
        return prefixes

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.BelphegorContext)
        await self.invoke(ctx)

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')
        await asyncio.sleep(5)
        await self.change_presence(game=discord.Game(name='with Chronos-senpai'))

    def remove_cog(self, name):
        cog = self.get_cog(name)
        try:
            cog.cleanup()
        except:
            pass
        super().remove_cog(name)

    async def close(self):
        await self.session.close()
        await super().close()

    async def load(self):
        await self.wait_until_ready()
        for extension in config.all_extensions:
            try:
                self.load_extension(extension)
                print(f"Loaded {extension}")
            except Exception as e:
                print(f"Failed loading {extension}: {e}")
                return await self.logout()
        print("Done")

#==================================================================================================================================================

if __name__ == "__main__":
    belphybot = Belphegor(owner_id=config.OWNER_ID)
    belphybot.run(token.TOKEN)
