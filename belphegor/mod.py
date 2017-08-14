import discord
from discord.ext import commands
from .utils import checks, config
import codecs
import asyncio

#==================================================================================================================================================

class ModBot:
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
        await member.send(f"You have been kicked from {ctx.message.guild.name} by {ctx.message.author.name}.\nReason: {reason}\n"
                          "If you think this action is unjustified, please contact the mods.")

    @commands.command()
    @checks.manager_only()
    async def ban(self, ctx, member:discord.Member, *, reason=None):
        await member.ban(reason=reason)
        await ctx.send(f"{member.name} has been banned.")
        await member.send(f"You have been banned from {ctx.message.guild.name} by {ctx.message.author.name}.\nReason: {reason}\n"
                          "If you think this action is unjustified, please contact the mods to unlift the ban.")

    @commands.command()
    @checks.manager_only()
    async def unban(self, ctx, member:discord.Member, *, reason=None):
        await member.unban(reason=reason)
        await ctx.send(f"{member.name} has been unbanned.")

    @commands.command()
    async def creampie(self, ctx):
        '''
            Add role 18+ for accessing creampie channel, which is NSFW.
        '''
        member = ctx.message.author
        role = discord.utils.get(member.guild.roles, name="18+")
        try:
            if role is not None:
                await member.add_roles(role)
                await ctx.message.add_reaction("\u2705")
        except:
            await ctx.message.add_reaction("\u274c")

    @commands.command()
    async def censored(self, ctx):
        '''
            Remove role 18+.
        '''
        member = ctx.message.author
        role = discord.utils.get(member.roles, name="18+")
        try:
            if role is not None:
                await member.remove_roles(role)
                await ctx.message.add_reaction("\u2705")
        except:
            await ctx.message.add_reaction("\u274c")

    @commands.group(invoke_without_command=True)
    async def rolecolor(self, ctx, name):
        if ctx.invoked_subcommand is None:
            try:
                role = discord.utils.find(lambda r:name in r.name, ctx.message.guild.roles)
                with codecs.open(f"{config.data_path}mod/role/{ctx.message.guild.id}.txt", encoding="utf-8") as file:
                    roles = file.read().rstrip().splitlines()
                if role.name in roles:
                    for r in ctx.message.author.roles:
                        if r.name in roles:
                            await ctx.message.author.remove_roles(r)
                            break
                    await ctx.message.author.add_roles(role)
                    await ctx.message.add_reaction("\u2705")
                else:
                    raise
            except Exception as e:
                print(e)
                await ctx.message.add_reaction("\u274c")

    @rolecolor.command()
    @checks.role_manager_only()
    async def create(self, ctx, colorhex, *, name=""):
        try:
            if not name:
                name = f"#{colorhex.upper()}"
            role = discord.utils.find(lambda r:r.name==name, ctx.message.guild.roles)
            if role is None:
                role = await ctx.message.guild.create_role(name=name, colour=discord.Colour(int(f"0x{colorhex}", 16)))
            else:
                raise
            try:
                with codecs.open(f"{config.data_path}mod/role/{ctx.message.guild.id}.txt", encoding="utf-8") as file:
                    roles = file.read().splitlines()
                if role in roles:
                    return
                else:
                    roles.append(role.name)
            except:
                roles = [role.name,]
            with codecs.open(f"{config.data_path}mod/role/{ctx.message.guild.id}.txt", "w+", encoding="utf-8") as file:
                file.write("\n".join(roles))
            await asyncio.sleep(0.5)
            await role.edit(position=ctx.me.top_role.position-1)
            await ctx.message.add_reaction("\u2705")
        except Exception as e:
            print(e)
            await ctx.message.add_reaction("\u274c")

    @rolecolor.command()
    @checks.role_manager_only()
    async def remove(self, ctx, name):
        try:
            role = discord.utils.find(lambda r:name in r.name, ctx.message.guild.roles)
            with codecs.open(f"{config.data_path}mod/role/{ctx.message.guild.id}.txt", encoding="utf-8") as file:
                roles = file.read().splitlines()
            if role.name in roles:
                await role.delete()
                roles.remove(role.name)
            with codecs.open(f"{config.data_path}mod/role/{ctx.message.guild.id}.txt", "w+", encoding="utf-8") as file:
                file.write("\n".join(roles))
            await ctx.message.add_reaction("\u2705")
        except Exception as e:
            print(e)
            await ctx.message.add_reaction("\u274c")

    @rolecolor.command()
    async def empty(self, ctx):
        try:
            with codecs.open(f"{config.data_path}mod/role/{ctx.message.guild.id}.txt", encoding="utf-8") as file:
                roles = file.read().splitlines()
            for r in ctx.message.author.roles:
                if r.name in roles:
                    await ctx.message.author.remove_roles(r)
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
    bot.add_cog(ModBot(bot))
