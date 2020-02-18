import discord
from discord.ext import commands
from . import utils
from .utils import checks, config, modding
import asyncio
import unicodedata
from io import BytesIO
import random
from PIL import Image
import textwrap
import traceback

#==================================================================================================================================================

DEFAULT_WELCOME = "Eeeeehhhhhh, go away {mention}, I don't want any more work..."

#==================================================================================================================================================

class Guild(commands.Cog):
    '''
    Doing stuff related to server.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.guild_data = bot.db.guild_data
        self.banned_emojis = set()
        self.autorole_registration = {}

    @modding.help(brief="Set up bot settings", category="Guild", field="Server management", paragraph=0)
    @commands.group(name="set")
    @checks.guild_only()
    @checks.manager_only()
    async def cmd_set(self, ctx):
        '''
            `>>set`
            Base command. Does nothing by itself, but with subcommands can be used to set up several bot functions in server.
            Subcommands include:
            -`welcome` - Welcome channel
            -`welcomemessage` - Welcome message
            -`dmrule` - Message that will be DM'ed to newly joined member
            -`nsfwrole` - NSFW role, for use with `>>creampie` and `>>censored` command
            -`muterole` - Mute role, for use with `>>mute` and `>>unmute` command
            -`autorole` - Auto assign/remove role for new member
            -`prefix` - Server custom prefix
            -`log` - Activity log channel
            -`logmessage` - Message log
            -`eq` - PSO2 EQ Alert
        '''
        pass

    @modding.help(brief="Unset bot settings", category="Guild", field="Server management", paragraph=0)
    @commands.group(name="unset")
    @checks.guild_only()
    @checks.manager_only()
    async def cmd_unset(self, ctx):
        '''
            `>>unset`
            Base command. Does nothing by itself, but with subcommands can be used to unset bot functions in server.
            Subcommands include:
            -`welcome` - Welcome channel
            -`welcomemessage` - Welcome message
            -`dmrule` - Message that will be DM'ed to newly joined member
            -`nsfwrole` - NSFW role, for use with `>>creampie` command
            -`muterole` - Mute role, for use with `>>mute` and `>>unmute` command
            -`autorole` - Auto assign/remove role for new member
            -`prefix` - Server custom prefix
            -`allprefix` - All server custom prefixes
            -`log` - Activity log channel
            -`logmessage` - Message log
            -`eq` - PSO2 EQ Alert (both normal and minimal)
        '''
        pass

    @modding.help(brief="Kick member", category="Guild", field="Server management", paragraph=2)
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
        except discord.Forbidden:
            await ctx.deny()
        else:
            await ctx.send(f"{member.name} has been kicked.")
            await member.send(f"You have been kicked from {ctx.guild.name} by {ctx.author.mention}.\nReason: {reason}")

    @modding.help(brief="Ban member", category="Guild", field="Server management", paragraph=2)
    @commands.command()
    @checks.guild_only()
    @checks.can_ban()
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        '''
            `>>Ban <member> <optional: reason>`
            Ban <member> and DM'ed them with <reason>.
        '''
        try:
            await member.ban(reason=reason)
        except discord.Forbidden:
            await ctx.deny()
        else:
            await ctx.send(f"{member.name} has been banned.")
            await member.send(f"You have been banned from {ctx.guild.name} by {ctx.author.mention}.\nReason: {reason}")

    @modding.help(brief="Unban member", category="Guild", field="Server management", paragraph=2)
    @commands.command()
    @checks.guild_only()
    @checks.can_ban()
    async def unban(self, ctx, user_id: int, *, reason=None):
        '''
            `>>unban <user ID> <optional: reason>`
            Unban user.
        '''
        try:
            await ctx.guild.unban(discord.Object(user_id), reason=reason)
        except discord.NotFound:
            await ctx.deny()
        else:
            await ctx.confirm()

    @modding.help(brief="Ban user not in server", category="Guild", field="Server management", paragraph=2)
    @commands.command()
    @checks.guild_only()
    @checks.can_ban()
    async def hackban(self, ctx, user_id: int, *, reason=None):
        '''
            `>>hackban <user ID> <optional: reason>`
            Ban user who is not currently in server.
        '''
        try:
            await ctx.guild.unban(discord.Object(user_id), reason=reason)
        except discord.NotFound:
            await ctx.deny()
        else:
            await ctx.confirm()

    @modding.help(brief="Ban user from current channel", category="Guild", field="Server management", paragraph=1)
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
        except asyncio.TimeoutError:
            await ctx.channel.set_permissions(target=member, read_messages=None)
            await ctx.send(f"{member.mention} has been unbanned from this channel.")

    @modding.help(brief="Mute user from current channel", category="Guild", field="Server management", paragraph=1)
    @commands.command(aliases=["shutup"])
    @checks.guild_only()
    @checks.manager_only()
    async def channelmute(self, ctx, member: discord.Member, *, reason=None):
        '''
            `>>channelmute <member> <optional: reason>`
            Mute <member> from posting in the current channel.
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
        except asyncio.TimeoutError:
            await ctx.channel.set_permissions(target=member, send_messages=None)
            await ctx.send(f"{member.mention} has been unmuted from this channel.")

    @cmd_set.command(name="nsfwrole")
    async def cmd_set_nsfwrole(self, ctx, *, name):
        '''
            `>>set nsfwrole <role name>`
            Set role with <role name> as NSFW role.
            Name is case-insensitive.
        '''
        role = discord.utils.find(lambda r: name.lower()==r.name.lower(), ctx.guild.roles)
        if role:
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"nsfw_role_id": role.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
            await ctx.confirm()
        else:
            raise checks.CustomError(f"No role named {name} found.")

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
            Oh and evading muted role is useless as it will be added automatically when rejoin.
        '''
        role = discord.utils.find(lambda r: name.lower()==r.name.lower(), ctx.guild.roles)
        if role:
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"mute_role_id": role.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
            await ctx.confirm()
        else:
            raise checks.CustomError(f"No role named {name} found.")

    @cmd_unset.command(name="muterole")
    async def cmd_unset_muterole(self, ctx):
        '''
            `>>unset muterole`
            Unset muted role.
        '''
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$unset": {"mute_role_id": None}})
        await ctx.confirm()

    @modding.help(brief="Get/remove NSFW role, if applicable", category="Guild", field="Role", paragraph=1)
    @commands.command(aliases=["nsfw"])
    @checks.guild_only()
    async def creampie(self, ctx):
        '''
            `>>creampie`
            Get/remove NSFW role, if applicable.
        '''
        role_data = await self.guild_data.find_one({"guild_id": ctx.guild.id, "nsfw_role_id": {"$ne": None}}, projection={"_id": -1, "nsfw_role_id": 1})
        if role_data:
            role = discord.utils.find(lambda r: r.id==role_data["nsfw_role_id"], ctx.guild.roles)
            if role:
                if role in ctx.author.roles:
                    await ctx.author.remove_roles(role)
                else:
                    await ctx.author.add_roles(role)
                await ctx.confirm()
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
            You can use `{name}` for member name, `{mention}` for member mention, `{server}` for server name, `\{` and `\}` for literal { and } character.
        '''
        try:
            content = utils.str_format(f"Welcome message will be displayed as:\n{text}", name=ctx.author.display_name, mention=ctx.author.mention, server=ctx.guild.name)
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
        await ctx.send(utils.str_format(f"Welcome message will be displayed as:\n{DEFAULT_WELCOME}", name=ctx.author.display_name, mention=ctx.author.mention, server=ctx.guild.name))

    @cmd_set.command(name="dmrule", aliases=["rule"])
    async def set_dm_rule(self, ctx, *, text):
        '''
            `>>set dmrule <message>`
            Set message that will be DM'ed to new member.
            Use `{server}` for server name, `\{` and `\}` for literal { and } character.
        '''
        try:
            content = utils.str_format(f"Newcomer will be messaged:\n{text}", server=ctx.guild.name)
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
        artype -= 1
        if artype is None:
            return await ctx.send("Okay, no autorole, right.")
        msg = await ctx.send("Input the registration phrase:")
        try:
            message = await self.bot.wait_for("message", check=lambda m: m.author.id==ctx.author.id and m.channel.id==ctx.channel.id, timeout=600)
        except asyncio.TimeoutError:
            return await ctx.send("You took too long, so I'll just sleep then.")
        phrase = message.content
        msg = await ctx.send(
            "Do you want to set a custom response?\n"
            "You can use `{name}` and `{mention}` for member name and mention respectively, `{role}` for role name and `{server}` for server name"
            ", `\\{` and `\\}` for literal { and } character.\n"
            "Type `skip` to skip."
        )
        for _ in range(10):
            try:
                message = await self.bot.wait_for("message", check=lambda m: m.author.id==ctx.author.id and m.channel.id==ctx.channel.id, timeout=600)
            except asyncio.TimeoutError:
                return await ctx.send("You took too long, so I'll just sleep then.")
            if message.content.lower() == "skip":
                response = None
            else:
                response = message.content
                try:
                    test_response = utils.str_format(response, name=message.author.name, mention=message.author.mention, role=role.name, server=message.guild.name)
                except:
                    await ctx.send("Beep bop, format error. Please try again.")
                    continue
                else:
                    await ctx.send(f"Successful registration will be responsed with:\n{test_response}")
            break
        else:
            return await ctx.send("You don't have any intention to create a good response, right? Let's just stop here then.")
        if response:
            sentences = {
                "initial":  "Do you want the response to be automatically delete after 30s?\nBtw registration phrase will be deleted immediately.",
                "yes":      "OK it's a yes, got it.",
                "no":       "So it's a no then.",
                "timeout":  "Do you even need to think that long? I'll set up a yes then."
            }
            check = await ctx.yes_no_prompt(sentences, timeout=120)
            if check is None:
                check = True
        else:
            check = False
        await self.guild_data.update_one(
            {"guild_id": ctx.guild.id},
            {
                "$set": {"autorole_id": role.id, "autorole_type": artype, "autorole_phrase": phrase, "autorole_response": response, "autorole_response_delete": check},
                "$setOnInsert": {"guild_id": ctx.guild.id}
            },
            upsert=True
        )
        self.autorole_registration[ctx.guild.id] = phrase
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
            Log channel records member activity events such as member nick/roles change or member join/leave/ban.
            If logmessage is set, it also records message edit/delete.
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

    @cmd_set.command(name="logmessage")
    async def set_log_message(self, ctx):
        '''
            `>>set logmessage`
            Set message log.
            If log channel is set, this command enables message edit/delete log.
        '''
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"log_message": True}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.confirm()

    @cmd_unset.command(name="logmessage")
    async def unset_log_message(self, ctx):
        '''
            `>>unset logmessage`
            Unset message log.
        '''
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$unset": {"log_message": ""}})
        await ctx.confirm()

    @cmd_set.command(name="prefix", ignore_extra=False)
    async def cmd_prefix(self, ctx, prefix):
        '''
            `>>set prefix <prefix>`
            Add custom prefix.
            If <prefix> contains whitespaces then it must be enclosed in double-quote marks.
            If a custom prefix is set then the default `>>` prefix is not available anymore. You can explicitly set it up if you want it alongside new prefixes.
            Bot mention is always a prefix, regardless of custom prefixes.
            Limit 10 custom prefixes per server.
        '''
        current = self.bot.guild_prefixes.get(ctx.guild.id, [])
        if prefix in current:
            await ctx.send("This prefix is already used.")
        else:
            if len(current) >= 10:
                return await ctx.send("Too many prefixes.")
            current.append(prefix)
            current.sort(reverse=True)
            self.bot.guild_prefixes[ctx.guild.id] = current
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$addToSet": {"prefixes": prefix}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
            await ctx.confirm()

    @cmd_prefix.error
    async def cmd_prefix_error(self, ctx, error):
        if isinstance(error, commands.TooManyArguments):
            await ctx.send(
                "If you want to set prefix with whitespaces you must enclosed it in double-quote marks.\n"
                "Reason is that discord strips whitespaces at the beginning and end of message so prefix may registered incorrectly."
            )

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
            await ctx.deny()
        else:
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$pull": {"prefixes": prefix}})
            await ctx.confirm()

    @cmd_unset.command(name="allprefix")
    async def cmd_unset_all_prefix(self, ctx):
        '''
            `>>unset allprefix`
            Remove all custom prefixes.
        '''
        self.bot.guild_prefixes[ctx.guild.id] = []
        await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$set": {"prefixes": []}})
        await ctx.confirm()

    @cmd_set.command(name="eq", aliases=["eqalert"])
    async def set_eq_channel(self, ctx, *, data: modding.KeyValue({("", "channel"): discord.TextChannel, "minimal": bool, "role": discord.Role})=modding.EMPTY):
        '''
            `>>set eq <keyword: _|channel> <keyword: minimal> <keyword: ship> <keyword: role>`
            Set channel as PSO2 EQ Alert channel. If no channel is provided, use the current channel that the command is invoked in.
            Minimal is either true or false, which indicates minimal mode. Default is false.
            Ship can be a comma-separated list of ship numbers, or left untouched for all ships.
            Role, if set up, will be mentioned every alert, and can be taken by members via `>alertme` command.
            EQs will be noticed 2h45m, 1h45m, 45m, 15m prior, at present in non-minimal mode, and 1h45m, 45m prior in minimal mode.
        '''
        target = data.geteither("", "channel", default=ctx.channel)
        ship = data.get("ship", None)
        if ship:
            temp = (utils.to_int(s.strip(), default=0) for s in ship.split(","))
            all_ships = [s for s in temp if 0 < s <= 10]
            if not all_ships:
                return await ctx.send(f"Please input valid ships.")
        else:
            all_ships = None
        minimal = data.get("minimal", False)
        role = data.get("role", None)
        await self.guild_data.update_one(
            {"guild_id": ctx.guild.id},
            {
                "$set": {
                    "eq_channel_id": target.id,
                    "eq_alert_minimal": minimal,
                    "eq_ship": all_ships,
                    "eq_role_id": getattr(role, "id", None)
                },
                "$setOnInsert": {"guild_id": ctx.guild.id}
            },
            upsert=True
        )
        await ctx.send(
            f"EQ alert for {'ship '+', '.join(map(str, all_ships)) if all_ships else 'all ships'} has been set up for channel {target.mention} "
            f"in {'' if minimal else 'non-'}minimal mode "
            f"with {'role '+role.name if role else 'no role'} mention."
        )

    @cmd_unset.command(name="eq", aliases=["eqalert"])
    async def unset_eq_channel(self, ctx):
        '''
            `>>unset eq`
            Unset PSO2 EQ Alert.
        '''
        result = await self.guild_data.update_one(
            {"guild_id": ctx.guild.id},
            {"$unset": {"eq_channel_id": "", "eq_alert_minimal": "", "eq_ship": "", "eq_role": ""}}
        )
        if result.modified_count > 0:
            await ctx.confirm()
        else:
            await ctx.deny()

    @commands.Cog.listener()
    async def on_message(self, message):
        member = message.author
        if member.bot or not message.guild:
            return
        check_not_in = message.guild.id not in self.autorole_registration
        check_equal = message.content == self.autorole_registration.get(message.guild.id)
        if check_not_in or check_equal:
            guild_data = await self.guild_data.find_one(
                {"guild_id": message.guild.id},
                projection={"_id": False, "autorole_id": True, "autorole_type": True, "autorole_phrase": True, "autorole_response": True, "autorole_response_delete": True}
            ) or {}
            if check_not_in:
                phrase = guild_data.get("autorole_phrase", False)
                self.autorole_registration[message.guild.id] = phrase
                check_equal = message.content == phrase
        if check_equal:
            role = discord.utils.find(lambda r: r.id==guild_data["autorole_id"], message.guild.roles)
            if not role:
                return
            artype = guild_data["autorole_type"]
            if artype == 0:
                if role in member.roles:
                    return
                else:
                    await member.add_roles(role)
            elif artype == 1:
                if role in member.roles:
                    await member.remove_roles(role)
                else:
                    return
            response = guild_data["autorole_response"]
            if response:
                await message.channel.send(
                    utils.str_format(response, name=message.author.name, mention=message.author.mention, role=role.name, server=message.guild.name),
                    delete_after=30 if guild_data.get("autorole_response_delete", True) else None
                )
            await message.delete()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        guild = member.guild
        guild_data = await self.guild_data.find_one(
            {"guild_id": guild.id},
            projection={
                "_id": False, "log_channel_id": True, "welcome_channel_id": True, "welcome_message": True, "welcome_rule": True,
                "autorole_type": True, "autorole_id": True, "mute_role_id": True, "muted_member_ids": True}
        )
        if guild_data:
            if member.id in guild_data.get("muted_member_ids", ()):
                mute_role = discord.utils.find(lambda r: r.id==guild_data["mute_role_id"], guild.roles)
                if mute_role:
                    await member.add_roles(mute_role)
            log_channel = guild.get_channel(guild_data.get("log_channel_id"))
            if log_channel:
                embed = discord.Embed(colour=discord.Colour.dark_orange())
                embed.add_field(name="Event", value="member_join", inline=False)
                embed.add_field(name="ID", value=member.id)
                embed.add_field(name="Name", value=member.mention)
                embed.set_footer(text=utils.format_time(utils.now_time()))
                await log_channel.send(embed=embed)
            welcome_channel = guild.get_channel(guild_data.get("welcome_channel_id"))
            if welcome_channel:
                welcome_message = guild_data.get("welcome_message", DEFAULT_WELCOME)
                await welcome_channel.send(utils.str_format(welcome_message, name=member.display_name, mention=member.mention, server=member.guild.name, guild=member.guild.name))
            welcome_rule = guild_data.get("welcome_rule")
            if welcome_rule:
                self.bot.do_after(member.send(utils.str_format(welcome_rule, server=member.guild.name)), 5)
            autorole_type = guild_data.get("autorole_type", None)
            if autorole_type == 1:
                role = discord.utils.find(lambda r: r.id==guild_data["autorole_id"], guild.roles)
                if role:
                    await member.add_roles(role)

    @commands.Cog.listener()
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
                embed.add_field(name="Name", value=member.mention)
                embed.set_footer(text=utils.format_time(utils.now_time()))
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if user.bot:
            return
        guild_data = await self.guild_data.find_one(
            {"guild_id": guild.id},
            projection={"_id": False, "log_channel_id": True}
        )
        if guild_data:
            log_channel = guild.get_channel(guild_data.get("log_channel_id"))
            if log_channel:
                embed = discord.Embed(colour=discord.Colour.dark_orange())
                embed.add_field(name="Event", value="member_ban", inline=False)
                embed.add_field(name="ID", value=user.id)
                embed.add_field(name="Name", value=user.mention)
                embed.set_footer(text=utils.format_time(utils.now_time()))
                await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.bot:
            return
        guild = before.guild
        guild_data = await self.guild_data.find_one(
            {"guild_id": guild.id},
            projection={"_id": False, "log_channel_id": True, "log_message": True, "mute_role_id": True, "muted_member_ids": True}
        )
        if guild_data:
            old_roles = set(before.roles)
            new_roles = set(after.roles)
            nick_change = before.nick != after.nick
            role_change = old_roles != new_roles
            if nick_change or role_change:
                embed = discord.Embed(colour=discord.Colour.dark_orange())
                embed.add_field(name="Event", value="member_update", inline=False)
                embed.add_field(name="ID", value=before.id)
                embed.add_field(name="Name", value=before.mention)
                if nick_change:
                    embed.add_field(name="Old nickname", value=before.nick, inline=False)
                    embed.add_field(name="New nickname", value=after.nick, inline=False)
                if role_change:
                    add_roles = new_roles - old_roles
                    remove_roles = old_roles - new_roles
                    if add_roles:
                        embed.add_field(name="Roles add", value=", ".join([r.name for r in add_roles]), inline=False)
                        if guild_data.get("mute_role_id") in (r.id for r in add_roles):
                            if before.id not in guild_data.get("muted_members", ()):
                                await self.guild_data.update_one({"guild_id": guild.id}, {"$addToSet": {"muted_member_ids": before.id}})
                    if remove_roles:
                        embed.add_field(name="Roles remove", value=", ".join([r.name for r in remove_roles]), inline=False)
                        if guild_data.get("mute_role_id") in (r.id for r in remove_roles):
                            if before.id in guild_data.get("muted_members", ()):
                                await self.guild_data.update_one({"guild_id": guild.id}, {"$pull": {"muted_member_ids": before.id}})
                embed.set_footer(text=utils.format_time(utils.now_time()))

                if guild_data.get("log_message"):
                    log_channel = guild.get_channel(guild_data.get("log_channel_id"))
                    if log_channel:
                        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        guild = message.guild
        if not guild:
            return
        guild_data = await self.guild_data.find_one(
            {"guild_id": guild.id},
            projection={"_id": False, "log_channel_id": True, "log_message": True}
        )
        if guild_data:
            if guild_data.get("log_message"):
                log_channel = guild.get_channel(guild_data.get("log_channel_id"))
                if log_channel:
                    file_ = None
                    embed = discord.Embed(colour=discord.Colour.dark_orange())
                    embed.add_field(name="Event", value="message_delete", inline=False)
                    embed.add_field(name="ID", value=message.id)
                    embed.add_field(name="Author", value=message.author.mention)
                    embed.add_field(name="Channel", value=message.channel.mention)
                    if message.content:
                        embed.add_field(name="Content", value=f"{message.content[:1000]}" if len(message.content)>1000 else message.content, inline=False)
                    if message.attachments:
                        a = message.attachments[0]
                        try:
                            bytes_ = await self.bot.fetch(a.proxy_url)
                        except checks.CustomError:
                            rest = message.attachments
                        else:
                            file_ = discord.File(BytesIO(bytes_), a.filename)
                            rest = message.attachments[1:]
                        if rest:
                            embed.add_field(name="Attachments", value="\n".join((a.proxy_url for a in rest)))
                    embed.set_footer(text=utils.format_time(utils.now_time()))
                    await log_channel.send(embed=embed, file=file_)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return
        guild = before.guild
        if not guild:
            return
        guild_data = await self.guild_data.find_one(
            {"guild_id": guild.id},
            projection={"_id": False, "log_channel_id": True, "log_message": True}
        )
        if guild_data:
            if guild_data.get("log_message"):
                log_channel = guild.get_channel(guild_data.get("log_channel_id"))
                if log_channel:
                    if before.content != after.content:
                        embed = discord.Embed(colour=discord.Colour.dark_orange())
                        embed.add_field(name="Event", value="message_edit", inline=False)
                        embed.add_field(name="ID", value=before.id)
                        embed.add_field(name="Author", value=before.author.mention)
                        embed.add_field(name="Channel", value=before.channel.mention)
                        embed.add_field(name="Before", value=f"{before.content[:1000]}..." if len(before.content)>1000 else before.content or "None", inline=False)
                        embed.add_field(name="After", value=f"{after.content[:1000]}..." if len(after.content)>1000 else after.content or "None", inline=False)
                        embed.set_footer(text=utils.format_time(utils.now_time()))
                        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if messages:
            channel = messages[0].channel
            guild = channel.guild
            guild_data = await self.guild_data.find_one(
                {"guild_id": guild.id},
                projection={"_id": False, "log_channel_id": True, "log_message": True}
            )
            if guild_data:
                if guild_data.get("log_message"):
                    log_channel = guild.get_channel(guild_data.get("log_channel_id"))
                    if log_channel:
                        embed = discord.Embed(colour=discord.Colour.dark_orange())
                        embed.add_field(name="Event", value="bulk_message_delete", inline=False)
                        embed.add_field(name="Count", value=len(messages))
                        embed.add_field(name="Channel", value=channel.mention)
                        embed.set_footer(text=utils.format_time(utils.now_time()))
                        all_text = "\n".join((f"{m.created_at.strftime('%Y-%m-%d %I:%M:%S')} {m.id: <18} {m.author}\n{textwrap.indent(m.content, '    ')}" for m in messages))
                        await log_channel.send(embed=embed, file=discord.File(BytesIO(all_text.encode("utf-8")), filename="purged_messages.log"))

    async def get_selfroles(self, guild):
        role_data = await self.guild_data.find_one({"guild_id": guild.id}, projection={"_id": -1, "selfrole_ids": 1})
        if role_data:
            roles = (discord.utils.find(lambda r: r.id==role_id, guild.roles) for role_id in role_data.get("selfrole_ids", []))
            return [r for r in roles if r is not None]
        else:
            return []

    @modding.help(brief="Get selfrole with given name, if applicable", category="Guild", field="Role", paragraph=0)
    @commands.group(invoke_without_command=True)
    @checks.guild_only()
    async def selfrole(self, ctx, *, name):
        '''
            `>>selfrole <name>`
            Get a selfrole from selfrole pool, or remove if you already had it.
            Role name is case-insensitive.
        '''
        if ctx.invoked_subcommand is None:
            role = discord.utils.find(lambda r: r.name.lower()==name.lower(), ctx.guild.roles)
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

    @modding.help(brief="Add an existed role to selfrole pool", category="Guild", field="Role", paragraph=0)
    @selfrole.command()
    @checks.guild_only()
    @checks.manager_only()
    async def add(self, ctx, *, name):
        '''
            `>>selfrole add <name>`
            Add a role to selfrole pool.
            Role name is case-insensitive.
        '''
        role = discord.utils.find(lambda r: r.name.lower()==name.lower(), ctx.guild.roles)
        if role:
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$addToSet": {"selfrole_ids": role.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
            await ctx.confirm()
        else:
            await ctx.deny()

    @modding.help(brief="Remove a role from selfrole pool", category="Guild", field="Role", paragraph=0)
    @selfrole.command()
    @checks.guild_only()
    @checks.manager_only()
    async def remove(self, ctx, *, name):
        '''
            `>>selfrole remove <name>`
            Remove a selfrole from pool.
            Role name is case-insensitive.
        '''
        role = discord.utils.find(lambda r: r.name.lower()==name.lower(), ctx.guild.roles)
        if role:
            await self.guild_data.update_one({"guild_id": ctx.guild.id}, {"$pull": {"selfrole_ids": role.id}})
            await ctx.confirm()
        else:
            await ctx.deny()

    @modding.help(brief="Remove all selfroles from self", category="Guild", field="Role", paragraph=0)
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

    @modding.help(brief="Display server selfrole pool", category="Guild", field="Role", paragraph=0)
    @selfrole.command(name="list", aliases=["pool"])
    @checks.guild_only()
    async def role_list(self, ctx):
        '''
            `>>selfrole list`
            Display server selfrole pool.
        '''
        roles = await self.get_selfroles(ctx.guild)
        if roles:
            paging = utils.Paginator(
                roles, 10,
                title=f"{ctx.guild.name}'s selfrole pool:",
                description=lambda i, x: f"`{i+1}.` {x.name}"
            )
            await paging.navigate(ctx)
        else:
            await ctx.send("Server has no selfrole.")

    @modding.help(brief="Bar chart showing selfrole distribution", category="Guild", field="Role", paragraph=0)
    @selfrole.command()
    @checks.guild_only()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def distribution(self, ctx):
        '''
            `>>selfrole distribution`
            Draw a chart showing server selfrole distribution.
        '''
        async with ctx.typing():
            roles = await self.get_selfroles(ctx.guild)
            if not roles:
                return await ctx.send("Server has no selfrole.")
            colors = {(0, 0, 0), (255, 255, 255)}
            check_roles = []
            all_members = set()
            for role in roles:
                all_members.update(role.members)
                rgb = role.colour.to_rgb()
                while rgb in colors:
                    rgb = (random.randrange(256), random.randrange(256), random.randrange(256))
                colors.add(rgb)
                check_roles.append({"name": role.name, "count": {"": len(role.members)}, "color": utils.adjust_alpha(rgb, 255)})
            check_roles.append({"name": "All with selfroles", "count": {"": len(all_members)}, "color": (255, 255, 255, 255)})

            bytes_ = await utils.bar_chart(check_roles, unit_y="members", unit_x="", loop=self.bot.loop)
            if bytes_:
                await ctx.send(file=discord.File(bytes_, filename="distribution.png"))
            else:
                await ctx.send("There's no one with selfrole.")

    @modding.help(brief="Give member mute role if applicable", category="Guild", field="Server management", paragraph=1)
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
        role_data = await self.guild_data.find_one({"guild_id": ctx.guild.id, "mute_role_id": {"$ne": None}}, projection={"_id": -1, "mute_role_id": 1})
        if role_data:
            muted_role = discord.utils.find(lambda r: r.id==role_data["mute_role_id"], ctx.guild.roles)
            await member.add_roles(muted_role)
            try:
                reason, duration = utils.extract_time(reason)
                duration = duration.total_seconds()
            except:
                traceback.print_exc()
                return await ctx.send("Time too large.")
            if duration > 0:
                await ctx.send(f"{member.mention} has been muted for {utils.seconds_to_text(duration)}.\nReason: {reason}")
                try:
                    before, after = await self.bot.wait_for(
                        "member_update",
                        check=lambda b,a: a.id==member.id and a.guild.id==member.guild.id and mute_role in b.roles and muted_role not in a.roles,
                        timeout=duration
                    )
                except asyncio.TimeoutError:
                    await member.remove_roles(muted_role)
                    await ctx.send(f"{member.mention} has been unmuted.")
            else:
                await ctx.send(f"{member.mention} has been muted.")
        else:
            await ctx.send("Muted role is not set up in this server.")

    @modding.help(brief="Remove mute role from a member", category="Guild", field="Server management", paragraph=1)
    @commands.command()
    @checks.guild_only()
    @checks.manager_only()
    async def unmute(self, ctx, member: discord.Member):
        '''
            `>>unmute <member>`
            Remove muted role from member.
        '''
        role_data = await self.guild_data.find_one({"guild_id": ctx.guild.id, "mute_role_id": {"$ne": None}}, projection={"_id": -1, "mute_role_id": 1})
        if role_data:
            muted_role = discord.utils.find(lambda r: r.id==role_data["mute_role_id"], ctx.guild.roles)
            await member.remove_roles(muted_role)
            await ctx.send(f"{member.mention} has been unmute.")
        else:
            await ctx.send("Muted role is not set up in this server.")

    @modding.help(brief="Bulk delete messages", category="Guild", field="Server management", paragraph=3)
    @commands.command()
    @checks.guild_only()
    @checks.manager_only()
    async def purge(self, ctx, number: int, *members: discord.Member):
        '''
            `>>purge <number> <optional: list of members>`
            Purge messages in the current channel.
            If members is provided, purge only messages of those members, otherwise purge everything.
        '''
        if number > 0:
            try:
                await ctx.message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                return
            try:
                if members:
                    await ctx.channel.purge(limit=number, check=lambda m: m.author in members)
                else:
                    await ctx.channel.purge(limit=number)
            except discord.NotFound:
                pass

    @modding.help(brief="Clear reactions from messages", category="Guild", field="Server management", paragraph=3)
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

    @commands.Cog.listener()
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

    @modding.help(brief="Display server prefixes", category="Guild", field="Info", paragraph=0)
    @commands.command(name="prefix")
    @checks.guild_only()
    async def guild_prefix(self, ctx):
        '''
            `>>prefix`
            Display all server prefixes.
        '''
        prefixes = await self.bot.get_prefix(ctx.message)
        prefixes.remove(f"<@!{ctx.me.id}> ")
        await ctx.send(embed=discord.Embed(title=f"Prefixes for {ctx.guild.name}", description="\n".join((f"{i+1}. {p}" for i, p in enumerate(prefixes)))))

    @modding.help(brief="Display server info", category="Guild", field="Info", paragraph=0)
    @commands.command(aliases=["serverinfo"])
    @checks.guild_only()
    async def guildinfo(self, ctx):
        '''
            `>>serverinfo`
            Display server info.
        '''
        guild = ctx.guild
        roleinfo = ", ".join((r.mention for r in reversed(guild.roles)))
        role_pages = utils.split_page(roleinfo, 1000, safe_mode=False)
        embeds = []
        for page in role_pages:
            embed = discord.Embed(title=guild.name, colour=discord.Colour.blue())
            embed.set_thumbnail(url=str(guild.icon_url_as(format="png")))
            embed.add_field(name="ID", value=guild.id)
            embed.add_field(name="Owner", value=guild.owner.mention)
            embed.add_field(name="Created at", value=guild.created_at.strftime("%d-%m-%Y"))
            embed.add_field(name="Region", value=str(guild.region).title().replace("Us-", "US ").replace("Vip-", "VIP ").replace("Eu-", "EU "))
            embed.add_field(name="Features", value=", ".join(guild.features) or "None", inline=False)
            embed.add_field(name="Channels", value=f"{len(guild.categories)} categories\n{len(guild.text_channels)} text channels\n{len(guild.voice_channels)} voice channels")
            embed.add_field(name="Members", value=f"{guild.member_count} members")
            embed.add_field(name="Roles", value=page, inline=False)
            embeds.append(embed)
        paging = utils.Paginator(embeds, render=False)
        await paging.navigate(ctx)

    @modding.help(brief="Display role info", category="Guild", field="Info", paragraph=0)
    @commands.command()
    @checks.guild_only()
    async def roleinfo(self, ctx, *, name):
        '''
            `>>roleinfo <name>`
            Display role info. Name is case-insensitive.
        '''
        role = discord.utils.find(lambda r: r.name.lower()==name.lower(), ctx.guild.roles)
        if not role:
            return await ctx.send(f"No role name {name} found.")
        else:
            embed = discord.Embed(title=role.name, colour=discord.Colour.blue())
            embed.add_field(name="ID", value=role.id)
            embed.add_field(name="Position", value=role.position)
            embed.add_field(name="Created at", value=role.created_at.strftime("%d-%m-%Y"))
            embed.add_field(name="Color", value=f"#{role.color.value:06X}")
            embed.add_field(name="Members", value=len(role.members), inline=False)
            perms = ("administrator", "manage_guild", "manage_channels", "manage_roles", "kick_members", "ban_members", "manage_nicknames", "manage_webhooks", "add_reactions", "view_audit_log", "manage_emojis",  "manage_messages", "read_messages", "send_messages", "send_tts_messages", "embed_links", "attach_files", "read_message_history", "mention_everyone", "external_emojis", "connect", "speak", "mute_members", "deafen_members", "move_members", "use_voice_activation", "change_nickname")
            embed.add_field(name="Permissions", value=", ".join((p for p in perms if getattr(role.permissions, p, False))) or "None", inline=False)
            pic = Image.new("RGB", (50, 50), role.colour.to_rgb())
            bytes_ = BytesIO()
            pic.save(bytes_, "png")
            bytes_.seek(0)
            f = discord.File(bytes_, filename="role_color.png")
            embed.set_thumbnail(url="attachment://role_color.png")
            await ctx.send(file=f, embed=embed)

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

    @modding.help(brief="Disable bot commands", category="Guild", field="Server management", paragraph=0)
    @commands.group(name="disable")
    @checks.guild_only()
    @checks.manager_only()
    async def cmd_disable(self, ctx):
        '''
            `>>disable`
            Base command. Does nothing by itself, but with subcommands can be used to disable certain bot features in server.
            Note that enabled is the default state, and disabled overwrites and takes precedence over that.
            Subcommands include:
            -`server` - Disable all bot commands in server
            -`channel` - Disable all bot commands in a channel
            -`member` - Prevent member from using bot commands
            -`command` - Disable a certain command
        '''
        pass

    @modding.help(brief="Enable bot commands", category="Guild", field="Server management", paragraph=0)
    @commands.group(name="enable")
    @checks.guild_only()
    @checks.manager_only()
    async def cmd_enable(self, ctx):
        '''
            `>>enable`
            Base command. Does nothing by itself, but with subcommands can be used to enable certain bot features in server.
            Note that enabled is the default state, and disabled overwrites and takes precedence over that.
            Subcommands include:
            -`server` - Enable all bot commands in server
            -`channel` - Enable all bot commands in a channel
            -`member` - Enable bot commands for member
            -`command` - Enable a certain command
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

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Guild(bot))
