import discord
from discord.ext import commands
import re
from fuzzywuzzy import process
from . import utils
from .utils import checks

#==================================================================================================================================================

class Sticker:
    def __init__(self, bot):
        self.bot = bot
        self.sticker_list = self.bot.db.sticker_list
        self.sticker_regex = re.compile(r"(?<=\$)\w+")

    async def on_message(self, message):
        if message.author.bot:
            return
        result = self.sticker_regex.findall(message.content)
        query = {"name": {"$in": result}}
        if message.guild:
            query["banned_guilds"] = {"$ne": message.guild.id}
        st = await self.sticker_list.find_one(query)
        if st:
            embed = discord.Embed()
            embed.set_image(url=st["url"])
            await message.channel.send(embed=embed)

    @commands.group()
    async def sticker(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

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
    async def edit(self, ctx, name, url):
        before = await self.sticker_list.find_one_and_update({"name": name, "author_id": ctx.author.id}, {"$set": {"url": url}})
        if before is None:
            await ctx.send(f"Cannot edit sticker.\nEither sticker doesn't exist or you are not the creator of the sticker.")
        else:
            await ctx.send(f"Sticker {name} edited.")

    @sticker.command()
    async def delete(self, ctx, name):
        result = await self.sticker_list.delete_one({"name": name, "author_id": ctx.author.id})
        if result.deleted_count > 0:
            await ctx.send(f"Sticker {name} deleted.")
        else:
            await ctx.send(f"Cannot delete sticker.\nEither sticker doesn't exist or you are not the creator of the sticker.")

    @sticker.command()
    async def find(self, ctx, name):
        sticker_names = await self.sticker_list.distinct("name", {})
        relevant = process.extract(name, sticker_names, limit=10)
        text = "\n".join((f"{r[0]} ({r[1]}%)" for r in relevant if r[1]>50))
        await ctx.send(f"Result:\n```\n{text}\n```")

    @sticker.command()
    @checks.guild_only()
    @checks.manager_only()
    async def ban(self, ctx, name):
        await self.sticker_list.update_one({"name": name}, {"$addToSet": {"banned_guilds": ctx.guild.id}})
        await ctx.confirm()

    @sticker.command()
    @checks.guild_only()
    @checks.manager_only()
    async def unban(self, ctx, name):
        result = await self.sticker_list.update_one({"name": name}, {"$pull": {"banned_guilds": ctx.guild.id}})
        if result.modified_count > 0:
            await ctx.confirm()
        else:
            await ctx.deny()

    @sticker.command()
    async def banlist(self, ctx):
        banned_stickers = await self.sticker_list.distinct("name", {"banned_guilds": {"$eq": ctx.guild.id}})
        if banned_stickers:
            embeds = utils.page_format(banned_stickers, 10, title="Banned stickers for this server", description=lambda i, x: f"`{i+1}.` {x}")
            await ctx.embed_page(embeds)
        else:
            await ctx.send("There's no banned sticker.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Sticker(bot))
