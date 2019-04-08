import discord
from discord.ext import commands

#==================================================================================================================================================

saved_stuff = {}

#==================================================================================================================================================

class CustomEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        self.bot.dispatch("reaction_add_or_remove", reaction, user)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        self.bot.dispatch("reaction_add_or_remove", reaction, user)

#==================================================================================================================================================

def to_rgba(self, alpha=255):
    r, g, b = self.to_rgb()
    return (r, g, b, alpha)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(CustomEvent(bot))
    discord.Colour.to_rgba = to_rgba

def teardown(bot):
    del discord.Colour.to_rgba
