import discord
from discord.ext import commands
from io import BytesIO

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

def from_bytes(cls, bytes_, filename, *, spoiler=False):
    return cls(BytesIO(bytes_), filename, spoiler=spoiler)

def from_str(cls, str_, filename="file.txt", *, spoiler=False, encoding="utf-8"):
    return cls(BytesIO(str_.encode(encoding)), filename, spoiler=spoiler)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(CustomEvent(bot))
    discord.Colour.to_rgba = to_rgba
    discord.File.from_bytes = classmethod(from_bytes)
    discord.File.from_str = classmethod(from_str)

def teardown(bot):
    del discord.Colour.to_rgba
