import discord
from discord.ext import commands
from . import utils
from .utils import token
import json
import dbl

#==================================================================================================================================================

class DBots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = f"https://discord.bots.gg/api/v1/bots/{bot.user.id}/stats"
        self.headers = {
            "User-Agent": "Belphegor",
            "Authorization": token.DBOTS_TOKEN,
            "content-type": "application/json"
        }
        self.dbl = dbl.Client(self.bot, token.DBL_TOKEN)

    async def update(self):
        payload = {"server_count": len(self.bot.guilds)}
        data = json.dumps(payload)
        await self.bot.session.post(self.base_url, headers=self.headers, data=data)
        await self.dbl.post_guild_count()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.update()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.update()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.update()

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(DBots(bot))
