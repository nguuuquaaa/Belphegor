import discord
from discord.ext import commands
from . import utils
from .utils import checks, config
from io import StringIO
import traceback
from contextlib import redirect_stdout
import importlib
from bs4 import BeautifulSoup as BS
import json
import os
from shutil import copyfile
from distutils.dir_util import copy_tree
import subprocess

#==================================================================================================================================================

class Admin:
    '''
        I should just call it OwnerOnlyCog but errr....
    '''

    def __init__(self, bot):
        self.bot = bot
        self.belphegor_config = bot.db.belphegor_config

    async def reload_extension(self, ctx, extension):
        try:
            self.bot.unload_extension(extension)
            self.bot.load_extension(extension)
            print(f"Reloaded {extension}")
            await ctx.confirm()
        except:
            print(f"Failed reloading {extension}:\n{traceback.format_exc()}")
            await ctx.deny()

    async def reload_all_extensions(self, ctx):
        for extension in tuple(self.bot.extensions.keys()):
            self.bot.unload_extension(extension)
        check = True
        for extension in config.all_extensions:
            try:
                self.bot.load_extension(extension)
                print(f"Reloaded {extension}")
            except Exception as e:
                print(f"Failed reloading {extension}:\n{traceback.format_exc()}")
                check = False
        if check:
            await ctx.confirm()
        else:
            await ctx.deny()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def reload(self, ctx, extension=""):
        if extension:
            await self.reload_extension(ctx, extension)
        else:
            await self.reload_all_extensions(ctx)

    @commands.command(hidden=True)
    @checks.owner_only()
    async def unload(self, ctx, extension):
        if extension in self.bot.extensions:
            self.bot.unload_extension(extension)
            print(f"Unloaded {extension}")
            await ctx.confirm()
        else:
            print(f"Extension {extension} doesn't exist.")
            await ctx.deny()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def reimport(self, ctx, module_name):
        modules = module_name.split(".")
        module = __import__("belphegor")
        try:
            for m in modules:
                module = getattr(module, m)
            importlib.reload(module)
        except:
            print(traceback.format_exc())
            await ctx.deny()
        else:
            await ctx.confirm()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def status(self, ctx, *, stuff):
        data = stuff.partition(" ")
        try:
            t = int(data[0])
            stuff = data[2]
        except:
            t = 0
        await self.bot.change_presence(game=discord.Game(name=stuff, type=t))

    @commands.command(hidden=True)
    @checks.owner_only()
    async def logout(self, ctx):
        await self.bot.logout()

    @commands.command(name="eval", hidden=True)
    @checks.owner_only()
    async def _eval(self, ctx, *, data: str):
        data = data.strip()
        if data.startswith("```"):
            data = data.splitlines()[1:]
        else:
            data = data.splitlines()
        data = "\n    ".join(data).strip("` \n")
        code = f"async def func():\n    {data}"
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "discord": discord,
            "commands": commands,
            "utils": utils
        }
        env.update(locals())
        try:
            exec(code, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e}\n```")
        stdout = StringIO()
        func = env["func"]
        try:
            with redirect_stdout(stdout):
                result = await func()
        except:
            value = stdout.getvalue()
            return await ctx.send(f'```\n{value}\n{traceback.format_exc()}\n```')
        value = stdout.getvalue()
        if result is None:
            if value:
                await ctx.send(f'```\n{value}\n```')
        else:
            await ctx.send(f'```\n{value}\n{result}\n```')

    @commands.command(hidden=True)
    @checks.owner_only()
    async def block(self, ctx, user: discord.User):
        if user.id in self.bot.blocked_users:
            await ctx.deny()
        else:
            self.bot.blocked_users.add(user.id)
            await self.belphegor_config.update_one({"category": "blocked"}, {"$addToSet": {"user_ids": user.id}})
            await ctx.send(f"{user.name} has been blocked.")

    @commands.command(hidden=True)
    @checks.owner_only()
    async def unblock(self, ctx, user: discord.User):
        if user.id in self.bot.blocked_users:
            self.bot.blocked_users.remove(user.id)
            await self.belphegor_config.update_one({"category": "blocked"}, {"$pull": {"user_ids": user.id}})
            await ctx.send(f"{user.name} has been unblocked.")
        else:
            await ctx.deny()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def hackblock(self, ctx, user_id: int):
        user = await self.bot.get_user_info(user_id)
        if user.id in self.bot.blocked_users:
            await ctx.deny()
        else:
            self.bot.blocked_users.add(user_id)
            await self.belphegor_config.update_one({"category": "blocked"}, {"$addToSet": {"user_ids": user_id}})
            await ctx.send(f"{user.name} has been blocked.")

    @commands.command(hidden=True)
    @checks.owner_only()
    async def prettify(self, ctx, url, filename="data.html"):
        try:
            bytes_ = await utils.fetch(self.bot.session, url)
            data = BS(bytes_.decode("utf-8"), "xml")
            with open(filename, "w", encoding="utf-8") as file:
                file.write(data.prettify())
        except:
            print(traceback.format_exc())
            await ctx.deny()
        else:
            await ctx.confirm()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def mongoitem(self, ctx, col, *, query="{}"):
        data = await self.bot.db[col].find_one(eval(query))
        if data:
            data.pop("_id")
            await ctx.send(file=discord.File(json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8"), filename="data.json"))
        else:
            await ctx.send("Nothing found.")

    @commands.command(hidden=True)
    @checks.owner_only()
    async def fuckgit(self, ctx, *, cmt):
        current_dir = os.getcwd().replace("\\", "/")
        with open("git_dir.txt", encoding="utf-8") as f:
            data = filter(None, f.read().splitlines())
        r = current_dir.rpartition("/")
        target_dir = f"{r[0]}/Belphegor.git"
        proc = subprocess.Popen("cmd.exe", cwd=target_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        def git_push():
            for item in data:
                c = f"{current_dir}{item}"
                t = f"{target_dir}{item}"
                if "." in item:
                    copyfile(c, t)
                else:
                    copy_tree(c, t)
                print(f"Done copying {item}")
            proc.stdin.write("git add .\n".encode("utf-8"))
            proc.stdin.flush()
            print(proc.stdout.readline().decode("utf-8"))
            proc.stdin.write(f"git commit -am \"{cmt}\"\n".encode("utf-8"))
            proc.stdin.flush()
            print(proc.stdout.readline().decode("utf-8"))
            proc.stdin.write("git push belphegor master\n".encode("utf-8"))
            proc.stdin.flush()
            print(proc.stdout.readline().decode("utf-8"))
            proc.stdin.write("exit\n".encode("utf-8"))
            proc.stdin.flush()
            print(proc.stdout.readline().decode("utf-8"))

        try:
            await self.bot.loop.run_in_executor(None, git_push)
        except:
            print(traceback.format_exc())
            await ctx.deny()
        else:
            return_code = await self.bot.loop.run_in_executor(None, proc.wait, 60)
            if return_code is None:
                proc.terminate()
                await ctx.deny()
            else:
                await ctx.confirm()

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Admin(bot))
