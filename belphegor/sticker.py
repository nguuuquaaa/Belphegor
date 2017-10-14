import discord
from discord.ext import commands
import re
from fuzzywuzzy import process

#==================================================================================================================================================

class StickerBot:
    def __init__(self, bot):
        self.bot = bot
        self.sticker_list = self.bot.db.sticker_list
        self.sticker_regex = re.compile(r"(?<=[$+])\w+", flags=re.I)

    async def on_message(self, message):
        result = self.sticker_regex.findall(message.content)
        st = await self.sticker_list.find_one({"name": {"$in": result}})
        if st:
            embed = discord.Embed()
            embed.set_image(url=st["url"])
            await message.channel.send(embed=embed)

    @commands.group()
    async def sticker(self, ctx):
        if ctx.invoked_subcommand is None:
            message = ctx.message
            message.content = ">>help sticker"
            await self.bot.process_commands(message)

    @sticker.command()
    async def add(self, ctx, name, url):
        name = re.sub(r"\W+", "", name)
        if url[:8] == "https://" or url[:7] == "http://":
            value = {"name": name, "url": url, "author_id": ctx.author.id}
            before = await self.sticker_list.find_one_and_update({"name": name}, {"$setOnInsert": value}, upsert=True)
            if before is not None:
                await ctx.send("Cannot add already existed sticker.")
            else:
                await ctx.send(f"Sticker {name} added.")
        else:
            await ctx.send("Url should start with http or https.")

    @sticker.command()
    async def find(self, ctx, *, name):
        sticker_names = await self.sticker_list.distinct("name", {})
        relevant = process.extract(name, sticker_names, limit=10)
        text = "\n".join([f"{r[0]} ({r[1]}%)" for r in relevant if r[1]>50])
        await ctx.send(f"Result:\n```\n{text}\n```")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(StickerBot(bot))