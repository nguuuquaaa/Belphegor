from discord.ext import commands
from . import config
import asyncio

#==================================================================================================================================================

def create_task(coro, *, loop=None):
    _loop = loop or asyncio.get_event_loop()
    _loop.create_task(coro)

def do_after(coro, wait_time, *, loop=None):
    async def things_to_do():
        await asyncio.sleep(wait_time)
        await coro
    create_task(things_to_do(), loop=loop)

def owner_only():
    def check_owner_only(ctx):
        if ctx.author.id==config.OWNER_ID:
            return True
        else:
            create_task(ctx.send("This command can only be used by owner.", delete_after=30), loop=ctx.bot.loop)
            do_after(ctx.message.delete(), 30, loop=ctx.bot.loop)
            return False
    return commands.check(check_owner_only)

def nsfw():
    def check_nsfw(ctx):
        if ctx.channel.nsfw or ctx.channel.name.startswith("nsfw-"):
            return True
        else:
            create_task(ctx.send("This command can only be used in nsfw channels.", delete_after=30), loop=ctx.bot.loop)
            do_after(ctx.message.delete(), 30, loop=ctx.bot.loop)
            return False
    return commands.check(check_nsfw)

def otogi_guild_only():
    def check_otogi_guild_only(ctx):
        if ctx.guild.id==config.OTOGI_GUILD_ID or ctx.author.id==config.OWNER_ID:
            return True
        else:
            create_task(ctx.send("This command can only be used in Otogi: Spirit Agents server.", delete_after=30), loop=ctx.bot.loop)
            do_after(ctx.message.delete(), 30, loop=ctx.bot.loop)
            return False
    return commands.check(check_otogi_guild_only)

def manager_only():
    def check_server_manager(ctx):
        if ctx.channel.permissions_for(ctx.message.author).manage_guild:
            return True
        else:
            create_task(ctx.send("This command can only be used by server managers.", delete_after=30), loop=ctx.bot.loop)
            do_after(ctx.message.delete(), 30, loop=ctx.bot.loop)
            return False
    return commands.check(check_server_manager)

def can_kick():
    def check_can_kick(ctx):
        if ctx.channel.permissions_for(ctx.message.author).kick_members:
            return True
        else:
            create_task(ctx.send("You don't have Kick members permission.", delete_after=30), loop=ctx.bot.loop)
            do_after(ctx.message.delete(), 30, loop=ctx.bot.loop)
            return False
    return commands.check(check_can_kick)

def can_ban():
    def check_can_ban(ctx):
        if ctx.channel.permissions_for(ctx.message.author).ban_members:
            return True
        else:
            create_task(ctx.send("You don't have Ban members permission.", delete_after=30), loop=ctx.bot.loop)
            do_after(ctx.message.delete(), 30, loop=ctx.bot.loop)
            return False
    return commands.check(check_can_ban)

def creampie_guild_only():
    def check_creampie_guild_only(ctx):
        if ctx.guild.id==config.CREAMPIE_GUILD_ID:
            return True
        else:
            create_task(ctx.send("This command can only be used in ༺çɾҽąണքìҽ༻ server.", delete_after=30), loop=ctx.bot.loop)
            do_after(ctx.message.delete(), 30, loop=ctx.bot.loop)
            return False
    return commands.check(check_creampie_guild_only)

def guild_only():
    def check_guild_only(ctx):
        if ctx.guild:
            return True
        else:
            create_task(ctx.send("This command cannot be used in DM.", delete_after=30), loop=ctx.bot.loop)
            return False
    return commands.check(check_guild_only)
