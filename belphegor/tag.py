import discord
from discord.ext import commands
from fuzzywuzzy import process

#==================================================================================================================================================

class Tag:
    def __init__(self, bot):
        self.bot = bot
        self.tag_list = bot.db.tag_list

    @commands.group(name="tag", invoke_without_command=True)
    async def tag_cmd(self, ctx, *, name):
        if ctx.invoked_subcommand is None:
            tag = await self.tag_list.find_one({"name": name})
            if tag is None:
                await ctx.send(f"Cannot find tag {name} in database.")
            else:
                alias_of = tag.get("alias_of", None)
                if alias_of is not None:
                    tag = await self.tag_list.find_one({"name": alias_of})
                await ctx.send(tag["content"])

    @tag_cmd.command()
    async def create(self, ctx, name, *, content):
        value = {"name": name, "content": content, "author_id": ctx.author.id}
        before = await self.tag_list.find_one_and_update({"name": name.strip()}, {"$setOnInsert": value}, upsert=True)
        if before is not None:
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
        tag_alias_of = await self.tag_list.find_one({"name": alias_of})
        if tag_alias_of is not None:
            alias_of = tag_alias_of.get("alias_of", alias_of)
        else:
            return await ctx.send(f"Tag {alias_of} doesn't exist.")
        value = {"name": name, "alias_of": alias_of, "author_id": ctx.author.id}
        before = await self.tag_list.find_one_and_update({"name": name}, {"$setOnInsert": value}, upsert=True)
        if before is not None:
            await ctx.send(f"Cannot create already existed tag.")
        else:
            await self.tag_list.update_one({"name": alias_of, "aliases": {"$nin": [name]}}, {"$push": {"aliases": name}})
            await ctx.send(f"Tag alias {name} for {alias_of} created.")

    @tag_cmd.command()
    async def delete(self, ctx, *, name):
        before = await self.tag_list.find_one_and_delete({"name": name, "author_id": ctx.author.id})
        if before is not None:
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

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Tag(bot))
