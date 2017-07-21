import discord
from discord.ext import commands
from .utils import checks
import inspect

#======================================================================================================

class AdminBot:
    def __init__(self, bot):
        self.bot = bot

    async def reload_extension(self, message, extension):
        try:
            self.bot.unload_extension(extension)
            self.bot.load_extension(extension)
            print(f"Reloaded {extension}")
            await message.add_reaction("\u2705")
        except Exception as e:
            print(f"Failed reloading {extension}: {e}")
            await message.add_reaction("\u274c")

    async def reload_all_extensions(self, message):
        with open("extensions.txt") as file:
            extensions = [e for e in file.read().splitlines() if e]
        for extension in extensions:
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
            await message.add_reaction("\u2705")
        else:
            await message.add_reaction("\u274c")

    @commands.command()
    @checks.owner_only()
    async def reload(self, ctx, extension:str=""):
        if extension:
            await self.reload_extension(ctx.message, extension)
        else:
            await self.reload_all_extensions(ctx.message)

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
        env = {'self': self,
               'ctx': ctx,
               'discord': discord}
        env.update(globals())
        try:
            code_obj = compile(data, "test_code", "eval")
            result = eval(code_obj, env)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            result = e
        await ctx.send(f"```{result}```")

#======================================================================================================

def setup(bot):
    bot.add_cog(AdminBot(bot))
