from discord.ext import commands
from . import config

def check_owner(ctx):
    return ctx.author.id==config.OWNER_ID

def owner_only():
    return commands.check(check_owner)

def check_nsfw(ctx):
    return ctx.channel.nsfw

def nsfw():
    return commands.check(check_nsfw)

def check_otogi_guild(ctx):
    return ctx.guild.id==config.OTOGI_GUILD_ID or ctx.author.id==config.OWNER_ID

def otogi_guild_only():
	return commands.check(check_otogi_guild)

def check_manager(ctx):
    return ctx.channel.permissions_for(ctx.message.author).manage_guild

def manager_only():
    return commands.check(check_manager)

def check_creampie_guild(ctx):
    return ctx.guild.id==config.CREAMPIE_GUILD_ID

def creampie_guild_only():
    return commands.check(check_creampie_guild)