import discord
from discord.ext import commands
from .utils import checks, config, format
import asyncio
import json
import unicodedata

#==================================================================================================================================================

class GuildBot:
    '''
    Doing stuff related to server.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.welcome_channels = {}
        with open(f"{config.data_path}/misc/welcome.json", encoding="utf-8") as file:
            jsonable = json.load(file)
        for key, value in jsonable.items():
            self.welcome_channels[int(key)] = self.bot.get_channel(value)

        self.banned_emojis = []

    @commands.command()
    @checks.manager_only()
    async def kick(self, ctx, member:discord.Member, *, reason=None):
        await member.kick(reason=reason)
        await ctx.send(f"{member.name} has been kicked.")
        await member.send(f"You have been kicked from {ctx.guild.name} by {ctx.author.name}.\nReason: {reason}\n\n"
                          "If you think this action is unjustified, please contact the mods.")

    @commands.command()
    @checks.manager_only()
    async def ban(self, ctx, member:discord.Member, *, reason=None):
        await member.ban(reason=reason)
        await ctx.send(f"{member.name} has been banned.")
        await member.send(f"You have been banned from {ctx.guild.name} by {ctx.author.name}.\nReason: {reason}\n\n"
                          "If you think this action is unjustified, please contact the mods to unlift the ban.")

    @commands.command()
    @checks.manager_only()
    async def unban(self, ctx, user:discord.User, *, reason=None):
        await user.unban(reason=reason)
        await ctx.send(f"{user.name} has been unbanned.")

    @commands.command()
    @checks.creampie_guild_only()
    async def creampie(self, ctx):
        '''
            Add role 18+ for accessing creampie channel, which is NSFW.
        '''
        member = ctx.author
        role = discord.utils.get(member.guild.roles, name="18+")
        if role is not None:
            await member.add_roles(role)
            await ctx.message.add_reaction("\u2705")
        else:
            await ctx.message.add_reaction("\u274c")

    @commands.command()
    @checks.creampie_guild_only()
    async def censored(self, ctx):
        '''
            Remove role 18+.
        '''
        member = ctx.author
        role = discord.utils.get(member.roles, name="18+")
        if role is not None:
            await member.remove_roles(role)
            await ctx.message.add_reaction("\u2705")
        else:
            await ctx.message.add_reaction("\u274c")

    @commands.group(invoke_without_command=True)
    async def selfrole(self, ctx, name):
        if ctx.invoked_subcommand is None:
            try:
                role = discord.utils.find(lambda r:name in r.name, ctx.guild.roles)
                with open(f"{config.data_path}/mod/role/{ctx.guild.id}.txt", encoding="utf-8") as file:
                    roles = file.read().strip().splitlines()
                if role.name in roles:
                    for r in ctx.author.roles:
                        if r.name in roles:
                            await ctx.author.remove_roles(r)
                            break
                    await ctx.author.add_roles(role)
                    await ctx.message.add_reaction("\u2705")
                else:
                    raise
            except Exception as e:
                print(e)
                await ctx.message.add_reaction("\u274c")

    @selfrole.command()
    @checks.role_manager_only()
    async def add(self, ctx, *, name):
        try:
            role = discord.utils.find(lambda r:r.name.lower()==name.lower(), ctx.guild.roles)
            try:
                with open(f"{config.data_path}/mod/role/{ctx.guild.id}.txt", encoding="utf-8") as file:
                    roles = file.read().splitlines()
            except:
                roles = []
            if role in roles:
                return
            else:
                roles.append(role.name)
            with open(f"{config.data_path}/mod/role/{ctx.guild.id}.txt", "w+", encoding="utf-8") as file:
                file.write("\n".join(roles))
            await ctx.message.add_reaction("\u2705")
        except Exception as e:
            print(e)
            await ctx.message.add_reaction("\u274c")

    @selfrole.command()
    @checks.role_manager_only()
    async def remove(self, ctx, *, name):
        try:
            role = discord.utils.find(lambda r:name.lower()==r.name.lower(), ctx.guild.roles)
            with open(f"{config.data_path}/mod/role/{ctx.guild.id}.txt", encoding="utf-8") as file:
                roles = file.read().splitlines()
            if role.name in roles:
                roles.remove(role.name)
            with open(f"{config.data_path}/mod/role/{ctx.guild.id}.txt", "w+", encoding="utf-8") as file:
                file.write("\n".join(roles))
            await ctx.message.add_reaction("\u2705")
        except Exception as e:
            print(e)
            await ctx.message.add_reaction("\u274c")

    @selfrole.command()
    async def empty(self, ctx):
        try:
            with open(f"{config.data_path}/mod/role/{ctx.guild.id}.txt", encoding="utf-8") as file:
                roles = file.read().splitlines()
            for r in ctx.author.roles:
                if r.name in roles:
                    await ctx.author.remove_roles(r)
                    break
            await ctx.message.add_reaction("\u2705")
        except Exception as e:
            print(e)
            await ctx.message.add_reaction("\u274c")

    @selfrole.command(name="list")
    async def role_list(self, ctx):
        with open(f"{config.data_path}/mod/role/{ctx.guild.id}.txt", encoding="utf-8") as file:
            roles = file.read().strip()
        await ctx.send(f"```\n{roles}\n```")

    @commands.command()
    @checks.owner_only()
    async def deletemessage(self, ctx, msg_id:int):
        try:
            message = await ctx.get_message(msg_id)
            await message.delete()
            await ctx.message.add_reaction("\u2705")
        except Exception as e:
            print(e)
            await ctx.message.add_reaction("\u274c")

    @commands.command()
    @checks.manager_only()
    async def welcome(self, ctx):
        self.welcome_channels[ctx.guild.id] = ctx.channel
        jsonable = {key: value.id for key, value in self.welcome_channels.items()}
        with open(f"{config.data_path}/misc/welcome.json", "w+", encoding="utf-8") as file:
            json.dump(jsonable, file, indent=4, ensure_ascii=False)
        await ctx.message.add_reaction("\u2705")

    async def on_member_join(self, member):
        channel = self.welcome_channels[member.guild.id]
        await channel.send(f"*\"Eeeeehhhhhh, go away {member.mention}, I don't want any more work...\"*")
        await asyncio.sleep(5)
        if member.guild.id == config.otogi_guild_id:
            otogi_guild = self.bot.get_guild(config.otogi_guild_id)
            await member.send(f"Welcome to {otogi_guild.name}.\n"
                              "Please read the rules in #server-rules before doing anything.")

    @commands.command()
    @checks.manager_only()
    async def purge(self, ctx, number:int=10, *members:discord.Member):
        if number > 0:
            if members:
                await ctx.channel.purge(limit=number, check=lambda m:m.author in members)
            else:
                await ctx.channel.purge(limit=number)
            await ctx.message.add_reaction("\u2705")

    @commands.command()
    @checks.manager_only()
    async def purgereact(self, ctx, *msg_ids):
        for msg_id in msg_ids:
            msg = await ctx.get_message(msg_id)
            await msg.clear_reactions()
            await ctx.message.add_reaction("\u2705")

    @commands.command()
    @checks.manager_only()
    async def mute(self, ctx, member:discord.Member, *, reason):
        muted_role = discord.utils.find(lambda r:r.name=="Muted", ctx.guild.roles)
        await member.add_roles(muted_role)
        duration = format.extract_time(reason)
        if duration > 0:
            if duration > 86400:
                return await ctx.send("Time too large.")
            await ctx.send(f"{member.mention} has been muted for {format.seconds_to_text(duration)}.")
            try:
                before, after = await self.bot.wait_for("member_update", check=lambda b,a:a.id==member.id and a.guild.id==member.guild.id and
                                                        "Muted" not in [r.name for r in a.roles], timeout=duration)
            except asyncio.TimeoutError:
                await member.remove_roles(muted_role)
                await ctx.send(f"{member.mention} has been unmute.")
        else:
            await ctx.send(f"{member.mention} has been muted.")

    @commands.command()
    @checks.manager_only()
    async def unmute(self, ctx, member:discord.Member):
        muted_role = discord.utils.find(lambda r:r.name=="Muted", ctx.guild.roles)
        await member.remove_roles(muted_role)
        await ctx.send(f"{member.mention} has been unmute.")

    async def on_reaction_add(self, reaction, user):
        if user.guild.id == config.otogi_guild_id:
            try:
                char = reaction.emoji.id
            except:
                char = reaction.emoji
            if char in self.banned_emojis:
                await reaction.message.clear_reactions()

    @commands.command()
    @checks.otogi_guild_only()
    @checks.manager_only()
    async def reactban(self, ctx, *, emoji):
        try:
            e_id = int(emoji)
            self.banned_emojis.append(e_id)
            await ctx.message.add_reaction("\u2705")
        except:
            self.banned_emojis.append(emoji)
            await ctx.message.add_reaction("\u2705")

    @commands.command()
    async def getreact(self, ctx, msg_id:int):
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
