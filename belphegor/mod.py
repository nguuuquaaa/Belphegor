import discord
from discord.ext import commands
from .utils import checks

#==================================================================================================================================================

class ModBot:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.owner_only()
    async def block(self, ctx, user:discord.User):
        await user.block()
        await ctx.send(f"{user.name} has been blocked.")

    @commands.command()
    @checks.owner_only()
    async def unblock(self, ctx, user:discord.User):
        await user.unblock()
        await ctx.send(f"{user.name} has been unblocked.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(ModBot(bot))
