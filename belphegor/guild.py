import discord
from discord.ext import commands
from .utils import checks, config
import asyncio

#==================================================================================================================================================

class GuildBot:
    '''
    Doing stuff related to server.
    '''

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.owner_only()
    async def block(self, ctx, member:discord.Member):
        await member.block()
        await ctx.send(f"{member.name} has been blocked.")

    @commands.command()
    @checks.owner_only()
    async def unblock(self, ctx, member:discord.Member):
        await member.unblock()
        await ctx.send(f"{member.name} has been unblocked.")

    @commands.command()
    @checks.manager_only()
    async def kick(self, ctx, member:discord.Member, *, reason=None):
        await member.kick(reason=reason)
        await ctx.send(f"{member.name} has been kicked.")
        await member.send(f"You have been kicked from {ctx.guild.name} by {ctx.author.name}.\nReason: {reason}\n"
                          "If you think this action is unjustified, please contact the mods.")

    @commands.command()
    @checks.manager_only()
    async def ban(self, ctx, member:discord.Member, *, reason=None):
        await member.ban(reason=reason)
        await ctx.send(f"{member.name} has been banned.")
        await member.send(f"You have been banned from {ctx.guild.name} by {ctx.author.name}.\nReason: {reason}\n"
                          "If you think this action is unjustified, please contact the mods to unlift the ban.")

    @commands.command()
    @checks.manager_only()
    async def unban(self, ctx, user:discord.User, *, reason=None):
        await user.unban(reason=reason)
        await ctx.send(f"{member.name} has been unbanned.")

    @commands.command()
    @checks.creampie_guild_only()
    async def creampie(self, ctx):
        '''
            Add role 18+ for accessing creampie channel, which is NSFW.
        '''
        member = ctx.author
        role = discord.utils.get(member.guild.roles, name="18+")
        try:
            if role is not None:
                await member.add_roles(role)
                await ctx.message.add_reaction("\u2705")
        except:
            await ctx.message.add_reaction("\u274c")

    @commands.command()
    @checks.creampie_guild_only()
    async def censored(self, ctx):
        '''
            Remove role 18+.
        '''
        member = ctx.author
        role = discord.utils.get(member.roles, name="18+")
        try:
            if role is not None:
                await member.remove_roles(role)
                await ctx.message.add_reaction("\u2705")
        except:
            await ctx.message.add_reaction("\u274c")

    @commands.group(invoke_without_command=True)
    async def selfrole(self, ctx, name):
        if ctx.invoked_subcommand is None:
            try:
                role = discord.utils.find(lambda r:name in r.name, ctx.guild.roles)
                with open(f"{config.data_path}mod/role/{ctx.guild.id}.txt", encoding="utf-8") as file:
                    roles = file.read().rstrip().splitlines()
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
                with open(f"{config.data_path}mod/role/{ctx.guild.id}.txt", encoding="utf-8") as file:
                    roles = file.read().splitlines()
            except:
                roles = []
            if role in roles:
                return
            else:
                roles.append(role.name)
            with open(f"{config.data_path}mod/role/{ctx.guild.id}.txt", "w+", encoding="utf-8") as file:
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
            with open(f"{config.data_path}mod/role/{ctx.guild.id}.txt", encoding="utf-8") as file:
                roles = file.read().splitlines()
            if role.name in roles:
                await role.delete()
                roles.remove(role.name)
            with open(f"{config.data_path}mod/role/{ctx.guild.id}.txt", "w+", encoding="utf-8") as file:
                file.write("\n".join(roles))
            await ctx.message.add_reaction("\u2705")
        except Exception as e:
            print(e)
            await ctx.message.add_reaction("\u274c")

    @selfrole.command()
    async def empty(self, ctx):
        try:
            with open(f"{config.data_path}mod/role/{ctx.guild.id}.txt", encoding="utf-8") as file:
                roles = file.read().splitlines()
            for r in ctx.author.roles:
                if r.name in roles:
                    await ctx.author.remove_roles(r)
                    break
            await ctx.message.add_reaction("\u2705")
        except Exception as e:
            print(e)
            await ctx.message.add_reaction("\u274c")

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

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(GuildBot(bot))
