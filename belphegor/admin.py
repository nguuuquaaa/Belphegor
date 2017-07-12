import discord
from discord.ext import commands
from .utils import checks
import inspect

#======================================================================================================

class AdminBot:
    def __init__(self, bot):
        self.bot = bot

    def reload_extension(self, extension):
        try:
            self.bot.unload_extension(extension)
            self.bot.load_extension(extension)
            print(f"Reloaded {extension}")
        except Exception as e:
            print(f"Failed reloading {extension}: {e}")

    def reload_all_extensions(self):
        with open("extensions.txt") as file:
            extensions = [e for e in file.read().splitlines() if e]
        for extension in extensions:
            self.bot.unload_extension(extension)
        for extension in extensions:
            try:
                self.bot.load_extension(extension)
                print(f"Reloaded {extension}")
            except Exception as e:
                print(f"Failed reloading {extension}: {e}")

    @commands.command()
    @checks.owner_only()
    async def reload(self, ctx, extension:str=""):
        if extension:
            self.reload_extension(extension)
        else:
            self.reload_all_extensions()
        print("Done.")

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
        env = {
            'self': self,
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
