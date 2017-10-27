import discord
from discord.ext import commands
from .utils import checks
from io import StringIO
import traceback
from contextlib import redirect_stdout

#==================================================================================================================================================

class AdminBot:
    '''
    I should just call it OwnerOnlyBot but errr....
    '''

    def __init__(self, bot):
        self.bot = bot

    def cancel_task_of(self, extension):
        _loop = self.bot.loop
        if extension == "belphegor.remind":
            cog = self.bot.get_cog("RemindBot")
            if cog:
                cog.reminder.cancel()
        elif extension == "belphegor.music":
            cog = self.bot.get_cog("MusicBot")
            if cog:
                for mp in cog.music_players.values():
                    _loop.create_task(mp.leave_voice())

    async def reload_extension(self, ctx, extension):
        try:
            self.cancel_task_of(extension)
            self.bot.unload_extension(extension)
            self.bot.load_extension(extension)
            print(f"Reloaded {extension}")
            await ctx.confirm()
        except Exception as e:
            print(f"Failed reloading {extension}: {e}")
            await ctx.deny()

    async def reload_all_extensions(self, ctx):
        with open("extensions.txt") as file:
            extensions = [e for e in file.read().splitlines() if e]
        for extension in self.bot.extensions.copy():
            self.cancel_task_of(extension)
            self.bot.unload_extension(extension)
        check = True
        for extension in extensions:
            try:
                self.bot.load_extension(extension)
                print(f"Reloaded {extension}")
            except Exception as e:
                print(f"Failed reloading {extension}: {e}")
                check = False
        if check:
            await ctx.confirm()
        else:
            await ctx.deny()

    @commands.command()
    @checks.owner_only()
    async def reload(self, ctx, extension:str=""):
        if extension:
            await self.reload_extension(ctx, extension)
        else:
            await self.reload_all_extensions(ctx)

    @commands.command()
    @checks.owner_only()
    async def unload(self, ctx, extension:str):
        if extension in self.bot.extensions:
            self.bot.unload_extension(extension)
            print(f"Unloaded {extension}")
            await ctx.confirm()
        else:
            print(f"Extension {extension} doesn't exist.")
            await ctx.deny()

    @commands.command()
    @checks.owner_only()
    async def status(self, ctx, *, stuff):
        await self.bot.change_presence(game=discord.Game(name=stuff))

    @commands.command()
    @checks.owner_only()
    async def logout(self, ctx):
        await self.bot.logout()

    @commands.command(name="eval")
    @checks.owner_only()
    async def _eval(self, ctx, *, data:str):
        data = data.strip()
        if data.startswith("```"):
            data = data.splitlines()[1:]
        else:
            data = data.splitlines()
        data = "\n    ".join(data).strip("` \n")
        code = f"async def func():\n    {data}"
        env = {
            'self': self,
            'ctx': ctx,
            'discord': discord
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
    bot.add_cog(AdminBot(bot))
