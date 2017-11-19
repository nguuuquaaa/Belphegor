import discord
from discord.ext import commands
from . import utils
from .utils import checks, config
from io import StringIO
import traceback
from contextlib import redirect_stdout

#==================================================================================================================================================

class Admin:
    '''
        I should just call it OwnerOnlyCog but errr....
    '''

    def __init__(self, bot):
        self.bot = bot

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

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Admin(bot))
