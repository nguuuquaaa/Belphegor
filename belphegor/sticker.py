import discord
from discord.ext import commands
import re
from fuzzywuzzy import process
from . import utils
from .utils import checks
import pymongo

#==================================================================================================================================================

DEFAULT_PREFIX_REGEX = re.compile(r"(?<=\$)\w+")
NO_SPACE_REGEX = re.compile(r"\S+")
NO_WORD_REGEX = re.compile(r"\W+")

#==================================================================================================================================================

class Sticker:
    def __init__(self, bot):
        self.bot = bot
        self.sticker_list = self.bot.db.sticker_list
        self.guild_data = bot.db.guild_data
        self.sticker_regexes = {}
        bot.loop.create_task(self.get_all_prefixes())

    async def get_all_prefixes(self):
        async for data in self.guild_data.find(
            {"sticker_prefix": {"$exists": True}},
            projection={"_id": False, "guild_id": True, "sticker_prefix": True}
        ):
            self.sticker_regexes[data["guild_id"]] = re.compile(fr"(?<={re.escape(data['sticker_prefix'])})\w+")

    async def on_message(self, message):
        if message.author.bot:
            return
        result = self.sticker_regexes.get(getattr(message.guild, "id", None), DEFAULT_PREFIX_REGEX).findall(message.content)
        query = {"name": {"$in": result}}
        if message.guild:
            query["banned_guilds"] = {"$not": {"$eq": message.guild.id}}
        st = await self.sticker_list.find_one_and_update(query, {"$inc": {"uses": 1}}, projection={"_id": False, "url": True})
        if st:
            embed = discord.Embed()
            embed.set_image(url=st["url"])
            await message.channel.send(embed=embed)

    @commands.group()
    async def sticker(self, ctx):
        '''
            `>>sticker`
            Base command. Does nothing, but with subcommands can be used to set and view stickers.
        '''
        if ctx.invoked_subcommand is None:
            pass

    @sticker.command()
    async def add(self, ctx, name, url):
        '''
            `>>sticker add <name> <url>`
            Add a sticker.
            Name can't contain spaces.
        '''
        name = NO_WORD_REGEX.sub("", name)
        if url.startswith(("https://", "http://")):
            value = {"name": name, "url": url, "author_id": ctx.author.id, "uses": 0}
            before = await self.sticker_list.find_one_and_update({"name": name}, {"$setOnInsert": value}, upsert=True)
            if before is not None:
                await ctx.send("Cannot add already existed sticker.")
            else:
                await ctx.send(f"Sticker {name} added.")
        else:
            await ctx.send("Url should start with http or https.")

    @sticker.command()
    async def edit(self, ctx, name, url):
        '''
            `>>sticker edit <name> <url>`
            Edit a sticker you own.
        '''
        before = await self.sticker_list.find_one_and_update({"name": name, "author_id": ctx.author.id}, {"$set": {"url": url}})
        if before is None:
            await ctx.send(f"Cannot edit sticker.\nEither sticker doesn't exist or you are not the creator of the sticker.")
        else:
            await ctx.send(f"Sticker {name} edited.")

    @sticker.command()
    async def delete(self, ctx, name):
        '''
            `>>sticker delete <name>`
            Delete a sticker you own.
        '''
        result = await self.sticker_list.delete_one({"name": name, "author_id": ctx.author.id})
        if result.deleted_count > 0:
            await ctx.send(f"Sticker {name} deleted.")
        else:
            await ctx.send(f"Cannot delete sticker.\nEither sticker doesn't exist or you are not the creator of the sticker.")

    @sticker.command(name="list")
    async def cmd_sticker_list(self, ctx, user: discord.User=None):
        '''
            `>>sticker list <optional: user>`
            Get all stickers created by <user>.
            If no user is provided, get all stickers you created.
        '''
        target = user or ctx.author
        sticker_names = await self.sticker_list.distinct("name", {"author_id": target.id})
        if sticker_names:
            paging = utils.Paginator(
                sticker_names, 10,
                title=f"All stickers by {target.display_name}",
                description=lambda i, x: f"`{i+1}.` {x}",
                colour=discord.Colour.green()
            )
            await paging.navigate(ctx)
        else:
            await ctx.send("You haven't created any sticker.")

    @sticker.command()
    async def find(self, ctx, name):
        '''
            `>>sticker find <name>`
            Find stickers.
        '''
        sticker_names = await self.sticker_list.distinct("name", {})
        relevant = process.extract(name, sticker_names, limit=10)
        text = "\n".join((f"{r[0]} ({r[1]}%)" for r in relevant if r[1]>50))
        await ctx.send(embed=discord.Embed(title="Result:", description=text, colour=discord.Colour.green()))

    @sticker.command()
    @checks.guild_only()
    @checks.manager_only()
    async def ban(self, ctx, name):
        '''
            `>>sticker ban <name>`
            Ban a sticker in current guild.
        '''
        result = await self.sticker_list.update_one({"name": name}, {"$addToSet": {"banned_guilds": ctx.guild.id}})
        if result.matched_count > 0:
            await ctx.confirm()
        else:
            await ctx.deny()

    @sticker.command()
    @checks.guild_only()
    @checks.manager_only()
    async def unban(self, ctx, name):
        '''
            `>>sticker unban <name>`
            Unban a sticker in current guild.
        '''
        result = await self.sticker_list.update_one({"name": name}, {"$pull": {"banned_guilds": ctx.guild.id}})
        if result.matched_count > 0:
            await ctx.confirm()
        else:
            await ctx.deny()

    @sticker.command()
    async def banlist(self, ctx):
        '''
            `>>sticker banlist`
            Display current guild's sticker ban list.
        '''
        banned_stickers = await self.sticker_list.distinct("name", {"banned_guilds": ctx.guild.id})
        if banned_stickers:
            paging = utils.Paginator(
                banned_stickers, 10,
                title="Banned stickers for this server",
                description=lambda i, x: f"`{i+1}.` {x}"
            )
            await paging.navigate(ctx)
        else:
            await ctx.send("This server has no banned sticker.")

    @sticker.command()
    @checks.guild_only()
    async def prefix(self, ctx, *, new_prefix=None):
        '''
            `>>sticker prefix <optional: prefix>`
            If <prefix> is provided, set server prefix to it. Server manager only.
            If <prefix> is not provided, display current server's prefix. Public use.
        '''
        if new_prefix is None:
            guild_data = await self.guild_data.find_one({"guild_id": ctx.guild.id}, projection={"_id": False, "sticker_prefix": True})
            await ctx.send(f"Prefix is {guild_data.get('sticker_prefix', '$')}")
        elif ctx.channel.permissions_for(ctx.message.author).manage_guild:
            if new_prefix == "$":
                self.sticker_regexes.pop(ctx.guild.id, None)
                await self.guild_data.update_one(
                    {"guild_id": ctx.guild.id},
                    {"$unset": {"sticker_prefix": None}}
                )
                await ctx.confirm()
            elif NO_SPACE_REGEX.fullmatch(new_prefix):
                self.sticker_regexes[ctx.guild.id] = re.compile(fr"(?<={re.escape(new_prefix)})\w+")
                await self.guild_data.update_one(
                    {"guild_id": ctx.guild.id},
                    {"$set": {"sticker_prefix": new_prefix}}
                )
                await ctx.confirm()
            else:
                await ctx.send(f"Prefix cannot contain spaces.")
        else:
            await ctx.send("This action is usable by server managers only.")

    @sticker.command(name="info")
    async def cmd_sticker_info(self, ctx, name):
        '''
            `>>sticker info <name>`
            Display sticker info.
        '''
        data = await self.sticker_list.find_one({"name": name})
        if data:
            embed = discord.Embed(title="Info", colour=discord.Colour.green())
            if getattr(ctx.guild, "id", None) in data.get("banned_guilds", ()):
                embed.description = "Banned in this server."
            embed.add_field(name="Name", value=f"[{name}]({data['url']})", inline=False)
            embed.add_field(name="Author", value=f"<@{data['author_id']}>")
            embed.add_field(name="Uses", value=data.get("uses", 0))
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Can't find sticker with name {name}.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Sticker(bot))
