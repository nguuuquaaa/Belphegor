import discord
from discord.ext import commands

saved_stuff = {}

#==================================================================================================================================================

class CustomEvent:
    def __init__(self, bot):
        self.bot = bot

    async def on_reaction_add(self, reaction, user):
        self.bot.dispatch("reaction_add_or_remove", reaction, user)

    async def on_reaction_remove(self, reaction, user):
        self.bot.dispatch("reaction_add_or_remove", reaction, user)

#==================================================================================================================================================

def to_rgba(self, alpha=255):
    r, g, b = self.to_rgb()
    return (r, g, b, alpha)

def parse_message_delete_bulk(self, data):
    raw = discord.raw_models.RawBulkMessageDeleteEvent(data)
    self.dispatch('raw_bulk_message_delete', raw)

    to_be_deleted = [message for message in self._messages if message.id in raw.message_ids]
    self.dispatch('bulk_message_delete', to_be_deleted)
    for msg in to_be_deleted:
        self._messages.remove(msg)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(CustomEvent(bot))
    discord.Colour.to_rgba = to_rgba
    saved_stuff["bulk"] = discord.state.ConnectionState.parse_message_delete_bulk
    discord.state.ConnectionState.parse_message_delete_bulk = parse_message_delete_bulk

def teardown(bot):
    del discord.Colour.to_rgba
    discord.state.ConnectionState.parse_message_delete_bulk = saved_stuff["bulk"]
