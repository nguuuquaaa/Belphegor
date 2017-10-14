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
        self.welcome_channel_list = bot.db.welcome_channel_list
        self.banned_emojis = []
        self.nsfw_role_list = bot.db.nsfw_role_list
        self.selfrole_list = bot.db.selfrole_list

    @commands.command()
    @checks.manager_only()
    async def kick(self, ctx, user: discord.User, *, reason=None):
        try:
            await user.kick(reason=reason)
            await ctx.send("{user.name} has been kicked.")
            await user.send(f"You have been kicked from {ctx.guild.name} by {ctx.author.name}.\nReason: {reason}")
        except:
            await ctx.deny()

    @commands.command()
    @checks.manager_only()
    async def ban(self, ctx, user: discord.User, *, reason=None):
        try:
            await user.ban(reason=reason)
            await ctx.send("{user.name} has been banned.")
            await user.send(
                f"You have been banned from {ctx.guild.name} by {ctx.author.name}.\nReason: {reason}\n\n"
                "If you think this action is unjustified, please contact the mods to unlift the ban.")
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
    async def setnsfwrole(self, ctx, *, name):
        role = discord.utils.find(lambda r: name.lower() in r.name.lower(), ctx.guild.roles)
        if role:
            await self.nsfw_role_list.update_one({"guild_id": ctx.guild.id}, {"$set": {"role_id": role.id}}, upsert=True)
            return await ctx.confirm()
        else:
            await ctx.deny()

    @commands.command()
    async def creampie(self, ctx):
        '''
            Add role 18+ for accessing creampie channel, which is NSFW.
        '''
        role_data = await self.nsfw_role_list.find_one({"guild_id": ctx.guild.id})
        role = discord.utils.find(lambda r: r.id==role_data["role_id"], ctx.guild.roles)
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
        role_data = await self.nsfw_role_list.find_one({"guild_id": ctx.guild.id})
        role = discord.utils.find(lambda r: r.id==role_data["role_id"], ctx.guild.roles)
        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
            await ctx.confirm()
        else:
            await ctx.deny()

    async def get_selfroles(self, guild):
        role_data = await self.selfrole_list.find_one({"guild_id": guild.id})
        if role_data:
            roles = [discord.utils.find(lambda r: r.id==role_id, guild.roles) for role_id in role_data["role_ids"]]
            return [r for r in roles if r is not None]
        else:
            return []

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
    @checks.role_manager_only()
    async def add(self, ctx, *, name):
        role = discord.utils.find(lambda r:r.name.lower()==name.lower(), ctx.guild.roles)
        await self.selfrole_list.update({"guild_id": ctx.guild.id}, {"$addToSet": {"role_ids": role.id}, "$setOnInsert": {"guild_id": ctx.guild.id}}, upsert=True)
        await ctx.confirm()

    @selfrole.command()
    @checks.role_manager_only()
    async def remove(self, ctx, *, name):
        role = discord.utils.find(lambda r:r.name.lower()==name.lower(), ctx.guild.roles)
        await self.selfrole_list.update({"guild_id": ctx.guild.id}, {"$pull": {"role_ids": role.id}})
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
    @checks.owner_only()
    async def deletemessage(self, ctx, msg_id:int):
        try:
            message = await ctx.get_message(msg_id)
            await message.delete()
            await ctx.confirm()
        except Exception as e:
            print(e)
            await ctx.deny()

    @commands.command()
    @checks.manager_only()
    async def welcome(self, ctx):
        await self.welcome_channel_list.update_one({"guild_id": ctx.guild.id}, {"$set": {"channel_id": ctx.channel.id}}, upsert=True)
        await ctx.confirm()

    @commands.command()
    @checks.manager_only()
    async def nowelcome(self, ctx):
        result = await self.welcome_channel_list.delete_one({"guild_id": ctx.guild.id})
        if result.delete_count > 0:
            await ctx.confirm()
        else:
            await ctx.confirm()

    async def on_member_join(self, member):
        channel_data = await self.welcome_channel_list.find_one({"guild_id": member.guild.id})
        channel = member.guild.get_channel(channel_data.get("channel_id"))
        if channel:
            await channel.send(f"*\"Eeeeehhhhhh, go away {member.mention}, I don't want any more work...\"*")
            if member.guild.id == config.OTOGI_GUILD_ID:
                await asyncio.sleep(5)
                otogi_guild = self.bot.get_guild(config.OTOGI_GUILD_ID)
                await member.send(f"Welcome to {otogi_guild.name}.\n"
                                  "Please read the rules in #server-rules before doing anything.\n"
                                  "You can use `>>help` to get a list of available commands.\n\n"
                                  "Have a nice day!")

    @commands.command()
    @checks.manager_only()
    async def purge(self, ctx, number:int=10, *members:discord.Member):
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
                before, after = await self.bot.wait_for("member_update", check=lambda b,a: a.id==member.id and a.guild.id==member.guild.id and "Muted" not in [r.name for r in a.roles], timeout=duration)
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

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(GuildBot(bot))
