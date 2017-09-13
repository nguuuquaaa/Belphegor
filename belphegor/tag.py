import discord
from discord.ext import commands
import re
import os
import json
from .utils import config, format
from urllib.parse import quote
import time
from fuzzywuzzy import process

#==================================================================================================================================================

class TagBot:
    def __init__(self, bot):
        self.bot = bot
        self.tags = {}
        for filename in os.listdir(f"{config.data_path}/tags"):
            if filename.endswith(".json"):
                with open(f"{config.data_path}/tags/{filename}", encoding="utf-8") as file:
                    cur_tag = json.load(file)
                    self.tags[cur_tag["name"]] = cur_tag

    def save(self, tag):
        with open(f"{config.data_path}/tags/{tag['filename']}.json", "w+", encoding="utf-8") as file:
            json.dump(tag, file, indent=4, ensure_ascii=False)

    @commands.group(name="tag", invoke_without_command=True)
    async def tag_cmd(self, ctx, *, name):
        if ctx.invoked_subcommand is None:
            tag = self.tags.get(name, None)
            if tag is None:
                relevant = process.extract(name, self.tags.keys(), limit=5)
                text = "\n".join([r[0] for r in relevant if r[1]>50])
                await ctx.send(f"Cannot find {name} in database.\nDo you mean:\n```\n{text}\n```")
            else:
                if tag.get("alias_of", None) is not None:
                    tag = self.tags[tag["alias_of"]]
                await ctx.send(tag["content"])

    @tag_cmd.command()
    async def create(self, ctx, *, data):
        data = data.strip().partition("\n")
        name = data[0]
        content = data[2]
        if len(name) > 30:
            await ctx.send("Tag name too long.")
        elif name in self.tags.keys():
            await ctx.send("Tag already existed.")
        else:
            new_tag = {"name": name, "content": content, "creator_id": ctx.author.id, "filename": "_".join([f"{ord(c):x}" for c in name])}
            self.tags[name] = new_tag
            self.save(new_tag)
            await ctx.send(f"Tag {name} created.")

    @tag_cmd.command()
    async def edit(self, ctx, *, data):
        data = data.strip().partition("\n")
        name = data[0]
        content = data[2]
        tag = self.tags.get(name, None)
        if tag is None:
            await ctx.send(f"Cannot find {name} in database.")
        elif tag.get("alias_of", None) is not None:
            await ctx.send(f"Cannot edit tag alias.")
        elif ctx.author.id != tag["creator_id"]:
            await ctx.send("You are not the creator of tag {name}.")
        else:
            tag["content"] = content
            self.save(tag)
            await ctx.send(f"Tag {name} edited.")

    @tag_cmd.command()
    async def append(self, ctx, *, data):
        data = data.strip().partition("\n")
        name = data[0]
        content = data[2]
        tag = self.tags.get(name, None)
        if tag is None:
            await ctx.send(f"Cannot find {name} in database.")
        elif tag.get("alias_of", None) is not None:
            await ctx.send(f"Cannot edit tag alias.")
        elif ctx.author.id != tag["creator_id"]:
            await ctx.send("You are not the creator of tag {name}.")
        else:
            tag["content"] = f"{tag['content']} {content}"
            self.save(tag)
            await ctx.send(f"Tag {name} edited.")

    @tag_cmd.command()
    async def alias(self, ctx, *, data):
        data = data.strip().partition("\n")
        alias_name = data[0]
        name = data[2]
        if len(alias_name) > 30:
            await ctx.send("Tag name too long.")
        if alias_name in self.tags.keys():
            await ctx.send("Tag already existed.")
        elif name not in self.tags.keys():
            await ctx.send("Target tag doesn't exist.")
        else:
            tag = self.tags.get(name, None)
            if tag.get("alias_of", None) is not None:
                tag = self.tags[tag["alias_of"]]
            if tag.get("aliases", None) is None:
                tag["aliases"] = [alias_name,]
            else:
                tag["aliases"].append(alias_name)
            self.save(tag)
            new_tag = {"name": alias_name, "alias_of": name, "creator_id": ctx.author.id, "filename": "_".join([f"{ord(c):x}" for c in alias_name])}
            self.tags[alias_name] = new_tag
            self.save(new_tag)
            await ctx.send(f"Tag alias {alias_name} created.")

    @tag_cmd.command()
    async def delete(self, ctx, *, name):
        tag = self.tags.get(name, None)
        if tag is None:
            await ctx.send(f"Cannot find {name} in database.")
        elif ctx.author.id != tag["creator_id"]:
            await ctx.send("You are not the creator of tag {name}.")
        else:
            tag = self.tags.pop(name)
            os.remove(f"{config.data_path}/tags/{tag['filename']}.json")
            for alias_tag_name in tag.get("aliases", []):
                alias_tag = self.tags.pop(alias_tag_name)
                os.remove(f"{config.data_path}/tags/{alias_tag['filename']}.json")
            if tag.get("alias_of", None) is not None:
                root_tag = self.tags[tag["alias_of"]]
                root_tag["aliases"].remove(name)
                self.save(root_tag)
            await ctx.send(f"Tag {name} deleted.")

    @tag_cmd.command(name="find")
    async def tag_find(self, ctx, *, name):
        relevant = process.extract(name, self.tags.keys(), limit=10)
        text = "\n".join([r[0] for r in relevant if r[1]>50])
        await ctx.send(f"Result:\n```\n{text}\n```")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(TagBot(bot))