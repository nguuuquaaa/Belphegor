import discord
from discord.ext import commands
from belphegor import utils
from belphegor.utils import checks, config, data_type
import asyncio
import aiohttp
import psutil
import os
from motor import motor_asyncio
import sys
import traceback
import functools

#==================================================================================================================================================

EMPTY_SET = frozenset()

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
        self.bot_lock = asyncio.Lock()
        self.initial_extensions = kwargs.get("initial_extensions", config.all_extensions)
        self.restart_flag = False
        self.saved_stuff = {}

    async def get_prefix(self, message):
        prefixes = [f"<@{self.user.id}> ", f"<@!{self.user.id}> "]
        if message.guild:
            gp = self.guild_prefixes.get(message.guild.id)
        else:
            gp = None
        if gp:
            prefixes.extend(gp)
        else:
            prefixes.extend(self.default_prefix)
        return prefixes

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=data_type.BelphegorContext)
        await self.invoke(ctx)

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return
        print(f"Ignoring exception in command {ctx.command}:", file=sys.stderr)
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        else:
            traceback.print_exception(type(error), error, None, file=sys.stderr)

    async def on_ready(self):
        print("Logged in as")
        print(self.user.name)
        print(self.user.id)
        print("------")
        await asyncio.sleep(5)
        await self.change_presence(activity=discord.Game(name="with Chronos-senpai"))

    def create_task_and_count(self, coro):
        self.counter += 1

        async def do_stuff():
            await coro
            self.counter -= 1

        self.loop.create_task(do_stuff())

    async def run_in_lock(self, *args, **kwargs):
        args = list(args)
        item = args.pop(0)
        lock = self.bot_lock
        if isinstance(item, (asyncio.Lock, asyncio.Condition)):
            lock = item
            item = args.pop(0)
        if callable(item):
            async with lock:
                run_func = functools.partial(item, *args, **kwargs)
                return await self.loop.run_in_executor(None, run_func)
        else:
            raise TypeError("Wat. You serious?")

    async def logout(self):
        await self.session.close()
        await super().logout()
        print("Logging out...")
        while self.counter > 0:
            await asyncio.sleep(0.1)
        await asyncio.sleep(3)
        if "google" in self.saved_stuff:
            self.saved_stuff["google"].terminate()

    def block_or_not(self, ctx):
        author_id = ctx.author.id
        channel_id = getattr(ctx.channel, "id", None)
        guild_id = getattr(ctx.guild, "id", None)

        if author_id in self.blocked_user_ids:
            self.loop.create_task(ctx.send("Omae wa mou blocked.", delete_after=30))
            self.do_after(ctx.message.delete(), 30)
            return False

        blocked_data = self.disabled_data.get(guild_id)
        if blocked_data:
            if getattr(ctx.command, "hidden", None) or getattr(ctx.command, "qualified_name", "").partition(" ")[0] in ("enable", "disable"):
                return True

            if blocked_data.get("disabled_bot_guild", False):
                self.loop.create_task(ctx.send("Command usage is disabled in this server.", delete_after=30))
                self.do_after(ctx.message.delete(), 30)
                return False
            if channel_id in blocked_data.get("disabled_bot_channel", EMPTY_SET):
                self.loop.create_task(ctx.send("Command usage is disabled in this channel.", delete_after=30))
                self.do_after(ctx.message.delete(), 30)
                return False
            if author_id in blocked_data.get("disabled_bot_member", EMPTY_SET):
                self.loop.create_task(ctx.send("You are forbidden from using bot commands in this server.", delete_after=30))
                self.do_after(ctx.message.delete(), 30)
                return False

            cmd_name = ctx.command.qualified_name
            if cmd_name in blocked_data.get("disabled_command_guild", EMPTY_SET):
                self.loop.create_task(ctx.send("This command is disabled in this server.", delete_after=30))
                self.do_after(ctx.message.delete(), 30)
                return False
            if (cmd_name, channel_id) in blocked_data.get("disabled_command_channel", EMPTY_SET):
                self.loop.create_task(ctx.send("This command is disabled in this channel.", delete_after=30))
                self.do_after(ctx.message.delete(), 30)
                return False
            if (cmd_name, author_id) in blocked_data.get("disabled_command_member", EMPTY_SET):
                self.loop.create_task(ctx.send("You are forbidden from using this command in this server.", delete_after=30))
                self.do_after(ctx.message.delete(), 30)
                return False
        return True

    async def load(self):
        async for guild_data in self.db.guild_data.find({"prefixes": {"$exists": True, "$ne": []}}, projection={"_id": -1, "guild_id": 1, "prefixes": 1}):
            if guild_data["prefixes"]:
                guild_data["prefixes"].sort(reverse=True)
                self.guild_prefixes[guild_data["guild_id"]] = guild_data["prefixes"]

        bot_data = await self.db.belphegor_config.find_one({"category": "block"})
        self.blocked_user_ids = set(bot_data.get("blocked_user_ids", []))

        self.disabled_data = {}
        async for guild_data in self.db.guild_data.find(
            {
                "$or": [
                    {
                        "disabled_bot_guild": {
                            "$eq": True
                        }
                    },
                    {
                        "disabled_bot_channel": {
                            "$exists": True,
                            "$ne": []
                        }
                    },
                    {
                        "disabled_bot_member": {
                            "$exists": True,
                            "$ne": []
                        }
                    },
                    {
                        "disabled_command_guild": {
                            "$exists": True,
                            "$ne": []
                        }
                    },
                    {
                        "disabled_command_channel": {
                            "$exists": True,
                            "$ne": []
                        }
                    },
                    {
                        "disabled_bot_member": {
                            "$exists": True,
                            "$ne": []
                        }
                    }
                ]
            },
            projection={
                "_id": False,
                "guild_id": True,
                "disabled_bot_guild": True,
                "disabled_bot_channel": True,
                "disabled_bot_member": True,
                "disabled_command_guild": True,
                "disabled_command_channel": True,
                "disabled_command_member": True
            }
        ):
            guild_id = guild_data.pop("guild_id")
            self.disabled_data[guild_id] = {key: (value if isinstance(value, bool) else set(tuple(v) if isinstance(v, list) else v for v in value)) for key, value in guild_data.items()}
        self.add_check(self.block_or_not)

        await self.wait_until_ready()
        for extension in self.initial_extensions:
            try:
                self.load_extension(extension)
                print(f"Loaded {extension}")
            except Exception as e:
                print(f"Failed loading {extension}: {e}")
                return await self.logout()
        print("Done")

    async def fetch(self, url, **kwargs):
        return await utils.fetch(self.session, url, **kwargs)

    async def download(self, url, path, **kwargs):
        return await utils.download(self.session, url, path, **kwargs)

    def do_after(self, coro, wait_time):
        async def things_to_do():
            await asyncio.sleep(wait_time)
            try:
                await coro
            except:
                pass
        self.loop.create_task(things_to_do())
