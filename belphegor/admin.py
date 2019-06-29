import discord
from discord.ext import commands
from . import utils
from .utils import checks, data_type
from io import StringIO, BytesIO
import traceback
from contextlib import redirect_stdout
import importlib
from bs4 import BeautifulSoup as BS
import json
import os
from shutil import copyfile
from distutils.dir_util import copy_tree
import subprocess
import copy
import sys
import textwrap
import objgraph
import math
import asyncio
import pymongo
import re

#==================================================================================================================================================

class Admin(commands.Cog):
    '''
        I should just call it OwnerOnlyCog but errr....
    '''

    def __init__(self, bot):
        self.bot = bot
        self.belphegor_config = bot.db.belphegor_config

    @commands.command(hidden=True)
    @checks.owner_only()
    async def reload(self, ctx, extension):
        extension = f"belphegor.{extension}"
        try:
            if extension in self.bot.extensions:
                self.bot.reload_extension(extension)
            else:
                self.bot.load_extension(extension)
        except commands.ExtensionError:
            await ctx.send(f"```\nFailed reloading {extension}:\n{traceback.format_exc()}```")
        else:
            print(f"Reloaded {extension}")
            await ctx.confirm()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def unload(self, ctx, extension):
        extension = f"belphegor.{extension}"
        if extension in self.bot.extensions:
            self.bot.unload_extension(extension)
            print(f"Unloaded {extension}")
            await ctx.confirm()
        else:
            await ctx.send(f"Extension {extension} doesn't exist.")

    @commands.command(hidden=True)
    @checks.owner_only()
    async def reimport(self, ctx, module_name):
        module = sys.modules.get(f"belphegor.{module_name}")
        try:
            importlib.reload(module)
        except:
            traceback.print_exc()
            await ctx.deny()
        else:
            print(f"Reimported belphegor.{module_name}")
            await ctx.confirm()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def deepreimport(self, ctx, module_name):
        name = f"belphegor.{module_name}"
        remove = [name]
        name_check = name + "."
        for n in sys.modules:
            if n.startswith(name_check):
                remove.append(n)

        for n in remove:
            sys.modules.pop(n, None)

        try:
            importlib.import_module(name)
        except:
            traceback.print_exc()
            await ctx.deny()
        else:
            print(f"Reimported {name}")
            await ctx.confirm()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def status(self, ctx, *, stuff):
        data = stuff.partition(" ")
        await self.bot.change_presence(activity=discord.Activity(type=getattr(discord.ActivityType, data[0]), name=data[2]))
        await ctx.confirm()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def restart(self, ctx):
        self.bot.restart_flag = True
        await self.bot.logout()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def logout(self, ctx):
        cog = self.bot.get_cog("Statistics")
        if cog:
            async def update_all():
                msg = await ctx.send("Updating stats...")
                await cog.update_all()
                await msg.edit(content="Done.")
            self.bot.create_task_and_count(update_all())
        await self.bot.logout()

    @commands.command(name="eval", hidden=True)
    @checks.owner_only()
    async def _eval(self, ctx, *, data: str):
        data = utils.clean_codeblock(data)
        code = f"async def func():\n{textwrap.indent(data, '    ')}"
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "discord": discord,
            "commands": commands,
            "utils": utils,
            "asyncio": asyncio
        }
        try:
            exec(code, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e}\n```")
        stdout = StringIO()
        func = env["func"]
        try:
            with redirect_stdout(stdout):
                await func()
        except:
            add_text = f"\n{traceback.format_exc()}"
        else:
            add_text = "\n"
        finally:
            value = stdout.getvalue()
            if value or add_text:
                ret = value + add_text
                if len(ret) > 1950:
                    await ctx.send(file=discord.File.from_str(ret, "result.txt"))
                else:
                    await ctx.send(f"```\n{ret}```")

    @commands.command(hidden=True)
    @checks.owner_only()
    async def block(self, ctx, user: discord.User):
        self.bot.blocked_user_ids.add(user.id)
        result = await self.belphegor_config.update_one({"category": "block"}, {"$addToSet": {"blocked_user_ids": user.id}})
        if result.modified_count > 0:
            await ctx.send(f"{user} has been blocked.")
        else:
            await ctx.send(f"{user} is already blocked.")

    @commands.command(hidden=True)
    @checks.owner_only()
    async def unblock(self, ctx, user: discord.User):
        self.bot.blocked_user_ids.discard(user.id)
        result = await self.belphegor_config.update_one({"category": "block"}, {"$pull": {"blocked_user_ids": user.id}})
        if result.modified_count > 0:
            await ctx.send(f"{user} has been unblocked.")
        else:
            await ctx.send(f"{user} is not blocked.")

    @commands.command(hidden=True)
    @checks.owner_only()
    async def hackblock(self, ctx, user_id: int):
        self.bot.blocked_user_ids.add(user_id)
        result = await self.belphegor_config.update_one({"category": "block"}, {"$addToSet": {"blocked_user_ids": user_id}})
        if result.modified_count > 0:
            await ctx.confirm()
        else:
            await ctx.deny()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def mongo(self, ctx, col, *, raw_query):
        raw_query = utils.clean_codeblock(raw_query)
        try:
            raw = eval(raw_query, globals(), locals())
        except:
            return await ctx.send(f"```\n{traceback.format_exc()}\n```")

        if isinstance(raw, dict):
            query = raw
            projection = {"_id": False}
        else:
            query = raw[0]
            projection = raw[1]
            projection["_id"] = False
        data = []
        try:
            async for d in self.bot.db[col].find(query, projection=projection):
                data.append(d)
        except pymongo.errors.OperationFailure as e:
            return await ctx.send(e)
        if data:
            text = json.dumps(data, indent=4, ensure_ascii=False, default=repr)
            if len(text) > 1950:
                await ctx.send(file=discord.File(BytesIO(text.encode("utf-8")), "data.json"))
            else:
                await ctx.send(f"```json\n{text}\n```")
        else:
            await ctx.send("Nothing found.")

    @commands.command(hidden=True)
    @checks.owner_only()
    async def aggregate(self, ctx, col, *, raw_query):
        raw_query = utils.clean_codeblock(raw_query)
        try:
            query = eval(raw_query, globals(), locals())
        except:
            return await ctx.send(f"```\n{traceback.format_exc()}\n```")

        data = []
        try:
            async for d in self.bot.db[col].aggregate(query):
                d.pop("_id")
                data.append(d)
        except pymongo.errors.OperationFailure as e:
            return await ctx.send(e)
        if data:
            text = json.dumps(data, indent=4, ensure_ascii=False, default=repr)
            if len(text) > 1950:
                await ctx.send(file=discord.File(BytesIO(text.encode("utf-8")), filename="data.json"))
            else:
                await ctx.send(f"```json\n{text}\n```")
        else:
            await ctx.send("Nothing found.")

    @commands.command(hidden=True, aliases=["sudo"])
    @checks.owner_only()
    async def force(self, ctx, *, cmd):
        msg = copy.copy(ctx.message)
        msg.content = f"{ctx.me.mention} {cmd}"
        new_ctx = await self.bot.get_context(msg, cls=data_type.BelphegorContext)
        await new_ctx.reinvoke()

    @commands.command(hidden=True, aliases=["impersonate"])
    @checks.owner_only()
    async def runas(self, ctx, member: discord.Member, *, cmd):
        msg = copy.copy(ctx.message)
        msg.content = f"{ctx.me.mention} {cmd}"
        msg.author = member
        await self.bot.process_commands(msg)

    @commands.command(hidden=True)
    @checks.owner_only()
    async def changeavatar(self, ctx, *, img_url):
        bytes_ = await self.bot.fetch(img_url)
        await ctx.bot.user.edit(avatar=bytes_)
        await ctx.confirm()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def prettify(self, ctx, url, *, params="None"):
        bytes_ = await self.bot.fetch(url, params=eval(params))
        data = BS(bytes_.decode("utf-8"), "lxml")
        await ctx.send(file=discord.File(BytesIO(data.prettify().encode("utf-8")), filename="data.html"))

    @commands.command(hidden=True)
    @checks.owner_only()
    async def growth(self, ctx, limit: int=10):
        g = objgraph.growth(limit)
        max_class = 0
        max_count = 0
        max_growth = 0
        for item in g:
            len_class = len(item[0])
            len_count = int(math.log10(item[1])) + 1
            len_growth = int(math.log10(item[2])) + 1

            if len_class > max_class:
                max_class = len_class
            if len_count > max_count:
                max_count = len_count
            if len_growth > max_growth:
                max_growth = len_growth

        gr = "\n".join((f"{i[0]: <{max_class}}     {i[1]: >{max_count}}     {i[2]: >+{max_growth+1}}" for i in g))
        await ctx.send(f"```\n{gr}\n```")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Admin(bot))
