import discord
from discord.ext import commands
from . import utils
from .utils import checks, modding
from rapidfuzz import process

#==================================================================================================================================================

class Tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tag_list = bot.db.tag_list

    async def get_tag(self, name, guild, *, update=False):
        if update:
            tag = await self.tag_list.find_one_and_update({"guild_id": guild.id, "name": name}, {"$inc": {"uses": 1}})
        else:
            tag = await self.tag_list.find_one({"guild_id": guild.id, "name": name})
        if tag:
            alias_of = tag.get("alias_of", None)
            if alias_of:
                if update:
                    tag = await self.tag_list.find_one_and_update({"guild_id": guild.id, "name": alias_of}, {"$inc": {"uses": 1}})
                else:
                    tag = await self.tag_list.find_one({"guild_id": guild.id, "name": alias_of})
        return tag

    @modding.help(brief="Get tag with given name", category="Tag & sticker", field="Commands", paragraph=0)
    @commands.group(name="tag", invoke_without_command=True)
    @checks.guild_only()
    async def tag_cmd(self, ctx, *, name):
        '''
            `>>tag <name>`
            Display a tag.
        '''
        tag = await self.get_tag(name, ctx.guild, update=True)
        if tag is None:
            await ctx.send(f"Cannot find tag {name} in database.")
        else:
            await ctx.send(tag["content"])

    @modding.help(brief="Create a tag", category="Tag & sticker", field="Commands", paragraph=0)
    @tag_cmd.command()
    @checks.guild_only()
    async def create(self, ctx, name, *, content):
        '''
            `>>tag create <name> <content>`
            Create a tag.
            If name contains spaces, it must be enclosed in double quotes.
        '''
        value = {"guild_id": ctx.guild.id, "name": name.strip(), "content": content, "author_id": ctx.author.id}
        before = await self.tag_list.find_one_and_update({"guild_id": ctx.guild.id, "name": name.strip()}, {"$setOnInsert": value}, upsert=True)
        if before:
            await ctx.send(f"Cannot create already existed tag.")
        else:
            await ctx.send(f"Tag {name} created.")

    @modding.help(brief="Edit a tag", category="Tag & sticker", field="Commands", paragraph=0)
    @tag_cmd.command()
    @checks.guild_only()
    async def edit(self, ctx, name, *, content):
        '''
            `>>tag edit <name> <content>`
            Edit a tag you own.
            If name contains spaces, it must be enclosed in double quotes.
        '''
        before = await self.tag_list.find_one_and_update(
            {"guild_id": ctx.guild.id, "name": name.strip(), "author_id": ctx.author.id, "content": {"$exists": True}},
            {"$set": {"content": content}}
        )
        if before is None:
            await ctx.send(f"Cannot edit tag.\nEither tag doesn't exist, tag is an alias or you are not the creator of the tag.")
        else:
            await ctx.send(f"Tag {name} edited.")

    @modding.help(brief="Add an alias to another tag", category="Tag & sticker", field="Commands", paragraph=0)
    @tag_cmd.command()
    @checks.guild_only()
    async def alias(self, ctx, name, *, alias_of):
        '''
            `>>tag alias <alias> <name>`
            Create an alias for a tag.
            If alias contains spaces, it must be enclosed in double quotes.
        '''
        base_tag = await self.get_tag(alias_of, ctx.guild)
        if base_tag:
            alias_of = base_tag["name"]
        else:
            return await ctx.send(f"Tag {alias_of} doesn't exist.")
        value = {"guild_id": ctx.guild.id, "name": name, "alias_of": alias_of, "author_id": ctx.author.id}
        before = await self.tag_list.find_one_and_update({"guild_id": ctx.guild.id, "name": name}, {"$setOnInsert": value}, upsert=True)
        if before:
            await ctx.send(f"Cannot create already existed tag.")
        else:
            await self.tag_list.update_one({"guild_id": ctx.guild.id, "name": alias_of, "aliases": {"$nin": [name]}}, {"$push": {"aliases": name}})
            await ctx.send(f"Tag alias {name} for {alias_of} created.")

    @modding.help(brief="Delete a tag", category="Tag & sticker", field="Commands", paragraph=0)
    @tag_cmd.command()
    @checks.guild_only()
    async def delete(self, ctx, *, name):
        '''
            `>>tag delete <name>`
            Delete a tag you own.
            Server managers can still delete other people' tags.
        '''
        if ctx.channel.permissions_for(ctx.author).manage_guild:
            q = {}
        else:
            q = {"author_id": ctx.author.id}
        q.update({"guild_id": ctx.guild.id, "name": name})
        before = await self.tag_list.find_one_and_delete(q)
        if before:
            aliases = before.get("aliases")
            if aliases:
                await self.tag_list.delete_many({"guild_id": ctx.guild.id, "name": {"$in": aliases}})
                await ctx.send(f"Tag {name} and its aliases deleted.")
            else:
                await ctx.send(f"Tag {name} deleted.")
        else:
            await ctx.send(f"Cannot delete tag.\nEither tag doesn't exist or you are not the creator of the tag.")

    @modding.help(brief="Find tags", category="Tag & sticker", field="Commands", paragraph=0)
    @tag_cmd.command()
    @checks.guild_only()
    async def find(self, ctx, *, name):
        '''
            `>>tag find <name>`
            Find tags with given name.
        '''
        tag_names = await self.tag_list.distinct("name", {"guild_id": ctx.guild.id})
        relevant = process.extract(name, tag_names, limit=10)
        text = "\n".join((f"{r[0]} ({r[1]}%)" for r in relevant if r[1]>50))
        await ctx.send(f"Result:\n```\n{text}\n```")

    @modding.help(brief="Display all tags in current server", category="Tag & sticker", field="Commands", paragraph=0)
    @tag_cmd.command(name="all")
    @checks.guild_only()
    async def cmd_tag_all(self, ctx):
        '''
            `>>tag all`
            Display current server's all tags.
        '''
        tags = await self.tag_list.distinct("name", {"guild_id": ctx.guild.id})
        if tags:
            paging = utils.Paginator(
                tags, 10,
                title=f"All ({len(tags)}) tags for this server",
                description=lambda i, x: f"`{i+1}.` {x}",
                colour=discord.Colour.blue()
            )
            await paging.navigate(ctx)
        else:
            await ctx.send("This server has no tag.")

    @modding.help(brief="Display all tags by member", category="Tag & sticker", field="Commands", paragraph=0)
    @tag_cmd.command(name="list")
    @checks.guild_only()
    async def cmd_tag_list(self, ctx, member: discord.Member=None):
        '''
            `>>tag list <optional: member>`
            Get all stickers created by <member> in this server.
            If no member is provided, get all stickers you created.
        '''
        target = member or ctx.author
        tag_names = await self.tag_list.distinct("name", {"guild_id": ctx.guild.id, "author_id": target.id})
        if tag_names:
            paging = utils.Paginator(
                tag_names, 10,
                title=f"All tags by {target.display_name}",
                description=lambda i, x: f"`{i+1}.` {x}",
                colour=discord.Colour.blue()
            )
            await paging.navigate(ctx)
        else:
            await ctx.send("You haven't created any tag.")

    @modding.help(brief="Display tag info", category="Tag & sticker", field="Commands", paragraph=0)
    @tag_cmd.command(name="info")
    @checks.guild_only()
    async def cmd_tag_info(self, ctx, *, name):
        '''
            `>>tag info <name>`
            Display tag info.
        '''
        data = await self.tag_list.find_one({"guild_id": ctx.guild.id, "name": name})
        if data:
            embed = discord.Embed(title="Info", colour=discord.Colour.blue())
            embed.add_field(name="Name", value=name, inline=False)
            embed.add_field(name="Author", value=f"<@{data['author_id']}>")
            original = data.get("alias_of")
            if original:
                embed.add_field(name="Alias of", value=original)
            else:
                embed.add_field(name="Uses", value=data.get("uses", 0))
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Can't find tag with name {name}.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Tag(bot))
