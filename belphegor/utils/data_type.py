import discord
from discord.ext import commands
from .format import embed_page_format, now_time
from .checks import do_after
from .request import *
import asyncio
import aiohttp
import psutil
import os
from motor import motor_asyncio
import sys
import traceback
import functools
import re

#==================================================================================================================================================

EMPTY_SET = frozenset()

#==================================================================================================================================================

def to_int(any_obj, *, default=None):
    try:
        return int(any_obj)
    except:
        return default

def get_element(container, predicate, *, default=None):
    result = default
    if isinstance(predicate, int):
        try:
            result = container[predicate]
        except IndexError:
            pass
    elif callable(predicate):
        for item in container:
            try:
                if predicate(item):
                    result = item
                    break
            except:
                pass
    else:
        raise TypeError("Predicate is an int or a callable.")
    return result

#==================================================================================================================================================

class BaseObject:
    def __init__(self, data):
        for key, value in data.items():
            if key[0] != "_":
                setattr(self, key, value)

#==================================================================================================================================================

class BelphegorContext(commands.Context):
    async def confirm(self):
        await self.message.add_reaction("\u2705")

    async def deny(self):
        await self.message.add_reaction("\u274c")

    async def embed_page(self, embeds, *, timeout=60, target=None):
        _loop = self.bot.loop
        item = embeds[0]
        vertical = isinstance(item, list)
        if vertical:
            message = await self.send(embed=item[0])
            max_page = sum((len(p) for p in embeds))
            max_vertical = len(embeds)
            if max_vertical == 1:
                vertical = False
                embeds = item
        else:
            max_vertical = 1
            message = await self.send(embed=item)
            max_page = len(embeds)
        if max_page > 1:
            target = target or self.author
            current_page = 0
            if max_page > max_vertical:
                possible_reactions = ["\u23ee", "\u25c0", "\u25b6", "\u23ed"]
            else:
                possible_reactions = []
            if vertical:
                pool_index = 0
                pool = item
                max_page = len(pool)
                possible_reactions.extend(("\U0001f53c", "\U0001f53d", "\u274c"))
            else:
                pool = embeds
                possible_reactions.append("\u274c")
            for r in possible_reactions:
                _loop.create_task(message.add_reaction(r))

            async def rmv_rection(r, u):
                try:
                    await message.remove_reaction(r, u)
                except:
                    pass

            while True:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add",
                        check=lambda r,u: u.id==target.id and r.emoji in possible_reactions and r.message.id==message.id,
                        timeout=timeout
                    )
                except:
                    try:
                        return await message.clear_reactions()
                    except:
                        return
                e = reaction.emoji
                if e == "\u25c0":
                    current_page = max(current_page-1, 0)
                elif e == "\u25b6":
                    current_page = min(current_page+1, max_page-1)
                elif e == "\u23ee":
                    current_page = max(current_page-10, 0)
                elif e == "\u23ed":
                    current_page = min(current_page+10, max_page-1)
                elif e == "\u274c":
                    try:
                        return await message.clear_reactions()
                    except:
                        return
                elif vertical:
                    if e == "\U0001f53c":
                        pool_index = max(pool_index-1, 0)
                        pool = embeds[pool_index]
                        max_page = len(pool)
                        current_page = min(current_page, max_page-1)
                    elif e == "\U0001f53d":
                        pool_index = min(pool_index+1, max_vertical-1)
                        pool = embeds[pool_index]
                        max_page = len(pool)
                        current_page = min(current_page, max_page-1)
                await message.edit(embed=pool[current_page])
                _loop.create_task(rmv_rection(reaction, user))

    async def yes_no_prompt(self, sentences, *, timeout=60, target=None, delete_mode=False):
        _loop = self.bot.loop
        message = await self.send(sentences["initial"])
        target = target or self.author
        possible_reactions = ("\u2705", "\u274c")
        for r in possible_reactions:
            _loop.create_task(message.add_reaction(r))
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=lambda r,u: u.id==target.id and r.emoji in possible_reactions and r.message.id==message.id,
                timeout=timeout
            )
        except:
            result = False
            if not delete_mode:
                _loop.create_task(message.edit(content=sentences["timeout"]))
        else:
            if reaction.emoji == "\u2705":
                result = True
                if not delete_mode:
                    _loop.create_task(message.edit(content=sentences["yes"]))
            else:
                result = False
                if not delete_mode:
                    _loop.create_task(message.edit(content=sentences["no"]))
        if delete_mode:
            _loop.create_task(message.delete())
        else:
            try:
                _loop.create_task(message.clear_reactions())
            except:
                pass
        return result

    async def search(self, name, pool, *, cls=BaseObject, colour=None, atts=["id"], name_att, emoji_att=None, prompt=None, sort={}):
        try:
            atts.remove("id")
            item_id = int(name)
        except:
            pass
        else:
            result = await pool.find_one({"id": item_id})
            if result:
                return cls(result)
            else:
                await self.send(f"Can't find {name} in database.")
                return None
        name = name.lower()
        regex = ".*?".join(map(re.escape, name.split()))
        pipeline = [{
            "$match": {
                "$or": [
                    {
                        att: {
                            "$regex": regex,
                            "$options": "i"
                        }
                    } for att in atts
                ]
            }
        }]
        if sort:
            add_fields = {}
            sort_order = {}
            for key, value in sort.items():
                if isinstance(value, int):
                    sort_order[key] = value
                elif isinstance(value, (list, tuple)):
                    new_field = f"_sort_{key}"
                    add_fields[new_field] = {"$indexOfArray": [value, f"${key}"]}
                    sort_order[new_field] = 1
            if add_fields:
                pipeline.append({"$addFields": add_fields})
            pipeline.append({"$sort": sort_order})
        cursor = pool.aggregate(pipeline)
        if prompt is False:
            async for item_data in cursor:
                if name in (item_data.get(att, "").lower() for att in atts):
                    break
            try:
                return cls(item_data)
            except:
                await self.send(f"Can't find {name} in database.")
                return None
        else:
            result = [cls(item_data) async for item_data in cursor]
            if not result:
                await self.send(f"Can't find {name} in database.")
                return None
            elif len(result) == 1 and not prompt:
                return result[0]
            emojis = self.cog.emojis
            embeds = embed_page_format(
                result, 10,
                title="Do you mean:",
                description=lambda i, x: f"`{i+1}:` {emojis.get(getattr(x, emoji_att), '') if emoji_att else ''}{getattr(x, name_att)}",
                colour=colour
            )
            self.bot.loop.create_task(self.embed_page(embeds))
            index = await self.wait_for_choice(max=len(result))
            if index is None:
                return None
            else:
                return result[index]

    async def wait_for_choice(self, *, max, target=None, timeout=600):
        target = target or self.author
        try:
            msg = await self.bot.wait_for("message", check=lambda m: m.author.id==target.id and m.channel.id==self.channel.id, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        try:
            result = int(msg.content) - 1
        except:
            return None
        if 0 <= result < max:
            return result
        else:
            return None

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
        self.start_time = now_time()
        self.loop.create_task(self.load())
        self.mongo_client = motor_asyncio.AsyncIOMotorClient()
        self.db = self.mongo_client.belphydb
        self.counter = 0
        self.bot_lock = asyncio.Lock()
        self.initial_extensions = kwargs.get("initial_extensions", config.all_extensions)
        self.restart_flag = False
        self.reload_needed = [sys.modules[__name__]]

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
        ctx = await self.get_context(message, cls=BelphegorContext)
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
        await self.change_presence(activity=discord.Game(name='with Chronos-senpai'))

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
            raise Exception("Wat. You serious?")

    async def logout(self):
        await self.session.close()
        await super().logout()
        print("Logging out...")
        while self.counter > 0:
            await asyncio.sleep(0.1)

    def block_or_not(self, ctx):
        author_id = ctx.author.id
        channel_id = getattr(ctx.channel, "id", None)
        guild_id = getattr(ctx.guild, "id", None)

        if author_id in self.blocked_user_ids:
            self.loop.create_task(ctx.send("Omae wa mou blocked.", delete_after=30))
            do_after(ctx.message.delete(), 30)
            return False

        blocked_data = self.disabled_data.get(guild_id)
        if blocked_data:
            if getattr(ctx.command, "hidden", None) or getattr(ctx.command, "qualified_name", "").partition(" ")[0] in ("enable", "disable"):
                return True

            if blocked_data.get("disabled_bot_guild", False):
                self.loop.create_task(ctx.send("Command usage is disabled in this server.", delete_after=30))
                do_after(ctx.message.delete(), 30)
                return False
            if channel_id in blocked_data.get("disabled_bot_channel", EMPTY_SET):
                self.loop.create_task(ctx.send("Command usage is disabled in this channel.", delete_after=30))
                do_after(ctx.message.delete(), 30)
                return False
            if author_id in blocked_data.get("disabled_bot_member", EMPTY_SET):
                self.loop.create_task(ctx.send("You are forbidden from using bot commands in this server.", delete_after=30))
                do_after(ctx.message.delete(), 30)
                return False

            cmd_name = ctx.command.qualified_name
            if cmd_name in blocked_data.get("disabled_command_guild", EMPTY_SET):
                self.loop.create_task(ctx.send("This command is disabled in this server.", delete_after=30))
                do_after(ctx.message.delete(), 30)
                return False
            if (cmd_name, channel_id) in blocked_data.get("disabled_command_channel", EMPTY_SET):
                self.loop.create_task(ctx.send("This command is disabled in this channel.", delete_after=30))
                do_after(ctx.message.delete(), 30)
                return False
            if (cmd_name, author_id) in blocked_data.get("disabled_command_member", EMPTY_SET):
                self.loop.create_task(ctx.send("You are forbidden from using this command in this server.", delete_after=30))
                do_after(ctx.message.delete(), 30)
                return False
        return True

    async def load(self):
        async for guild_data in self.db.guild_data.find({"prefixes": {"$exists": True, "$ne": []}}, projection={"_id": -1, "guild_id": 1, "prefixes": 1}):
            if guild_data["prefixes"]:
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
        return await fetch(self.session, url, **kwargs)

    async def download(self, url, path, **kwargs):
        return await download(self.session, url, path, **kwargs)
