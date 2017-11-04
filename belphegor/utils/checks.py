from discord.ext import commands
from . import config

async def check_owner(ctx):
    if ctx.author.id==config.OWNER_ID:
        return True
    else:
        await ctx.send("This command can only be used by owner.")
        return False

def owner_only():
    return commands.check(check_owner)

async def check_nsfw(ctx):
    if ctx.channel.nsfw:
        return True
    else:
        await ctx.send("This command can only be used in nsfw channels.")
        return False

def nsfw():
    return commands.check(check_nsfw)

async def check_otogi_guild(ctx):
    if ctx.guild.id==config.OTOGI_GUILD_ID or ctx.author.id==config.OWNER_ID:
        return True
    else:
        await ctx.send("This command can only be used in Otogi: Spirit Agents server.")
        return False

def otogi_guild_only():
	return commands.check(check_otogi_guild)

async def check_manager(ctx):
    if ctx.channel.permissions_for(ctx.message.author).manage_guild:
        return True
    else:
        await ctx.send("This command can only be used by server managers.")
        return False

def manager_only():
    return commands.check(check_manager)

async def check_creampie_guild(ctx):
    if ctx.guild.id==config.CREAMPIE_GUILD_ID:
        return True
    else:
        await ctx.send("This command can only be used in ༺çɾҽąണքìҽ༻ server.")
        return False

def creampie_guild_only():
    return commands.check(check_creampie_guild)

async def check_guild_only(ctx):
    if ctx.guild:
        return True
    else:
        await ctx.send("This command cannot be used in DM.")
        return False

def guild_only():
    return commands.check(check_guild_only)