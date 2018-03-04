import discord
from discord.ext import commands
from fuzzywuzzy import process
from . import utils
from .utils import checks

#==================================================================================================================================================

class Tag:
    def __init__(self, bot):
        self.bot = bot
        self.tag_list = bot.db.tag_list

    async def get_tag(self, name):
        tag = await self.tag_list.find_one({"name": name})
        if tag:
            alias_of = tag.get("alias_of", None)
            if alias_of:
                tag = await self.tag_list.find_one({"name": alias_of})
        return tag

    @commands.group(name="tag", invoke_without_command=True)
    async def tag_cmd(self, ctx, *, name):
        if ctx.invoked_subcommand is None:
            tag = await self.get_tag(name)
            if tag is None:
                await ctx.send(f"Cannot find tag {name} in database.")
            else:
                if ctx.guild:
                    if ctx.guild.id in tag.get("banned_guilds", []):
                        return await ctx.send("This tag is banned in this server.")
                await ctx.send(tag["content"])

    @tag_cmd.command()
    async def create(self, ctx, name, *, content):
        value = {"name": name, "content": content, "author_id": ctx.author.id}
        before = await self.tag_list.find_one_and_update({"name": name.strip()}, {"$setOnInsert": value}, upsert=True)
        if before:
            await ctx.send(f"Cannot create already existed tag.")
        else:
            await ctx.send(f"Tag {name} created.")

    @tag_cmd.command()
    async def edit(self, ctx, name, *, content):
        before = await self.tag_list.find_one_and_update({"name": name.strip(), "author_id": ctx.author.id, "content": {"$exists": True}}, {"$set": {"content": content}})
        if before is None:
            await ctx.send(f"Cannot edit tag.\nEither tag doesn't exist, tag is an alias or you are not the creator of the tag.")
        else:
            await ctx.send(f"Tag {name} edited.")

    @tag_cmd.command()
    async def alias(self, ctx, name, *, alias_of):
        base_tag = await self.get_tag(alias_of)
        if base_tag:
            alias_of = base_tag["name"]
        else:
            return await ctx.send(f"Tag {alias_of} doesn't exist.")
        value = {"name": name, "alias_of": alias_of, "author_id": ctx.author.id}
        before = await self.tag_list.find_one_and_update({"name": name}, {"$setOnInsert": value}, upsert=True)
        if before:
            await ctx.send(f"Cannot create already existed tag.")
        else:
            await self.tag_list.update_one({"name": alias_of, "aliases": {"$nin": [name]}}, {"$push": {"aliases": name}})
            await ctx.send(f"Tag alias {name} for {alias_of} created.")

    @tag_cmd.command()
    async def delete(self, ctx, *, name):
        before = await self.tag_list.find_one_and_delete({"name": name, "author_id": ctx.author.id})
        if before:
            aliases = before.get("aliases", [])
            if aliases:
                await self.tag_list.delete_many({"name": {"$in": aliases}})
            await ctx.send(f"Tag {name} and its aliases deleted.")
        else:
            await ctx.send(f"Cannot delete tag.\nEither tag doesn't exist or you are not the creator of the tag.")

    @tag_cmd.command()
    async def find(self, ctx, *, name):
        tag_names = await self.tag_list.distinct("name", {})
        relevant = process.extract(name, tag_names, limit=10)
        text = "\n".join((f"{r[0]} ({r[1]}%)" for r in relevant if r[1]>50))
        await ctx.send(f"Result:\n```\n{text}\n```")

    @tag_cmd.command()
    @checks.guild_only()
    @checks.manager_only()
    async def ban(self, ctx, *, name):
        tag = await self.get_tag(name)
        await self.tag_list.update_one({"name": tag["name"]}, {"$addToSet": {"banned_guilds": ctx.guild.id}})
        await ctx.confirm()

    @tag_cmd.command()
    @checks.guild_only()
    @checks.manager_only()
    async def unban(self, ctx, *, name):
        tag = await self.get_tag(name)
        result = await self.tag_list.update_one({"name": tag["name"]}, {"$pull": {"banned_guilds": ctx.guild.id}})
        if result.modified_count > 0:
            await ctx.confirm()
        else:
            await ctx.deny()

    @tag_cmd.command()
    async def banlist(self, ctx):
        banned_tags = [tag async for tag in self.tag_list.find({"banned_guilds": {"$eq": ctx.guild.id}})]
        if banned_tags:
            embeds = utils.embed_page_format(banned_tags, 10, title="Banned tags for this server", description=lambda i, x: f"`{i+1}.` {', '.join([x['name']]+x.get('aliases', []))}")
            await ctx.embed_page(embeds)
        else:
            await ctx.send("There's no banned tag.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Tag(bot))
