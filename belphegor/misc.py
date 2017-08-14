import discord
from discord.ext import commands
import random
import time
from .board_game import dices
from .utils import config, checks, request
import psutil
import os
import codecs
import json

#==================================================================================================================================================

class MiscBot:
    def __init__(self, bot):
        self.bot = bot
        self.add_quote()

    def add_quote(self):
        self.w_quote =          ["I won! Yay!",
                                 "Hehehe, I'm good at this.",
                                 "Lalala~"]
        self.d_quote =          ["It's a tie.",
                                 "It's a draw.",
                                 "Again!"]
        self.l_quote =          ["I-I lost...",
                                 "I won't lose next time!",
                                 "Why?"]
        self.wstreak_quote =    ["I'm invincible!",
                                 "I'm on a roll!",
                                 "Triple kill! Penta kill!!!",
                                 "(smug)"]
        self.dstreak_quote =    ["This kinda... \\*put on shades\\* draws out for too long.",
                                 "Tie again... How many tie in a row did we have?",
                                 "(staaaareeee~)"]
        self.lstreak_quote =    ["E-eh? Did you cheat or something?",
                                 "Mwuu... this is frustrating...",
                                 "Eeeeeek! EEEEEEEKKKKKKK!",
                                 "(attemp to logout to reset the game)"]

    def quote(self, streak):
        if streak.endswith("ddd"):
            return random.choice(self.dstreak_quote + self.d_quote)
        elif streak.count("w") > 2:
            if streak[-1] == "w":
                return random.choice(self.w_quote + self.wstreak_quote)
            else:
                return random.choice(self.d_quote)
        elif 0 < streak.count("w") <= 2:
            if streak[-1] == "w":
                return random.choice(self.w_quote)
            else:
                return random.choice(self.d_quote)
        elif streak.count("l") > 2:
            if streak[-1] == "l":
                return random.choice(self.l_quote + self.lstreak_quote)
            else:
                return random.choice(self.d_quote)
        elif 0 < streak.count("l") <= 2:
            if streak[-1] == "l":
                return random.choice(self.l_quote)
            else:
                return random.choice(self.d_quote)
        else:
                return random.choice(self.d_quote)

    @commands.command(aliases=["jkp",])
    async def jankenpon(self, ctx):
        message = await ctx.send(embed=discord.Embed(description="What will you use? Rock, paper or scissor?"))
        e_value = {"\u270a": 1, "\u270b": 2, "\u270c": 3, "\u274c": 0}
        e_emoji = ("\u274c", "\u270a", "\u270b", "\u270c")
        for e in e_value:
            await message.add_reaction(e)
        try:
            with codecs.open(f"{config.data_path}misc/jankenpon/{ctx.message.author.id}.txt", encoding="utf-8") as file:
                win = [int(i) for i in file.read().split()]
        except:
            win = [0, 0, 0]
        streak = ""
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=lambda r,u:u.id==ctx.message.author.id and r.emoji in e_value and r.message.id==message.id, timeout=10)
            except:
                await message.clear_reactions()
                await message.edit(embed=discord.Embed(description="\"I'm tir..e...d.....zzzz...........\""))
                break
            roll = random.randint(1,3)
            value = e_value[reaction.emoji]
            if value == 0:
                await message.clear_reactions()
                await message.edit(embed=discord.Embed(description="\"No more jankenpon? Yay!!!\""))
                break
            else:
                await message.remove_reaction(reaction, user)
                if (value - roll) % 3 == 0:
                    win[1] += 1
                    streak += "d"
                elif (value - roll) % 3 == 2:
                    win[2] += 1
                    if "w" in streak:
                        streak += "w"
                    else:
                        streak = "w"
                else:
                    win[0] += 1
                    if "l" in streak:
                        streak += "l"
                    else:
                        streak = "l"
                embed = discord.Embed()
                embed.add_field(name=f"I use {e_emoji[roll]}", value=f"*\"{self.quote(streak)}\"*")
                embed.set_footer(text=f"{win[0]}W - {win[1]}D - {win[2]}L")
                await message.edit(embed=embed)
        with codecs.open(f"{config.data_path}misc/jankenpon/{ctx.message.author.id}.txt", "w+", encoding="utf-8") as file:
            file.write(f"{win[0]} {win[1]} {win[2]}")

    async def on_message(self, message):
        if message.author.bot:
            return
        inp = message.content
        if inp[:3] in ("/o/", "\\o\\"):
            reply = ""
            for index, ch in enumerate(inp):
                current = inp[index:index+3]
                if current == "\\o\\":
                    reply = f"{reply} /o/"
                elif current == "/o/":
                    reply = f"{reply} \\o\\"
                else:
                    pass
            await message.channel.send(reply)
        elif inp == "ping":
            msg = await message.channel.send("pong")
            timedelta = msg.created_at - message.created_at
            await msg.edit(content=f"pong ({int(timedelta.total_seconds()*1000)}ms)")

    @commands.command()
    async def avatar(self, ctx, member:discord.Member=None):
        try:
            embed = discord.Embed(title=f"{member.display_name}'s avatar", url=member.avatar_url)
            embed.set_image(url=member.avatar_url)
            await ctx.send(embed=embed)
        except:
            embed = discord.Embed(title=f"{ctx.message.author.display_name}'s avatar", url=ctx.message.author.avatar_url)
            embed.set_image(url=ctx.message.author.avatar_url)
            await ctx.send(embed=embed)

    @commands.command()
    async def dice(self, ctx, max_side:int, number_of_dices:int = 2):
        if 120 >= max_side > 3 and 0 < number_of_dices <= 100:
            RNG = dices.Dices(max_side, number_of_dices)
            await ctx.send("```\nRoll result:\n{}\n\nDistribution:\n{}\n```"
                               .format(", ".join([str(r) for r in RNG.rolls]), "\n".join(["{} showed up {} times.".format(i, RNG.rolls.count(i)) for i in range(1, max_side+1)])))
        else:
            await ctx.send("Max side must be between 4 and 120 and number of dices must be between 1 and 100")

    @commands.command()
    async def stats(self, ctx):
        embed = discord.Embed(colour=discord.Colour.blue())
        embed.set_author(name="{}".format(self.bot.user), icon_url=self.bot.user.avatar_url)
        owner = self.bot.get_user(config.owner_id)
        embed.add_field(name="Owner", value="{}".format(owner))
        embed.add_field(name="Library", value="discord.py[rewrite]")
        embed.add_field(name="Created at", value=str(self.bot.user.created_at)[:10])
        process = psutil.Process(os.getpid())
        embed.add_field(name="Servers", value="{} servers".format(len(self.bot.guilds)))
        embed.add_field(name="Memory usage", value="{:.2f} MBs".format(process.memory_info().rss/1024/1024))
        with open(f"{config.data_path}misc/start_time.txt") as file:
            start_time = float(file.read())
        uptime = int(time.time() - start_time)
        d = uptime // 86400
        h = (uptime % 86400) // 3600
        m = ((uptime % 86400) % 3600) // 60
        s = ((uptime % 86400) % 3600) % 60
        embed.add_field(name="Uptime", value="{}d {}h{}m{}s".format(d, h, m, s))
        embed.set_footer(text=time.strftime("%a, %Y-%m-%d at %I:%M:%S %p, GMT%z", time.localtime()))
        await ctx.send(embed=embed)

    @commands.command()
    @checks.manager_only()
    async def welcome(self, ctx):
        with codecs.open(f"{config.data_path}misc/welcome/{ctx.message.guild.id}.txt", "w+", encoding="utf-8") as file:
            file.write(str(ctx.message.channel.id))
        await ctx.send("Got it.")

    async def on_member_join(self, member):
        try:
            with codecs.open(f"{config.data_path}misc/welcome/{member.guild.id}.txt", encoding="utf-8") as file:
                channel_id = int(file.read().rstrip())
            channel = member.guild.get_channel(channel_id)
            await channel.send("Eeeeehhhhhh, go away {}, I don't want any more work...".format(member.display_name))
        except:
            pass

    @commands.command()
    async def fancy(self, ctx, *, textin:str):
        textout = ""
        textin = textin.upper()
        for charin in textin:
            try:
                charout = config.emojis[charin]
            except:
                charout = charin
            textout += charout + " "
        await ctx.send(textout)

    @commands.command(aliases=["hello",])
    async def hi(self, ctx):
        await ctx.send("*\"Go away...\"*")


#==================================================================================================================================================

def setup(bot):
    bot.add_cog(MiscBot(bot))
