from discord.ext import commands
from . import config

def owner_only():
    return commands.check(lambda ctx:ctx.author.id==config.OWNER_ID)

def nsfw():
    return commands.check(lambda ctx:ctx.channel.nsfw)

def otogi_guild_only():
	return commands.check(lambda ctx:ctx.guild.id==config.OTOGI_GUILD_ID or ctx.message.author.id==config.OWNER_ID)

def manager_only():
    return commands.check(lambda ctx:ctx.channel.permissions_for(ctx.message.author).manage_guild)

def role_manager_only():
    return commands.check(lambda ctx:ctx.channel.permissions_for(ctx.message.author).manage_roles)

def creampie_guild_only():
    return commands.check(lambda ctx:ctx.guild.id==config.CREAMPIE_GUILD_ID)