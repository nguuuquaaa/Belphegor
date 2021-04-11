from discord.ext import commands
from . import config
import asyncio

#==================================================================================================================================================

class CheckFailure(commands.CheckFailure):
    pass

class NSFW(CheckFailure):
    pass

class CertainGuild(CheckFailure):
    def __init__(self, guild_id, *args):
        self.guild_id = guild_id
        super().__init__(*args)

class CertainGuilds(CheckFailure):
    def __init__(self, guild_ids, *args):
        self.guild_ids = guild_ids
        super().__init__(*args)

class MissingPerms(CheckFailure):
    def __init__(self, perms, *args):
        self.perms = perms
        super().__init__(*args)

class CustomError(commands.CommandError):
    pass

#==================================================================================================================================================

def owner_only():
    def check_owner_only(ctx):
        if ctx.author.id==config.OWNER_ID:
            return True
        else:
            raise commands.NotOwner("This command can only be used by owner.")
    return commands.check(check_owner_only)

def nsfw():
    def check_nsfw(ctx):
        if ctx.guild is None:
            raise NSFW("Sorry, no porn in DM.")
        elif ctx.channel.nsfw or ctx.channel.name.startswith("nsfw-"):
            return True
        else:
            raise NSFW("This command can only be used in nsfw channels.")
    return commands.check(check_nsfw)

def guild_only():
    def check_no_dm(ctx):
        if ctx.guild:
            return True
        else:
            raise commands.NoPrivateMessage("This command cannot be used in DM.")
    return commands.check(check_no_dm)

def in_certain_guild(gid):
    def check_in_certain_guild(ctx):
        if ctx.guild and ctx.guild.id == gid:
            return True
        else:
            g = ctx.bot.get_guild(gid)
            raise CertainGuild(gid, f"This command can only be used in {g.name} server.")
    return commands.check(check_in_certain_guild)

def in_certain_guilds(*gids):
    def check_in_certain_guilds(ctx):
        if ctx.guild and ctx.guild.id in gids:
            return True
        else:
            raise CertainGuilds(gids, f"This command can only be used in certain servers.")
    return commands.check(check_in_certain_guilds)

def otogi_guild_only():
    return in_certain_guild(config.OTOGI_GUILD_ID)

def creampie_guild_only():
    return in_certain_guild(config.CREAMPIE_GUILD_ID)

def manager_only():
    def check_guild_manager(ctx):
        if ctx.channel.permissions_for(ctx.message.author).manage_guild:
            return True
        else:
            raise MissingPerms("manage_guild", "This command can only be used by server managers.")
    return commands.check(check_guild_manager)

def can_kick():
    def check_can_kick(ctx):
        if ctx.channel.permissions_for(ctx.message.author).kick_members:
            return True
        else:
            raise MissingPerms("kick_members", "You don't have kick members permission.")
    return commands.check(check_can_kick)

def can_ban():
    def check_can_ban(ctx):
        if ctx.channel.permissions_for(ctx.message.author).ban_members:
            return True
        else:
            raise MissingPerms("ban_members", "You don't have ban members permission.")
    return commands.check(check_can_ban)
