from discord.ext import commands
from . import config
import json

with open(f"{config.data_path}/adventure/S-Rank.json", encoding="utf-8") as file:
    s_rank_adventures = json.load(file)

def owner_only():
    return commands.check(lambda ctx:ctx.author.id==config.owner_id)

def srank_only():
    return commands.check(lambda ctx:ctx.author.id in s_rank_adventures)

def nsfw():
    return commands.check(lambda ctx:ctx.channel.name.startswith("nsfw"))

def otogi_guild_only():
	return commands.check(lambda ctx:ctx.guild.id==config.otogi_guild_id or ctx.message.author.id==config.owner_id)

def manager_only():
    return commands.check(lambda ctx:ctx.channel.permissions_for(ctx.message.author).manage_guild)

def role_manager_only():
    return commands.check(lambda ctx:ctx.channel.permissions_for(ctx.message.author).manage_roles)

def creampie_guild_only():
    return commands.check(lambda ctx:ctx.guild.id==config.creampie_guild_id)