import discord
from discord.ext import commands
from . import utils
from .utils import checks, config
import asyncio
import unicodedata
from io import BytesIO

#==================================================================================================================================================

class GuildBot:
    '''
    Doing stuff related to server.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.guild_task_list = bot.db.guild_task_list
        self.banned_emojis = []

    @commands.group(name="set")
    @checks.manager_only()
    async def cmd_set(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @commands.group(name="unset")
    @checks.manager_only()
    async def cmd_unset(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @commands.command()
    @checks.manager_only()
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        try:
            await member.kick(reason=reason)
            await ctx.send("{member.name} has been kicked.")
            await member.send(f"You have been kicked from {ctx.guild.name} by {ctx.author.name}.\nReason: {reason}")
        except:
            await ctx.deny()

    @commands.command()
    @checks.manager_only()
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        try:
            await member.ban(reason=reason)
            await ctx.send("{member.name} has been banned.")
            await member.send(
                f"You have been banned from {ctx.guild.name} by {ctx.author.name}.\nReason: {reason}\n\n"
                "If you think this action is unjustified, please contact the mods to unlift the ban."
            )
        except:
            await ctx.deny()

    @commands.command()
    @checks.manager_only()
    async def unban(self, ctx, user_id: int, *, reason=None):
        try:
            user = await self.bot.get_user_info(user_id)
            await user.unban(reason=reason)
            await ctx.send("{user.name} has been unbanned.")
        except:
            await ctx.deny()

    @commands.command()
    @checks.manager_only()
    async def hackban(self, ctx, user_id: int, *, reason=None):
        try:
            user = await self.bot.get_user_info(user_id)
            await user.ban(reason=reason)
            await ctx.send("{user.name} has been banned.")
        except:
            await ctx.deny()

    @commands.command()
    @checks.manager_only()
    async def channelban(self, ctx, member: discord.Member, *, reason=None):
        try:
            await ctx.channel.set_permissions(target=member, read_messages=False)
        except:
            return await ctx.deny()
        try:
            duration = utils.extract_time(reason).total_seconds()
        except:
            return await ctx.send("Time too large.")
        if duration <= 0:
            duration = 600
        await ctx.send(f"{member.mention} has been banned from this channel for {utils.seconds_to_text(duration)}.")
        try:
            before, after = await self.bot.wait_for(
                "guild_channel_update",
                check=lambda b, a: a.overwrites_for(member).read_messages in (None, True),
                timeout=duration
            )
        except:
            await ctx.channel.set_permissions(target=member, read_messages=None)
            await ctx.send(f"{member.mention} has been unbanned from this channel.")

    @commands.command(aliases=["shutup"])
    @checks.manager_only()
    async def channelmute(self, ctx, member: discord.Member, *, reason=None):
        try:
            await ctx.channel.set_permissions(target=member, send_messages=False)
        except:
            return await ctx.deny()
        try:
            duration = utils.extract_time(reason).total_seconds()
        except:
            return await ctx.send("Time too large.")
        if duration <= 0:
            duration = 600
        await ctx.send(f"{member.mention} has been muted from this channel for {utils.seconds_to_text(duration)}.")
        try:
            before, after = await self.bot.wait_for(
                "guild_channel_update",
                check=lambda b, a: a.overwrites_for(member).send_messages in (None, True),
                timeout=duration
            )
        except:
            await ctx.channel.set_permissions(target=member, send_messages=None)
            await ctx.send(f"{member.mention} has been unmuted from this channel.")

    @cmd_set.command()
    async def nsfwrole(self, ctx, *, name):
        role = discord.utils.find(lambda r: name.lower() in r.name.lower(), ctx.guild.roles)
        if role:
            await self.guild_task_list.update_one({"guild_id": ctx.guild.id}, {"$set": {"nsfw_role_id": role.id}}, upsert=True)
            return await ctx.confirm()
        else:
            await ctx.deny()

    @cmd_unset.command(name="nsfwrole")
    async def nonsfwrole(self, ctx, *, name):
        role = discord.utils.find(lambda r: name.lower() in r.name.lower(), ctx.guild.roles)
        if role:
            await self.guild_task_list.update_one({"guild_id": ctx.guild.id}, {"$unset": {"nsfw_role_id": role.id}})
            return await ctx.confirm()
        else:
            await ctx.deny()

    @commands.command()
    async def creampie(self, ctx):
        '''
            Add role 18+ for accessing creampie channel, which is NSFW.
        '''
        role_data = await self.guild_task_list.find_one({"guild_id": ctx.guild.id})
        role = discord.utils.find(lambda r: r.id==role_data.get("nsfw_role_id"), ctx.guild.roles)
        if role:
            await ctx.author.add_roles(role)
            await ctx.confirm()
        else:
            await ctx.deny()

    @commands.command()
    async def censored(self, ctx):
        '''
            Remove role 18+.
        '''
        role_data = await self.guild_task_list.find_one({"guild_id": ctx.guild.id})
        role = discord.utils.find(lambda r: r.id==role_data.get("nsfw_role_id"), ctx.guild.roles)
        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
            await ctx.confirm()
        else:
            await ctx.deny()

    async def get_selfroles(self, guild):
        role_data = await self.guild_task_list.find_one({"guild_id": guild.id})
        if role_data:
            roles = [discord.utils.find(lambda r: r.id==role_id, guild.roles) for role_id in role_data["selfrole_ids"]]
            return [r for r in roles if r is not None]
        else:
            return []

    @cmd_set.command()
    async def welcome(self, ctx, channel: discord.TextChannel=None):
        target = channel or ctx.channel
        await self.guild_task_list.update_one({"guild_id": ctx.guild.id}, {"$set": {"welcome_channel_id": target.id}}, upsert=True)
        await ctx.confirm()

    @cmd_unset.command(name="welcome")
    async def nowelcome(self, ctx):
        result = await self.guild_task_list.update_one({"guild_id": ctx.guild.id}, {"$unset": {"welcome_channel_id": ""}})
        if result.acknowledged:
            await ctx.confirm()

    @cmd_set.command(name="log")
    async def logchannel(self, ctx, channel: discord.TextChannel=None):
        target = channel or ctx.channel
        await self.guild_task_list.update_one({"guild_id": ctx.guild.id}, {"$set": {"log_channel_id": target.id}}, upsert=True)
        await ctx.confirm()

    @cmd_unset.command(name="log")
    async def nolog(self, ctx):
        result = await self.guild_task_list.update_one({"guild_id": ctx.guild.id}, {"$log": {"welcome_channel_id": ""}})
        if result.acknowledged:
            await ctx.confirm()

    async def on_member_join(self, member):
        if member.bot:
            return
        guild = member.guild
        guild_data = await self.guild_task_list.find_one({"guild_id": guild.id})
        if guild_data:
            welcome_channel = guild.get_channel(guild_data.get("welcome_channel_id"))
            if welcome_channel:
                await welcome_channel.send(f"*\"Eeeeehhhhhh, go away {member.mention}, I don't want any more work...\"*")
                if guild.id == config.OTOGI_GUILD_ID:
                    await asyncio.sleep(5)
                    otogi_guild = self.bot.get_guild(config.OTOGI_GUILD_ID)
                    await member.send(
                        f"Welcome to {otogi_guild.name}.\n"
                        "Please read the rules in #server-rules before doing anything.\n"
                        "You can use `>>help` to get a list of available commands.\n\n"
                        "Have a nice day!"
                    )
            log_channel = guild.get_channel(guild_data.get("log_channel_id"))
            if log_channel:
                embed = discord.Embed(colour=discord.Colour.dark_orange())
                embed.add_field(name="Event", value="member_join", inline=False)
                embed.add_field(name="ID", value=member.id)
                embed.add_field(name="Name", value=str(member))
                embed.set_footer(text=utils.format_time(utils.now_time()))
                await log_channel.send(embed=embed)

    async def on_member_remove(self, member):
        if member.bot:
            return
        guild = member.guild
        guild_data = await self.guild_task_list.find_one({"guild_id": guild.id})
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
        guild_data = await self.guild_task_list.find_one({"guild_id": guild.id})
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
        guild = message.channel.guild
        guild_data = await self.guild_task_list.find_one({"guild_id": guild.id})
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
        guild = before.channel.guild
        guild_data = await self.guild_task_list.find_one({"guild_id": guild.id})
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

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def selfrole(self, ctx, *, name):
        if ctx.invoked_subcommand is None:
            role = discord.utils.find(lambda r:r.name.lower()==name.lower(), ctx.guild.roles)
            roles = await self.get_selfroles(ctx.guild)
            if role in roles:
                for r in roles:
                    if r in ctx.author.roles:
                        await ctx.author.remove_roles(r)
                        break
                await ctx.author.add_roles(role)
                await ctx.confirm()
            else:
                await ctx.deny()

    @selfrole.command()
    @checks.manager_only()
    async def add(self, ctx, *, name):
        role = discord.utils.find(lambda r:r.name.lower()==name.lower(), ctx.guild.roles)
        await self.guild_task_list.update_one({"guild_id": ctx.guild.id}, {"$addToSet": {"selfrole_ids": role.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.confirm()

    @selfrole.command()
    @checks.manager_only()
    async def remove(self, ctx, *, name):
        role = discord.utils.find(lambda r:r.name.lower()==name.lower(), ctx.guild.roles)
        await self.guild_task_list.update_one({"guild_id": ctx.guild.id}, {"$pull": {"selfrole_ids": role.id}})
        await ctx.confirm()

    @selfrole.command()
    async def empty(self, ctx):
        roles = await self.get_selfroles(ctx.guild)
        for role in roles:
            if role in ctx.author.roles:
                await ctx.author.remove_roles(role)
        await ctx.confirm()

    @selfrole.command(name="list")
    async def role_list(self, ctx):
        roles = await self.get_selfroles(ctx.guild)
        await ctx.send(embed=discord.Embed(description="\n".join([f"{i+1}. {r.name}" for i, r in enumerate(roles)])))

    @selfrole.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def distribution(self, ctx):
        async with ctx.typing():
            roles = await self.get_selfroles(ctx.guild)
            check_roles = []
            total_members = 0
            for role in roles:
                member_count = len(role.members)
                total_members += member_count
                check_roles.append((role.name, member_count, role.colour.to_rgb()))
            bytes_ = await utils.pie_chart(check_roles, unit="member(s)")
            if total_members == 0:
                await ctx.send("There's no one with selfrole.")
            else:
                await ctx.send(file=discord.File(bytes_, filename="distribution.png"))

    @commands.command()
    @checks.manager_only()
    async def mute(self, ctx, member: discord.Member, *, reason=""):
        muted_role = discord.utils.find(lambda r:r.name=="Muted", ctx.guild.roles)
        if muted_role is None:
            return await ctx.deny()
        await member.add_roles(muted_role)
        try:
            duration = utils.extract_time(reason).total_seconds()
        except:
            return await ctx.send("Time too large.")
        if duration > 0:
            await ctx.send(f"{member.mention} has been muted for {utils.seconds_to_text(duration)}.")
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

    @commands.command()
    @checks.manager_only()
    async def unmute(self, ctx, member: discord.Member):
        muted_role = discord.utils.find(lambda r:r.name=="Muted", ctx.guild.roles)
        await member.remove_roles(muted_role)
        await ctx.send(f"{member.mention} has been unmute.")

    @commands.command()
    @checks.manager_only()
    async def purge(self, ctx, number: int=100, *members: discord.Member):
        if number > 0:
            if members:
                await ctx.channel.purge(limit=number, check=lambda m:m.author in members)
            else:
                await ctx.channel.purge(limit=number)
            await ctx.confirm()

    @commands.command()
    @checks.manager_only()
    async def purgereact(self, ctx, *msg_ids):
        for msg_id in msg_ids:
            msg = await ctx.get_message(msg_id)
            await msg.clear_reactions()
            await ctx.confirm()

    @commands.command()
    @checks.owner_only()
    async def deletemessage(self, ctx, msg_id: int):
        try:
            message = await ctx.get_message(msg_id)
            await message.delete()
            await ctx.confirm()
        except Exception as e:
            print(e)
            await ctx.deny()

    @commands.command()
    @checks.otogi_guild_only()
    @checks.manager_only()
    async def reactban(self, ctx, *emojis):
        for emoji in emojis:
            em = discord.utils.find(lambda e:emoji==str(e), self.bot.emojis)
            if em:
                self.banned_emojis.append(em.id)
            else:
                try:
                    em = int(em)
                except:
                    pass
                self.banned_emojis.append(emoji)
        await ctx.confirm()

    @commands.command()
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
                    await reaction.message.clear_reactions()

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(GuildBot(bot))
