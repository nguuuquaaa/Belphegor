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
import sys
import traceback

#==================================================================================================================================================

EMPTY_SET = set()

#==================================================================================================================================================

class Belphegor(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(None, **kwargs)
        self.default_prefix = kwargs.get("default_prefix", (">>",))
        self.guild_prefixes = {}
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.process = psutil.Process(os.getpid())
        self.cpu_count = psutil.cpu_count()
        self.process.cpu_percent(None)
        self.start_time = utils.now_time()
        self.loop.create_task(self.load())
        self.mongo_client = motor_asyncio.AsyncIOMotorClient()
        self.db = self.mongo_client.belphydb
        self.counter = 0

    async def get_prefix(self, message):
        prefixes = {f"<@{self.user.id}> ", f"<@!{self.user.id}> "}
        if message.guild:
            gp = self.guild_prefixes.get(message.guild.id)
        else:
            gp = None
        if gp:
            prefixes.update(gp)
        else:
            prefixes.update(self.default_prefix)
        return prefixes

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.BelphegorContext)
        await self.invoke(ctx)

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        if self.extra_events.get('on_command_error', None):
            return
        if hasattr(ctx.command, 'on_error'):
            return
        cog = ctx.cog
        if cog:
            attr = f"_{cog.__class__.__name__}__error"
            if hasattr(cog, attr):
                return

        print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
        if isinstance(error, (commands.CheckFailure, commands.CommandOnCooldown, commands.BadArgument, commands.MissingRequiredArgument, commands.BotMissingPermissions)):
            print(f"{type(error).__module__}.{type(error).__name__}: {error}", file=sys.stderr)
        else:
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        if not isinstance(error, (commands.CheckFailure, commands.CommandOnCooldown, commands.CommandNotFound)):
            try:
                await ctx.deny()
            except:
                pass

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

    def create_task_and_count(self, coro):
        async def do_stuff():
            self.counter += 1
            await coro
            self.counter -= 1
        self.loop.create_task(do_stuff())

    async def do_after(self, coro, wait_time):
        await asyncio.sleep(wait_time)
        try:
            await coro
        except:
            pass

    async def logout(self):
        await self.session.close()
        await super().logout()
        print("Logging out...")
        while self.counter > 0:
            await asyncio.sleep(0.1)

    async def block_or_not(self, ctx):
        author_id = ctx.author.id
        channel_id = getattr(ctx.channel, "id", None)
        guild_id = getattr(ctx.guild, "id", None)

        bot_usage = self.disabled_data.get(None)
        if author_id in bot_usage.get("users", EMPTY_SET):
            await ctx.send("Omae wa mou banned.", delete_after=30)
            await self.do_after(ctx.message.delete(), 30)
            return False
        if channel_id in bot_usage.get("channels", EMPTY_SET):
            await ctx.send("Command usage is disabled in this channel.", delete_after=30)
            await self.do_after(ctx.message.delete(), 30)
            return False

        cmd_usage = self.disabled_data.get(ctx.command.qualified_name, {})
        if guild_id in cmd_usage.get("guilds", EMPTY_SET):
            await ctx.send("This command is disabled in this server.", delete_after=30)
            await self.do_after(ctx.message.delete(), 30)
            return False
        if channel_id in cmd_usage.get("channels", EMPTY_SET):
            await ctx.send("You can't use this command in this channel.", delete_after=30)
            await self.do_after(ctx.message.delete(), 30)
            return False
        if (author_id, guild_id) in cmd_usage.get("members", EMPTY_SET):
            await ctx.send("You are banned from using this command in this server.", delete_after=30)
            await self.do_after(ctx.message.delete(), 30)
            return False
        return True

    async def load(self):
        async for guild_data in self.db.guild_data.find({"prefixes": {"$exists": True}}, projection={"_id": -1, "guild_id": 1, "prefixes": 1}):
            if guild_data["prefixes"]:
                self.guild_prefixes[guild_data["guild_id"]] = guild_data["prefixes"]

        bot_data = await self.db.command_data.find_one({"name": {"$eq": None}})
        self.disabled_data = {
            None: {
                "users":    set(bot_data.get("banned_user_ids", [])),
                "channels": set(bot_data.get("disabled_channel_id", []))
            }
        }
        async for command_data in self.db.command_data.find({"name": {"$ne": None}}):
            self.disabled_data[command_data["name"]] = {
                "guilds":   set(command_data.get("disabled_guild_ids", [])),
                "channels": set(command_data.get("disabled_channel_ids", [])),
                "members":  set(command_data.get("disabled_member_ids", []))
            }
        self.add_check(self.block_or_not)

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
