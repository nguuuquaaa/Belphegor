import discord
from discord.ext import commands
from belphegor.utils import token, config, checks
import asyncio
import aiohttp
import psutil
import os
import time

class Belphegor(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.process = psutil.Process(os.getpid())
        self.cpu_count = psutil.cpu_count()
        self.process.cpu_percent(None)
        self.start_time = time.time()
        self.loop.create_task(self.load())
        self.block_users = []

    async def on_message(self, message):
        if message.author.bot:
            return
        elif not self.block_users:
            if message.author.id in self.block_users:
                return
        await self.process_commands(message)

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')
        await asyncio.sleep(5)
        await self.change_presence(game=discord.Game(name='with Chronos-senpai'))

    async def close(self):
        await super().close()
        await self.session.close()

    async def load(self):
        await self.wait_until_ready()
        with open("extensions.txt") as file:
            extensions = [e for e in file.read().strip().splitlines()]
        for extension in extensions:
            try:
                self.load_extension(extension)
                print(f"Loaded {extension}")
            except Exception as e:
                print(f"Failed loading {extension}: {e}")
                return await self.logout()
        print("Done")

if __name__ == "__main__":
    belphegor = Belphegor(command_prefix=commands.when_mentioned_or("!!", ">>", "b>"), owner_id=config.owner_id)
    belphegor.run(token.token)
