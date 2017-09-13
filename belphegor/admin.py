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
    async def unload(self, ctx, extension:str):
        if extension in self.bot.extensions:
            self.bot.unload_extension(extension)
            print(f"Unloaded {extension}")
            await ctx.message.add_reaction("\u2705")
        else:
            print(f"Extension {extension} doesn't exist.")
            await ctx.message.add_reaction("\u274c")

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
        if data.startswith("```") and data.endswith("```"):
            data = data.splitlines()[1:]
        else:
            data = data.splitlines()
        data = "\n ".join(data).strip("` \n")
        code = f"async def func():\n {data}"
        env = {'self': self,
               'ctx': ctx,
               'discord': discord}
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

    @commands.command()
    @checks.owner_only()
    async def block(self, ctx, member:discord.Member):
        self.bot.block_users.append(member.id)
        await ctx.send(f"{member.name} has been blocked (temporary).")

    @commands.command()
    @checks.owner_only()
    async def unblock(self, ctx, member:discord.Member):
        self.bot.block_users.remove(member.id)
        await ctx.send(f"{member.name} has been unblocked.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(AdminBot(bot))
