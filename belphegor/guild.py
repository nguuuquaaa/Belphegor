import discord
from discord.ext import commands
from . import utils
from .utils import checks, config
import asyncio
import unicodedata
from io import BytesIO
import random

#==================================================================================================================================================

DEFAULT_WELCOME = "*\"Eeeeehhhhhh, go away {mention}, I don't want any more work...\"*"

#==================================================================================================================================================

class Guild:
    '''
    Doing stuff related to server.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.guild_data = bot.db.guild_data
        self.banned_emojis = set()

    @commands.group(name="set")
    @checks.guild_only()
    @checks.manager_only()
    async def cmd_set(self, ctx):
        '''
            `>>set`
            Base command. Does nothing by itself, but with subcommands can be used to set up several bot functions in server.
            Subcommands include:
                  `welcome` - Welcome channel
                  `welcomemessage` - Welcome message
                  `dmrule` - Message that will be DM'ed to newly joined member
                  `nsfwrole` - NSFW role, for use with `>>creampie` and `>>censored` command
                  `muterole` - Mute role, for use with `>>mute` and `>>unmute` command
                  `autorole` - Auto assign/remove role for new member
                  `prefix` - Server custom prefix
                  `log` - Log channel that records things not in Audit Logs
                  `eq` - PSO2 EQ Alert
                  `eqmini` - EQ Alert, but less spammy
        '''
        if ctx.invoked_subcommand is None:
            pass

    @commands.group(name="unset")
    @checks.guild_only()
    @checks.manager_only()
    async def cmd_unset(self, ctx):
        '''
            `>>unset`
            Base command. Does nothing by itself, but with subcommands can be used to unset bot functions in server.
            Subcommands include:
                  `welcome` - Welcome channel
                  `welcomemessage` - Welcome message
                  `dmrule` - Message that will be DM'ed to newly joined member
                  `nsfwrole` - NSFW role, for use with `>>creampie` and `>>censored` command
                  `muterole` - Mute role, for use with `>>mute` and `>>unmute` command
                  `autorole` - Auto assign/remove role for new member
                  `prefix` - Server custom prefix
                  `log` - Log channel that records things not in Audit Logs
                  `eq` - PSO2 EQ Alert (both normal and minimal)
        '''
        if ctx.invoked_subcommand is None:
            pass

    @commands.command()
    @checks.guild_only()
    @checks.can_kick()
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        '''
            `>>kick <member> <optional: reason>`
            Kick <member> and DM'ed them with <reason>.
        '''
        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.name} has been kicked.")
        except:
            await ctx.deny()
        else:
            await member.send(f"You have been kicked from {ctx.guild.name} by {ctx.author.mention}.\nReason: {reason}")

    @commands.command()
    @checks.guild_only()
    @checks.can_ban()
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        '''
            `>>Ban <member> <optional: reason>`
            Ban <member> and DM'ed them with <reason>.
        '''
        await member.ban(reason=reason)
        await ctx.send(f"{member.name} has been banned.")
        await member.send(
            f"You have been banned from {ctx.guild.name} by {ctx.author.mention}.\nReason: {reason}\n\n"
            "If you think this action is unjustified, please contact the mod in question to unlift the ban."
        )

    @commands.command()
    @checks.guild_only()
    @checks.can_ban()
    async def unban(self, ctx, user_id: int, *, reason=None):
        '''
            `>>unban <user ID> <optional: reason>`
            Unban user.
        '''
        user = await self.bot.get_user_info(user_id)
        await ctx.guild.unban(user, reason=reason)
        await ctx.send(f"{user.name} has been unbanned.")

    @commands.command()
    @checks.guild_only()
    @checks.can_ban()
    async def hackban(self, ctx, user_id: int, *, reason=None):
        '''
            `>>hackban <user ID> <optional: reason>`
            Ban user who is not currently in server.
        '''
        user = await self.bot.get_user_info(user_id)
        await ctx.guild.ban(user, reason=reason)
        await ctx.send(f"{user.name} has been hackbanned.")

    @commands.command()
    @checks.guild_only()
    @checks.manager_only()
    async def channelban(self, ctx, member: discord.Member, *, reason=None):
        '''
            `>>channelban <member> <optional: reason>`
            Ban <member> from using the current channel.
            Can specify ban time in <reason>, i.e. `for 10 minutes`.
            If no ban time is specified, 10 minutes is used.
        '''
        await ctx.channel.set_permissions(target=member, read_messages=False)
        if reason:
            try:
                reason, duration = utils.extract_time(reason)
            except:
                return await ctx.send("Time too large.")
            else:
                duration = duration.total_seconds()
        else:
            duration = 0
        if duration <= 0:
            duration = 600
        await ctx.send(f"{member.mention} has been banned from this channel for {utils.seconds_to_text(duration)}.\nReason: {reason}")
        try:
            before, after = await self.bot.wait_for(
                "guild_channel_update",
                check=lambda b, a: a.overwrites_for(member).read_messages is not False,
                timeout=duration
            )
        except:
            await ctx.channel.set_permissions(target=member, read_messages=None)
            await ctx.send(f"{member.mention} has been unbanned from this channel.")

    @commands.command(aliases=["shutup"])
    @checks.guild_only()
    @checks.manager_only()
    async def channelmute(self, ctx, member: discord.Member, *, reason=None):
        '''
            `>>channelmute <member> <optional: reason>`
            Mute <member> from posting the current channel.
            Can specify mute time in <reason>, i.e. `for 10 minutes`.
            If no mute time is specified, 10 minutes is used.
        '''
        await ctx.channel.set_permissions(target=member, send_messages=False)
        try:
            if reason:
                reason, duration = utils.extract_time(reason)
                duration = duration.total_seconds()
            else:
                duration = 0
        except:
            return await ctx.send("Time too large.")
        if duration <= 0:
            duration = 600
        await ctx.send(f"{member.mention} has been muted from this channel for {utils.seconds_to_text(duration)}.\nReason: {reason}")
        try:
            before, after = await self.bot.wait_for(
                "guild_channel_update",
                check=lambda b, a: a.overwrites_for(member).send_messages is not False,
                timeout=duration
            )
        except:
            await ctx.channel.set_permissions(target=member, send_messages=None)
            await ctx.send(f"{member.mention} has been unmuted from this channel.")

    @cmd_set.command(name="nsfwrole")
    async def cmd_set_nsfwrole(self, ctx, *, name):
        '''
            `>>set nsfwrole <role name>`
            Set role with <role name> as NSFW role.
            Name is case-insensitive.
        '''
        role = discord.utils.find(lambda r: name.lower() in r.name.lower(), ctx.guild.roles)
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"nsfw_role_id": role.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.confirm()

    @cmd_unset.command(name="nsfwrole")
    async def cmd_unset_nsfwrole(self, ctx):
        '''
            `>>unset nsfwrole`
            Unset NSFW role.
        '''
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$unset": {"nsfw_role_id": None}})
        await ctx.confirm()

    @cmd_set.command(name="muterole")
    async def cmd_set_muterole(self, ctx, *, name):
        '''
            `>>set muterole <role name>`
            Set role with <role name> as muted role.
            Name is case-insensitive.
        '''
        role = discord.utils.find(lambda r: name.lower() in r.name.lower(), ctx.guild.roles)
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"mute_role_id": role.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.confirm()

    @cmd_unset.command(name="muterole")
    async def cmd_unset_muterole(self, ctx, *, name):
        '''
            `>>unset muterole`
            Unset muted role.
        '''
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$unset": {"mute_role_id": None}})
        await ctx.confirm()

    @commands.command()
    @checks.guild_only()
    async def creampie(self, ctx):
        '''
            `>>creampie`
            Get NSFW role, if applicable.
        '''
        role_data = await self.guild_data.find_one({"guild_id": ctx.guild.id, "nsfw_role_id": {"$ne": None}}, projection={"_id": -1, "nsfw_role_id": 1})
        if role_data:
            role = discord.utils.find(lambda r: r.id==role_data["nsfw_role_id"], ctx.guild.roles)
            if role:
                await ctx.author.add_roles(role)
                return await ctx.confirm()
        else:
            await ctx.send("NSFW role is not set up in this server.")

    @commands.command()
    @checks.guild_only()
    async def censored(self, ctx):
        '''
            `>>censored`
            Remove NSFW role, if applicable.
        '''
        role_data = await self.guild_data.find_one({"guild_id": ctx.guild.id, "nsfw_role_id": {"$ne": None}}, projection={"_id": -1, "nsfw_role_id": 1})
        if role_data:
            role = discord.utils.find(lambda r: r.id==role_data["nsfw_role_id"], ctx.guild.roles)
            if role in ctx.author.roles:
                await ctx.author.remove_roles(role)
                return await ctx.confirm()
        else:
            await ctx.send("NSFW role is not set up in this server.")

    @cmd_set.command(name="welcome", aliases=["welcomechannel"])
    async def set_welcome(self, ctx, channel: discord.TextChannel=None):
        '''
            `>>set welcome <optional: channel>`
            Set <channel> as welcome channel. If no channel is provided, use the current channel that the command is invoked in.
            A message will be sent to that channel every time a new member joined.
        '''
        target = channel or ctx.channel
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"welcome_channel_id": target.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.confirm()

    @cmd_unset.command(name="welcome", aliases=["welcomechannel"])
    async def unset_welcome(self, ctx):
        '''
            `>>unset welcome`
            Unset welcome channel.
        '''
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$unset": {"welcome_channel_id": None}})
        await ctx.confirm()

    @cmd_set.command(name="welcomemessage")
    async def set_welcome_message(self, ctx, *, text):
        '''
            `>>set welcomemessage <message>`
            Set custom welcome message.
            Use `{name}` for member name, `{mention}` for member mention, `{server}` for server name.
        '''
        try:
            content = f"Welcome message will be displayed as:\n{text}".format(name=ctx.author.display_name, mention=ctx.author.mention, server=ctx.guild.name)
        except:
            await ctx.send("Format error. You sure read the instruction?")
        else:
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"welcome_message": text}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
            await ctx.send(content)

    @cmd_unset.command(name="welcomemessage")
    async def unset_welcome_message(self, ctx):
        '''
            `>>unset welcomemessage`
            Unset custom welcome message and use the default one instead.
        '''
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$unset": {"welcome_message": None}})
        await ctx.send(f"Welcome message will be displayed as:\n{DEFAULT_WELCOME}".format(name=ctx.author.display_name, mention=ctx.author.mention, server=ctx.guild.name))

    @cmd_set.command(name="dmrule", aliases=["rule"])
    async def set_dm_rule(self, ctx, *, text):
        '''
            `>>set dmrule <message>`
            Set message that will be DM'ed to new member.
            Use `{server}` for server name.
        '''
        try:
            content = f"Newcomer will be messaged:\n{text}".format(server=ctx.guild.name)
        except:
            await ctx.send("Format error. You sure read the instruction?")
        else:
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"welcome_rule": text}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
            await ctx.send(content)

    @cmd_unset.command(name="dmrule", aliases=["rule"])
    async def unset_dm_rule(self, ctx):
        '''
            `>>unset dmrule`
            Unset DM rule message.
        '''
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$unset": {"welcome_rule": None}})
        await ctx.confirm()

    @cmd_set.command(name="autorole")
    async def set_autorole(self, ctx):
        '''
            `>>set autorole`
            Set auto assign/remove role for new member. Advance step-by-step.
        '''
        msg = await ctx.send("Input the role name:")
        try:
            message = await self.bot.wait_for("message", check=lambda m: m.author.id==ctx.author.id and m.channel.id==ctx.channel.id, timeout=600)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long, so I'll just sleep then.")
        role = discord.utils.find(lambda r: r.name.lower()==message.content.lower(), ctx.guild.roles)
        if not role:
            return await ctx.send("Role not found. You sure type in correctly?")
        msg = await ctx.send(
            "What autorole type do you want?\n"
            "`1:` Newcomer will get a role upon registration.\n"
            "`2:` Newcomer will get a role on join, and it will be removed upon registration."
        )
        artype = await ctx.wait_for_choice(max=2)
        if artype is None:
            return await ctx.send("Okay, no autorole, right.")
        msg = await ctx.send("Input the registration phrase:")
        try:
            message = await self.bot.wait_for("message", check=lambda m: m.author.id==ctx.author.id and m.channel.id==ctx.channel.id, timeout=600)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long, so I'll just sleep then.")
        phrase = message.content
        msg = await ctx.send("Do you want to set a custom response? Type `no` to skip.")
        try:
            message = await self.bot.wait_for("message", check=lambda m: m.author.id==ctx.author.id and m.channel.id==ctx.channel.id, timeout=600)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long, so I'll just sleep then.")
        if message.content.lower() == "no":
            response = None
        else:
            response = message.content
        await self.guild_data.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {"autorole_id": role.id, "autorole_type": artype, "autorole_phrase": phrase, "autorole_response": response}, "$setOnInsert": {"guild_id": ctx.guild.id}},
            upsert=True
        )
        await ctx.send("\U0001f44c Autorole is ready to go.")

    @cmd_unset.command(name="autorole")
    async def unset_autorole(self, ctx):
        '''
            `>>unset autorole`
            Unset auto assign/remove role for new member.
        '''
        await self.guild_data.update_one(
            {"guild_id": ctx.guild.id},
            {"$unset": {"autorole_id": None, "autorole_type": None, "autorole_phrase": None, "autorole_response": None}}
        )
        await ctx.confirm()

    @cmd_set.command(name="log", aliases=["logchannel"])
    async def logchannel(self, ctx, channel: discord.TextChannel=None):
        '''
            `>>set log <optional: channel>`
            Set <channel> as log channel. If no channel is provided, use the current channel that the command is invoked in.
            Log channel records member events that Audit Logs doesn't record, such as member nick/roles change, member join/leave, and message edit/delete.
            Bot activity is excluded.
        '''
        target = channel or ctx.channel
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"log_channel_id": target.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.confirm()

    @cmd_unset.command(name="log", aliases=["logchannel"])
    async def nolog(self, ctx):
        '''
            `>>unset log`
            Unset log channel.
        '''
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$unset": {"log_channel_id": ""}})
        await ctx.confirm()

    @cmd_set.command(name="prefix")
    async def cmd_prefix(self, ctx, prefix):
        '''
            `>>set prefix <prefix>`
            Add custom prefix.
            If <prefix> contains whitespace then it must be enclosed in double-quote marks.
            If a custom prefix is set then the default `>>` prefix is not available anymore. You can explicitly set it up if you want it alongside new prefixes.
            Bot mention is always a prefix, regardless of custom prefixes.
            Limit 10 custom prefixes per server.
        '''
        current = self.bot.guild_prefixes.get(ctx.guild.id, [])
        if prefix in current:
            if len(current) >= 10:
                return await ctx.send("Too many prefixes.")
            current.append(prefix)
            self.bot.guild_prefixes[ctx.guild.id] = current
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$addToSet": {"prefixes": prefix}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.confirm()

    @cmd_unset.command(name="prefix")
    async def cmd_noprefix(self, ctx, prefix):
        '''
            `>>unset prefix <prefix>`
            Remove custom prefix.
            If <prefix> contains whitespace then it must be enclosed in double-quote marks.
            You can't unset bot mention prefix.
        '''
        current = self.bot.guild_prefixes.get(ctx.guild.id, [])
        try:
            current.remove(prefix)
        except:
            pass
        else:
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$pull": {"prefixes": prefix}})
        finally:
            await ctx.confirm()

    @cmd_set.command(name="eq", aliases=["eqalert"])
    async def set_eq_channel(self, ctx, channel: discord.TextChannel=None):
        '''
            `>>set eq <optional: channel>`
            Set <channel> as PSO2 EQ Alert channel. If no channel is provided, use the current channel that the command is invoked in.
            EQs will be noticed 2h45m, 1h45m, 45m, 15m prior, and currently happening.
        '''
        target = channel or ctx.channel
        await self.guild_data.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {"eq_channel_id": target.id, "eq_alert_minimal": False}, "$setOnInsert": {"guild_id": ctx.guild.id}},
            upsert=True
        )
        await ctx.confirm()

    @cmd_set.command(name="eqmini", aliases=["minimaleq"])
    async def set_minimal_eq_channel(self, ctx, channel: discord.TextChannel=None):
        '''
            `>>set eq <optional: channel>`
            Set <channel> as PSO2 EQ Alert channel, in minimal mode. If no channel is provided, use the current channel that the command is invoked in.
            EQ will only be noticed 1h45m and 45m prior in minimal mode.
        '''
        target = channel or ctx.channel
        await self.guild_data.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {"eq_channel_id": target.id, "eq_alert_minimal": True}, "$setOnInsert": {"guild_id": ctx.guild.id}},
            upsert=True
        )
        await ctx.confirm()

    @cmd_unset.command(name="eq", aliases=["eqalert"])
    async def unset_eq_channel(self, ctx):
        '''
            `>>unset eq`
            Unset PSO2 EQ Alert.
        '''
        result = await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$unset": {"eq_channel_id": "", "eq_alert_minimal": ""}})
        if result.modified_count > 0:
            await ctx.confirm()
        else:
            await ctx.deny()

    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            return
        guild_data = await self.guild_data.find_one(
            {"guild_id": message.guild.id, "autorole_phrase": message.content},
            projection={"_id": False, "autorole_id": True, "autorole_type": True, "autorole_phrase": True, "autorole_response": True}
        )
        if guild_data:
            role = discord.utils.find(lambda r: r.id==guild_data["autorole_id"], message.guild.roles)
            if not role:
                return
            artype = guild_data["autorole_type"]
            if artype == 0:
                await message.author.add_roles(role)
            elif artype == 1:
                await message.author.remove_roles(role)
            response = guild_data["autorole_response"]
            if response:
                await message.channel.send(response, delete_after=30)
            await utils.do_after(message.delete(), 30)

    async def on_member_join(self, member):
        if member.bot:
            return
        guild = member.guild
        guild_data = await self.guild_data.find_one(
            {"guild_id": guild.id},
            projection={"_id": False, "log_channel_id": True, "welcome_channel_id": True, "welcome_message": True, "welcome_rule": True, "autorole_type": True, "autorole_id": True}
        )
        if guild_data:
            log_channel = guild.get_channel(guild_data.get("log_channel_id"))
            if log_channel:
                embed = discord.Embed(colour=discord.Colour.dark_orange())
                embed.add_field(name="Event", value="member_join", inline=False)
                embed.add_field(name="ID", value=member.id)
                embed.add_field(name="Name", value=str(member))
                embed.set_footer(text=utils.format_time(utils.now_time()))
                await log_channel.send(embed=embed)
            welcome_channel = guild.get_channel(guild_data.get("welcome_channel_id"))
            if welcome_channel:
                welcome_message = guild_data.get("welcome_message", DEFAULT_WELCOME)
                await welcome_channel.send(welcome_message.format(name=member.display_name, mention=member.mention, server=member.guild.name, guild=member.guild.name))
            welcome_rule = guild_data.get("welcome_rule")
            if welcome_rule:
                await utils.do_after(member.send(welcome_rule.format(server=member.guild.name)), 5)
            autorole_type = guild_data.get("autorole_type", None)
            if autorole_type == 1:
                role = discord.utils.find(lambda r: r.id==guild_data["autorole_id"], guild.roles)
                await member.add_roles(role)

    async def on_member_remove(self, member):
        if member.bot:
            return
        guild = member.guild
        guild_data = await self.guild_data.find_one(
            {"guild_id": guild.id},
            projection={"_id": False, "log_channel_id": True}
        )
        if guild_data:
            log_channel = guild.get_channel(guild_data.get("log_channel_id"))
            if log_channel:
                embed = discord.Embed(colour=discord.Colour.dark_orange())
                embed.add_field(name="Event", value="member_leave", inline=False)
                embed.add_field(name="ID", value=member.id)
                embed.add_field(name="Name", value=str(member))
                embed.set_footer(text=utils.format_time(utils.now_time()))
                await log_channel.send(embed=embed)

    async def on_member_update(self, before, after):
        if before.bot:
            return
        guild = before.guild
        guild_data = await self.guild_data.find_one(
            {"guild_id": guild.id},
            projection={"_id": False, "log_channel_id": True}
        )
        if guild_data:
            log_channel = guild.get_channel(guild_data.get("log_channel_id"))
            if log_channel:
                old_roles = set(before.roles)
                new_roles = set(after.roles)
                nick_change = before.nick != after.nick
                role_change = old_roles != new_roles
                if nick_change or role_change:
                    embed = discord.Embed(colour=discord.Colour.dark_orange())
                    embed.add_field(name="Event", value="member_update", inline=False)
                    embed.add_field(name="ID", value=before.id)
                    embed.add_field(name="Name", value=str(before))
                    if nick_change:
                        embed.add_field(name="Old nickname", value=before.nick, inline=False)
                        embed.add_field(name="New nickname", value=after.nick, inline=False)
                    if role_change:
                        add_roles = new_roles - old_roles
                        remove_roles = old_roles - new_roles
                        if add_roles:
                            embed.add_field(name="Roles add", value=", ".join([r.name for r in add_roles]), inline=False)
                        if remove_roles:
                            embed.add_field(name="Roles remove", value=", ".join([r.name for r in remove_roles]), inline=False)
                    embed.set_footer(text=utils.format_time(utils.now_time()))
                    await log_channel.send(embed=embed)

    async def on_message_delete(self, message):
        if message.author.bot:
            return
        guild = message.guild
        if not guild:
            return
        guild_data = await self.guild_data.find_one({"guild_id": guild.id})
        if guild_data:
            log_channel = guild.get_channel(guild_data.get("log_channel_id"))
            if log_channel:
                embed = discord.Embed(colour=discord.Colour.dark_orange())
                embed.add_field(name="Event", value="message_delete", inline=False)
                embed.add_field(name="ID", value=message.id)
                embed.add_field(name="Author", value=str(message.author))
                embed.add_field(name="Channel", value=message.channel.mention)
                if message.content:
                    embed.add_field(name="Content", value=f"{message.content[:1000]}" if len(message.content)>1000 else message.content, inline=False)
                if message.attachments:
                    embed.add_field(name="Attachments", value="\n".join([a.url for a in message.attachments]))
                embed.set_footer(text=utils.format_time(utils.now_time()))
                await log_channel.send(embed=embed)

    async def on_message_edit(self, before, after):
        if before.author.bot:
            return
        guild = before.guild
        if not guild:
            return
        guild_data = await self.guild_data.find_one(
            {"guild_id": guild.id},
            projection={"_id": False, "log_channel_id": True}
        )
        if guild_data:
            log_channel = guild.get_channel(guild_data.get("log_channel_id"))
            if log_channel:
                if before.content != after.content:
                    embed = discord.Embed(colour=discord.Colour.dark_orange())
                    embed.add_field(name="Event", value="message_edit", inline=False)
                    embed.add_field(name="ID", value=before.id)
                    embed.add_field(name="Author", value=str(before.author))
                    embed.add_field(name="Channel", value=before.channel.mention)
                    embed.add_field(name="Before", value=f"{before.content[:1000]}..." if len(before.content)>1000 else before.content, inline=False)
                    embed.add_field(name="After", value=f"{after.content[:1000]}..." if len(after.content)>1000 else after.content, inline=False)
                    embed.set_footer(text=utils.format_time(utils.now_time()))
                    await log_channel.send(embed=embed)

    async def get_selfroles(self, guild):
        role_data = await self.guild_data.find_one({"guild_id": guild.id}, projection={"_id": -1, "selfrole_ids": 1})
        if role_data:
            roles = (discord.utils.find(lambda r: r.id==role_id, guild.roles) for role_id in role_data.get("selfrole_ids", []))
            return [r for r in roles if r is not None]
        else:
            return []

    @commands.group(invoke_without_command=True)
    @checks.guild_only()
    async def selfrole(self, ctx, *, name):
        '''
            `>>selfrole <name>`
            Get a selfrole from selfrole pool, or remove if you already had it.
            Role name is case-insensitive.
        '''
        if ctx.invoked_subcommand is None:
            role = discord.utils.find(lambda r:r.name.lower()==name.lower(), ctx.guild.roles)
            roles = await self.get_selfroles(ctx.guild)
            if role in roles:
                if role in ctx.author.roles:
                    await ctx.author.remove_roles(role)
                    await ctx.send(f"Role {role.name} removed.")
                else:
                    await ctx.author.add_roles(role)
                    await ctx.confirm()
            else:
                await ctx.deny()

    @selfrole.error
    async def selfrole_error(self, ctx, error):
        if isinstance(error, discord.Forbidden):
            await ctx.send("I don't have permissions to do this.")

    @selfrole.command()
    @checks.guild_only()
    @checks.manager_only()
    async def add(self, ctx, *, name):
        '''
            `>>selfrole add <name>`
            Add a role to selfrole pool.
            Role name is case-insensitive.
        '''
        role = discord.utils.find(lambda r:r.name.lower()==name.lower(), ctx.guild.roles)
        if role:
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$addToSet": {"selfrole_ids": role.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
            await ctx.confirm()
        else:
            await ctx.deny()

    @selfrole.command()
    @checks.guild_only()
    @checks.manager_only()
    async def remove(self, ctx, *, name):
        '''
            `>>selfrole remove <name>`
            Remove a selfrole from pool.
            Role name is case-insensitive.
        '''
        role = discord.utils.find(lambda r:r.name.lower()==name.lower(), ctx.guild.roles)
        if role:
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$pull": {"selfrole_ids": role.id}})
            await ctx.confirm()
        else:
            await ctx.deny()

    @selfrole.command()
    @checks.guild_only()
    async def empty(self, ctx):
        '''
            `>>selfrole empty`
            Remove all selfroles from self.
        '''
        roles = await self.get_selfroles(ctx.guild)
        for role in roles:
            if role in ctx.author.roles:
                await ctx.author.remove_roles(role)
        await ctx.confirm()

    @selfrole.command(name="list", aliases=["pool"])
    @checks.guild_only()
    async def role_list(self, ctx):
        '''
            `>>selfrole list`
            Display server selfrole pool.
        '''
        roles = await self.get_selfroles(ctx.guild)
        if roles:
            embeds = utils.embed_page_format(
                roles, 10,
                title=f"{ctx.guild.name}'s selfrole pool:",
                description=lambda i, x: f"`{i+1}.` {x.name}"
            )
            await ctx.embed_page(embeds)
        else:
            await ctx.send("Server has no selfrole.")

    @selfrole.command()
    @checks.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def distribution(self, ctx):
        '''
            `>>selfrole distribution`
            Draw a piechart showing server selfrole distribution.
        '''
        async with ctx.typing():
            roles = await self.get_selfroles(ctx.guild)
            if not roles:
                return await ctx.send("Server has no selfrole.")
            colors = {(0, 0, 0)}
            check_roles = []
            for role in roles:
                rgb = role.colour.to_rgb()
                while rgb in colors:
                    rgb = (random.randrange(256), random.randrange(256), random.randrange(256))
                colors.add(rgb)
                check_roles.append({"name": role.name, "count": len(role.members), "color": rgb})
            bytes_ = await utils.pie_chart(check_roles)
            if bytes_:
                await ctx.send(file=discord.File(bytes_, filename="distribution.png"))
            else:
                await ctx.send("There's no one with selfrole.")

    @commands.command()
    @checks.guild_only()
    @checks.manager_only()
    async def mute(self, ctx, member: discord.Member, *, reason=""):
        '''
            `>>mute <member> <reason>`
            Give member muted role.
            Can specify mute time in reason, i.e. `for 1 hour`.
            If no mute time is specified, mute indefinitely.
        '''
        role_data = await self.guild_data.find_one({"guild_id": guild.id, "mute_role_id": {"$ne": None}}, projection={"_id": -1, "mute_role_id": 1})
        if role_data:
            muted_role = discord.utils.find(lambda r: r.id==role_data["mute_role_id"], ctx.guild.roles)
            await member.add_roles(muted_role)
            try:
                reason, duration = utils.extract_time(reason)
                duration = duration.total_seconds()
            except:
                return await ctx.send("Time too large.")
            if duration > 0:
                await ctx.send(f"{member.mention} has been muted for {utils.seconds_to_text(duration)}.\nReason: {reason}")
                try:
                    before, after = await self.bot.wait_for(
                        "member_update",
                        check=lambda b,a: a.id==member.id and a.guild.id==member.guild.id and "Muted" not in [r.name for r in a.roles],
                        timeout=duration
                    )
                except asyncio.TimeoutError:
                    await member.remove_roles(muted_role)
                    await ctx.send(f"{member.mention} has been unmuted.")
            else:
                await ctx.send(f"{member.mention} has been muted.")
        else:
            await ctx.send("Muted role is not set up in this server.")

    @commands.command()
    @checks.guild_only()
    @checks.manager_only()
    async def unmute(self, ctx, member: discord.Member):
        '''
            `>>unmute <member>`
            Remove muted role from member.
        '''
        role_data = await self.guild_data.find_one({"guild_id": guild.id, "mute_role_id": {"$ne": None}}, projection={"_id": -1, "mute_role_id": 1})
        if role_data:
            muted_role = discord.utils.find(lambda r: r.id==role_data["mute_role_id"], ctx.guild.roles)
            await member.remove_roles(muted_role)
            await ctx.send(f"{member.mention} has been unmute.")
        else:
            await ctx.send("Muted role is not set up in this server.")

    @commands.command()
    @checks.guild_only()
    @checks.manager_only()
    async def purge(self, ctx, number: int=10, *members: discord.Member):
        '''
            `>>purge <optional: number> <optional: list of members>`
            Purge messages in the current channel.
            The default number of messages is 10.
            If members is provided, purge only messages of those members, otherwise purge everything.
        '''
        if number > 0:
            if members:
                await ctx.channel.purge(limit=number, check=lambda m: m.author in members)
            else:
                await ctx.channel.purge(limit=number)

    @commands.command()
    @checks.guild_only()
    @checks.manager_only()
    async def purgereact(self, ctx, *msg_ids: int):
        '''
            `>>purgereact <list of message ids>`
            Remove all reactions from the provided messages.
        '''
        for msg_id in msg_ids:
            msg = await ctx.get_message(msg_id)
            await msg.clear_reactions()
        await ctx.confirm()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def deletemessage(self, ctx, msg_id: int):
        try:
            message = await ctx.get_message(msg_id)
            await message.delete()
            await ctx.confirm()
        except:
            await ctx.deny()

    @commands.command()
    @checks.guild_only()
    @checks.otogi_guild_only()
    @checks.manager_only()
    async def reactban(self, ctx, *emojis):
        '''
            `>>reactban <list of emojis>`
            Prevent reaction with certain emojis by removing them upon adding.
        '''
        for emoji in emojis:
            em = discord.utils.find(lambda e:emoji==str(e), self.bot.emojis)
            if em:
                self.banned_emojis.add(em.id)
            else:
                try:
                    em = int(em)
                except:
                    pass
                self.banned_emojis.add(emoji)
        await ctx.confirm()

    @commands.command(hidden=True)
    async def getreact(self, ctx, msg_id: int):
        msg = await ctx.get_message(msg_id)
        e_list = []
        for r in msg.reactions:
            try:
                e_list.append(f"`@<{r.emoji.id}>` - {r.emoji.name}")
            except:
                e_list.append("\n".join([f"`\\U{ord(c):08x}` - {unicodedata.name(c)}" for c in r.emoji]))
        await ctx.send("\n".join(e_list))

    async def on_reaction_add(self, reaction, user):
        guild = getattr(user, "guild", None)
        if guild:
            if guild.id == config.OTOGI_GUILD_ID:
                try:
                    e = reaction.emoji.id
                except AttributeError:
                    e = reaction.emoji
                if e in self.banned_emojis:
                    await reaction.message.remove_reaction(reaction, user)

    @commands.group(name="guild", aliases=["server"])
    async def cmd_guild(self, ctx):

        if ctx.invoked_subcommand is None:
            pass

    @cmd_guild.command(name="prefix")
    async def guild_prefix(self, ctx):
        '''
            `>>server prefix`
            Display all server prefixes.
        '''
        prefixes = list(await self.bot.get_prefix(ctx.message))
        prefixes.sort()
        desc = "\n".join((f"{i+1}. {p}" for i, p in enumerate(prefixes)))
        await ctx.send(embed=discord.Embed(title=f"Prefixes for {ctx.guild.name}", description=f"```fix\n{desc}\n```"))

    @cmd_guild.command(name="icon")
    async def guild_icon(self, ctx):
        '''
            `>>server icon`
            Display server icon.
        '''
        embed = discord.Embed(title=f"{ctx.guild.name}'s icon")
        embed.set_image(url=ctx.guild.icon_url_as(format='png'))
        await ctx.send(embed=embed)

    async def get_command_name(self, ctx, cmd_name):
        cmd = self.bot.get_command(cmd_name)
        if not cmd:
            await ctx.send(f"{cmd_name} is not a valid command.")
            return None
        elif cmd.hidden or cmd.qualified_name.partition(" ")[0] in ("enable", "disable"):
            await ctx.send("This command cannot be disabled or enabled.")
            return None
        else:
            return cmd.qualified_name

    @commands.group(name="disable")
    @checks.guild_only()
    @checks.manager_only()
    async def cmd_disable(self, ctx):
        '''
            `>>disable`
            Base command. Does nothing by itself, but with subcommands can be used to disable certain bot features in server.
            Subcommands include:
                  `server` - Disable all bot commands in server
                  `channel` - Disable all bot commands in a channel
                  `member` - Prevent member from using bot commands
                  `command` - Disable a certain command
        '''
        pass

    @commands.group(name="enable")
    @checks.guild_only()
    @checks.manager_only()
    async def cmd_enable(self, ctx):
        '''
            `>>enable`
            Base command. Does nothing by itself, but with subcommands can be used to enable certain bot features in server.
            Subcommands include:
                  `server` - Enable all bot commands in server
                  `channel` - Enable all bot commands in a channel
                  `member` - Enable bot commands for member
                  `command` - Enable a certain command
        '''
        pass

    #enable and disable bot usage for guild
    @cmd_disable.command(name="guild", aliases=["server"])
    async def cmd_disable_guild(self, ctx):
        '''
            `>>disable server`
            Disable all commands in current server, except enable/disable command.
            This does not affect automatic tasks like welcome or log, and non-command like ping or registration.
        '''
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        guild_data["disabled_bot_guild"] = True
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"disabled_bot_guild": True}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.send(f"Bot usage has been disabled in this server.")

    @cmd_enable.command(name="guild", aliases=["server"])
    async def cmd_enable_guild(self, ctx):
        '''
            `>>enable server`
            Enable all commands in current server.
            This does not affect other specific disabled command(s).
        '''
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        guild_data["disabled_bot_guild"] = False
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"disabled_bot_guild": False}})
        await ctx.send(f"Bot usage has been enabled in this server.")

    #enable and disable bot usage for channel
    @cmd_disable.command(name="channel")
    async def cmd_disable_channel(self, ctx, channel: discord.TextChannel):
        '''
            `>>disable channel <channel>`
            Disable all commands in <channel>, except enable/disable command.
            This does not affect automatic tasks like welcome or log, and non-command like ping or registration.
        '''
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        disabled_channel = guild_data.get("disabled_bot_channel", set())
        disabled_channel.add(channel.id)
        guild_data["disabled_bot_channel"] = disabled_channel
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$addToSet": {"disabled_bot_channel": channel.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.send(f"Bot usage has been disabled in {channel.mention}.")

    @cmd_enable.command(name="channel")
    async def cmd_enable_channel(self, ctx, channel: discord.TextChannel):
        '''
            `>>enable channel <channel>`
            Enable all commands in <channel>.
            This does not affect other specific disabled command(s).
        '''
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        disabled_channel = guild_data.get("disabled_bot_channel", set())
        disabled_channel.discard(channel.id)
        guild_data["disabled_bot_channel"] = disabled_channel
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$pull": {"disabled_bot_channel": channel.id}})
        await ctx.send(f"Bot usage has been enabled in {channel.mention}.")

    #enable and disable bot usage for member
    @cmd_disable.command(name="member")
    async def cmd_disable_member(self, ctx, member: discord.Member):
        '''
            `>>disable member <member>`
            Disable all commands for <member>, except enable/disable command.
            This does not affect non-command like ping or registration.
        '''
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        disabled_member = guild_data.get("disabled_bot_member", set())
        disabled_member.add(member.id)
        guild_data["disabled_bot_member"] = disabled_member
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$addToSet": {"disabled_bot_member": channel.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.send(f"Bot usage has been disabled for {member} in this server.")

    @cmd_enable.command(name="member")
    async def cmd_enable_member(self, ctx, member: discord.Member):
        '''
            `>>enable member <member>`
            Enable all commands for <member>.
            This does not affect other specific disabled command(s).
        '''
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        disabled_member = guild_data.get("disabled_bot_member", set())
        disabled_member.discard(member.id)
        guild_data["disabled_bot_member"] = disabled_member
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$pull": {"disabled_bot_member": channel.id}})
        await ctx.send(f"Bot usage has been enabled for {member} in this server.")

    @cmd_disable.group(name="command", aliases=["cmd"])
    async def cmd_disable_command(self, ctx):
        '''
            `>>disable command`
            Base command. Does nothing by itself, but with subcommands can be used to disable specific command(s) in server.
        '''
        pass

    @cmd_enable.group(name="command", aliases=["cmd"])
    async def cmd_enable_command(self, ctx):
        '''
            `>>enable command`
            Base command. Does nothing by itself, but with subcommands can be used to enable specific command(s) in server.
        '''
        pass

    #enable and disable command usage for guild
    @cmd_disable_command.command(name="guild", aliases=["server"])
    async def cmd_disable_command_guild(self, ctx, *, cmd_name):
        '''
            `>>disable command server <command>`
            Disable <command> in server, except enable/disable command.
        '''
        cmd = await self.get_command_name(ctx, cmd_name)
        if not cmd:
            return
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        disabled_guild = guild_data.get("disabled_command_guild", set())
        disabled_guild.add(cmd)
        guild_data["disabled_command_guild"] = disabled_guild
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$addToSet": {"disabled_command_guild": cmd}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.send(f"Command `{cmd}` has been disabled in this server.")

    @cmd_enable_command.command(name="guild", aliases=["server"])
    async def cmd_enable_command_guild(self, ctx, *, cmd_name):
        '''
            `>>enable command server <command>`
            Enable <command> in server, except enable/disable command.
            This does not affect other specific disabled command(s).
        '''
        cmd = await self.get_command_name(ctx, cmd_name)
        if not cmd:
            return
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        disabled_guild = guild_data.get("disabled_command_guild", set())
        disabled_guild.discard(cmd)
        guild_data["disabled_command_guild"] = disabled_guild
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$pull": {"disabled_command_guild": cmd}})
        await ctx.send(f"Command `{cmd}` has been enabled in this server.")

    #enable and disable command usage for channel
    @cmd_disable_command.command(name="channel")
    async def cmd_disable_command_channel(self, ctx, channel: discord.TextChannel, *, cmd_name):
        '''
            `>>disable command channel <channel> <command>`
            Disable <command> in <channel>, except enable/disable command.
        '''
        cmd = await self.get_command_name(ctx, cmd_name)
        if not cmd:
            return
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        disabled_channel = guild_data.get("disabled_command_channel", set())
        disabled_channel.add((cmd, channel.id))
        guild_data["disabled_command_channel"] = disabled_channel
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one(
            {"guild_id": ctx.guild.id},
            {"$addToSet": {"disabled_command_channel": (cmd, channel.id)}, "$setOnInsert": {"guild_id": ctx.guild.id}},
            upsert=True
        )
        await ctx.send(f"Command `{cmd}` has been disabled in {channel.mention}.")

    @cmd_enable_command.command(name="channel")
    async def cmd_enable_command_channel(self, ctx, channel: discord.TextChannel, *, cmd_name):
        '''
            `>>enable command channel <channel> <command>`
            Enable <command> in <channel>, except enable/disable command.
            This does not affect other specific disabled command(s).
        '''
        cmd = await self.get_command_name(ctx, cmd_name)
        if not cmd:
            return
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        disabled_channel = guild_data.get("disabled_command_channel", set())
        disabled_channel.discard((cmd, channel.id))
        guild_data["disabled_command_channel"] = disabled_channel
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$pull": {"disabled_command_channel": (cmd, channel.id)}})
        await ctx.send(f"Command `{cmd}` has been enabled in {channel.mention}.")

    #enable and disable command usage for member
    @cmd_disable_command.command(name="member")
    async def cmd_disable_command_member(self, ctx, member: discord.Member, *, cmd_name):
        '''
            `>>disable command member <member> <command>`
            Disable <command> for <member>, except enable/disable command.
        '''
        cmd = await self.get_command_name(ctx, cmd_name)
        if not cmd:
            return
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        disabled_member = guild_data.get("disabled_command_member", set())
        disabled_member.add((cmd, member.id))
        guild_data["disabled_command_member"] = disabled_member
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one(
            {"guild_id": ctx.guild.id},
            {"$addToSet": {"disabled_command_member": (cmd, member.id)}, "$setOnInsert": {"guild_id": ctx.guild.id}},
            upsert=True
        )
        await ctx.send(f"Command `{cmd}` has been disabled for {member}'s use.")

    @cmd_enable_command.command(name="member")
    async def cmd_enable_command_member(self, ctx, member: discord.Member, *, cmd_name):
        '''
            `>>enable command member <member> <command>`
            Enable <command> for <member>, except enable/disable command.
            This does not affect other specific disabled command(s).
        '''
        cmd = await self.get_command_name(ctx, cmd_name)
        if not cmd:
            return
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        disabled_member = guild_data.get("disabled_command_member", set())
        disabled_member.discard((cmd, member.id))
        guild_data["disabled_command_member"] = disabled_member
        self.bot.disabled_data[ctx.guild.id] = guild_data
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$pull": {"disabled_command_member": (cmd, member.id)}})
        await ctx.send(f"Command `{cmd}` has been enabled for {member}'s use.")

    @cmd_guild.command()
    async def info(self, ctx):
        '''
            `>>disable info`

        '''
        empty_set = frozenset()
        guild_data = self.bot.disabled_data.get(ctx.guild.id, {})
        disabled_guild = guild_data.get("disabled_guild", False)
        disabled_channel = guild_data.get("disabled_channel", empty_set)
        disabled_member = guild_data.get("disabled_member", empty_set)
        disabled_command_guild = guild_data.get("disabled_command_guild", empty_set)
        disabled_command_channel = guild_data.get("disabled_command_channel", empty_set)
        disabled_command_member = guild_data.get("disabled_command_member", empty_set)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Guild(bot))
