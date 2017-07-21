from discord.ext import commands
from . import config
import codecs

def owner_only():
    return commands.check(lambda ctx:ctx.message.author.id==config.owner_id)

def is_srank(ctx):
    with codecs.open(f"{config.adventure_path}config/S-Rank.txt", encoding="utf-8") as file:
        s_rank_adventurers = [int(l.rstrip()) for l in file.readlines()]
        return ctx.message.author.id in s_rank_adventurers
    return False

def srank_only():
    return commands.check(is_srank)

def nsfw():
    return commands.check(lambda ctx:ctx.message.channel.name.startswith("nsfw"))
	
def otogi_guild_only():
	return commands.check(lambda ctx:ctx.message.guild.id==config.otogi_guild_id or ctx.message.author.id==config.owner_id)
