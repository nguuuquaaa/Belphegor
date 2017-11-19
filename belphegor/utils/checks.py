from discord.ext import commands
from . import config

def owner_only():
    async def check_owner(ctx):
        if ctx.author.id==config.OWNER_ID:
            return True
        else:
            await ctx.send("This command can only be used by owner.")
            return False
    return commands.check(check_owner)

def nsfw():
    async def check_nsfw(ctx):
        if ctx.channel.nsfw:
            return True
        else:
            await ctx.send("This command can only be used in nsfw channels.")
            return False
    return commands.check(check_nsfw)

def otogi_guild_only():
    async def check_otogi_guild(ctx):
        if ctx.guild.id==config.OTOGI_GUILD_ID or ctx.author.id==config.OWNER_ID:
            return True
        else:
            await ctx.send("This command can only be used in Otogi: Spirit Agents server.")
            return False
    return commands.check(check_otogi_guild)

def manager_only():
    async def check_manager(ctx):
        if ctx.channel.permissions_for(ctx.message.author).manage_guild:
            return True
        else:
            await ctx.send("This command can only be used by server managers.")
            return False
    return commands.check(check_manager)

def can_kick():
    async def check_kick(ctx):
        if ctx.channel.permissions_for(ctx.message.author).kick_members:
            return True
        else:
            await ctx.send("You don't have Kick members permission.")
            return False
    return commands.check(check_kick)

def can_ban():
    async def check_ban(ctx):
        if ctx.channel.permissions_for(ctx.message.author).ban_members:
            return True
        else:
            await ctx.send("You don't have Ban members permission.")
            return False
    return commands.check(check_ban)

def creampie_guild_only():
    async def check_creampie_guild(ctx):
        if ctx.guild.id==config.CREAMPIE_GUILD_ID:
            return True
        else:
            await ctx.send("This command can only be used in ༺çɾҽąണքìҽ༻ server.")
            return False
    return commands.check(check_creampie_guild)

def guild_only():
    async def check_guild_only(ctx):
        if ctx.guild:
            return True
        else:
            await ctx.send("This command cannot be used in DM.")
            return False
    return commands.check(check_guild_only)
