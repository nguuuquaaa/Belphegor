import discord
from discord.ext import commands
from . import utils, board_game
from .utils import config, checks, modding
import random
import asyncio
import unicodedata
import re
from pymongo import ReturnDocument
import json
from io import BytesIO
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import traceback
import collections
import time
import copy
import numpy as np
import aiohttp
import scipy.ndimage
import colorsys

#==================================================================================================================================================

FANCY_CHARS = {
    "A": "\U0001F1E6", "B": "\U0001F1E7", "C": "\U0001F1E8", "D": "\U0001F1E9", "E": "\U0001F1EA",
    "F": "\U0001F1EB", "G": "\U0001F1EC", "H": "\U0001F1ED", "I": "\U0001F1EE", "J": "\U0001F1EF",
    "K": "\U0001F1F0", "L": "\U0001F1F1", "M": "\U0001F1F2", "N": "\U0001F1F3", "O": "\U0001F1F4",
    "P": "\U0001F1F5", "Q": "\U0001F1F6", "R": "\U0001F1F7", "S": "\U0001F1F8", "T": "\U0001F1F9",
    "U": "\U0001F1FA", "V": "\U0001F1FB", "W": "\U0001F1FC", "X": "\U0001F1FD", "Y": "\U0001F1FE",
    "Z": "\U0001F1FF", "!": "\u2757", "?": "\u2753",
    "0": "\u0030\u20E3", "1": "\u0031\u20E3", "2": "\u0032\u20E3", "3": "\u0033\u20E3", "4": "\u0034\u20E3",
    "5": "\u0035\u20E3", "6": "\u0036\u20E3", "7": "\u0037\u20E3", "8": "\u0038\u20E3", "9": "\u0039\u20E3"
}

GLITCH_TEXT = "¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķĸĹĺĻļĽľĿŀŁłŃńŅņŇňŉŊŋŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŦŧŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽž                    "

GLITCH_UP = tuple("̍	̎	̄	̅	̿	̑	̆	̐	͒	͗͑	̇	̈	̊	͂	̓	̈́	͊	͋	͌̃	̂	̌	͐	̀	́	̋	̏	̒	̓̔	̽	̉	ͣ	ͤ	ͥ	ͦ	ͧ	ͨ	ͩͪ	ͫ	ͬ	ͭ	ͮ	ͯ	̾	͛	͆	̚".split())

GLITCH_MIDDLE = tuple("̕	̛	̀	́	͘	̡	̢	̧	̨	̴̵	̶	͏	͜	͝	͞	͟	͠	͢	̸̷	͡	҉".split())

GLITCH_DOWN = tuple("̖	̗	̘	̙	̜	̝	̞	̟	̠	̤̥	̦	̩	̪	̫	̬	̭	̮	̯	̰̱	̲	̳	̹	̺	̻	̼	ͅ	͇	͈͉	͍	͎	͓	͔	͕	͖	͙	͚	̣".split())

GLITCH_ALL = tuple(i for j in (GLITCH_UP, GLITCH_MIDDLE, GLITCH_DOWN) for i in j)

QUOTES = {
    "win": [
        "I won! Yay!",
        "Hehehe, I'm good at this.",
        "Lalala~"
    ],
    "draw": [
        "It's a tie.",
        "It's a draw.",
        "Again!"
    ],
    "lose": [
        "I-I lost...",
        "I won't lose next time!",
        "Why?"
    ],
    "winstreak": [
        "I'm invincible!",
        "I'm on a roll!",
        "Triple kill! Penta kill!!!",
        "(smug)"
    ],
    "drawstreak": [
        "This kinda... draws out for too long.",
        "Tie again... How many tie in a row did we have?",
        "(staaaareeee~)"
    ],
    "losestreak": [
        "E-eh? Did you cheat or something?",
        "Mwuu... this is frustrating...",
        "Eeeeeek! EEEEEEEKKKKKKK!",
        "(attemp to logout to reset the game)"
    ]
}
ASCII = "@%#*+=-:. "
RANGE = 256 / len(ASCII)
CHAR_SIZE = (8, 16)

DOT_PATTERN = (1, 4, 2, 5, 3, 6, 7, 8)
BOX_PATTERN = {
    (0, 0): " ",
    (0, 1): "\u2584",
    (1, 0): "\u2580",
    (1, 1): "\u2588"
}

def lstrip_generator(generator):
    check = True
    for item in generator:
        if check:
            if not item:
                continue
            else:
                yield item
                check = False
        else:
            yield item

def generate_blank_char():
    while True:
        yield "\u2002"
        yield "\u2003"

blank_chars = generate_blank_char()
MOON_PATTERN = {
    (0, 0): "\U0001f311",
    (0, 1): "\U0001f312",
    (0, 2): "\U0001f313",
    (1, 0): "\U0001f318",
    (1, 1): "\U0001f315",
    (1, 2): "\U0001f314",
    (2, 0): "\U0001f317",
    (2, 1): "\U0001f316",
    (2, 2): "\U0001f315"
}

def strip_url(url):
    return url.lstrip("<").rstrip(">")

#==================================================================================================================================================

class CharImage:
    def __init__(self, char, *, font, weight=None, pos=(0, 0)):
        image = Image.new("L", CHAR_SIZE, 0)
        draw = ImageDraw.Draw(image)
        draw.text(pos, char, font=font, fill=255)
        self.weight = weight or 1
        self.raw = np.where(np.array(image)>127, 1, 0)
        self.sum_raw = np.sum(self.raw)

    def compare(self, other, inverse_weight):
        rating = 0
        inverse_rating = 0
        rating = np.sum(self.raw * other)
        inverse_rating = self.sum_raw - rating
        rating = (rating - inverse_weight * inverse_rating) * self.weight
        return rating

#==================================================================================================================================================

class Misc(commands.Cog):
    '''
    Stuff that makes no difference if they aren't there.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.jankenpon_record = bot.db.jankenpon_record
        self.guild_data = bot.db.guild_data
        self.owo = {"/o/": "\\o\\", "\\o\\": "/o/", "\\o/": "/o\\", "/o\\": "\\o/"}
        self.setup_ascii_chars()
        self.auto_rep_disabled = set()
        bot.loop.create_task(self.fetch_auto_rep_settings())

    def quote(self, streak):
        if streak.endswith("ddd"):
            return random.choice(QUOTES["drawstreak"] + QUOTES["draw"])
        elif streak.count("w") > 2:
            if streak[-1] == "w":
                return random.choice(QUOTES["winstreak"] + QUOTES["win"])
        elif 0 < streak.count("w") <= 2:
            if streak[-1] == "w":
                return random.choice(QUOTES["win"])
        elif streak.count("l") > 2:
            if streak[-1] == "l":
                return random.choice(QUOTES["losestreak"] + QUOTES["lose"])
        elif 0 < streak.count("l") <= 2:
            if streak[-1] == "l":
                return random.choice(QUOTES["lose"])
        return random.choice(QUOTES["draw"])

    @modding.help(brief="Play rock-paper-scissor", category="Misc", field="Commands", paragraph=0)
    @commands.command(aliases=["jkp",])
    async def jankenpon(self, ctx):
        '''
            `>>jankenpon`
            Play rock-paper-scissor.
        '''
        embed = discord.Embed(description="What will you use? Rock, paper or scissor?")
        message = await ctx.send(embed=embed)
        possible_reactions = ("\u270a", "\u270b", "\u270c", "\u274c")
        for e in possible_reactions:
            await message.add_reaction(e)
        record = await self.jankenpon_record.find_one_and_update(
            {"id": ctx.author.id},
            {"$setOnInsert": {"id": ctx.author.id, "win": 0, "draw": 0, "lose": 0}},
            return_document=ReturnDocument.AFTER,
            upsert=True
        )
        streak = ""
        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    check=lambda r,u: u.id==ctx.author.id and r.emoji in possible_reactions and r.message.id==message.id,
                    timeout=30
                )
            except asyncio.TimeoutError:
                embed.description = "\"I'm tir..e...d.....zzzz...........\""
                try:
                    await message.clear_reactions()
                except:
                    pass
                await message.edit(embed=embed)
                break
            roll = random.randint(0,2)
            value = possible_reactions.index(reaction.emoji)
            if value == 3:
                embed.title = ""
                embed.description = "\"No more jankenpon? Yay!!!\""
                try:
                    await message.clear_reactions()
                except:
                    pass
                await message.edit(embed=embed)
                break
            else:
                try:
                    await message.remove_reaction(reaction, user)
                except:
                    pass
                if (value - roll) % 3 == 0:
                    record["draw"] += 1
                    streak = f"{streak}d"
                elif (value - roll) % 3 == 2:
                    record["lose"] += 1
                    if "w" in streak:
                        streak = f"{streak}w"
                    else:
                        streak = "w"
                else:
                    record["win"] += 1
                    if "l" in streak:
                        streak = f"{streak}l"
                    else:
                        streak = "l"
                embed.title = f"I use {possible_reactions[roll]}"
                embed.description = f"*\"{self.quote(streak)}\"*"
                embed.set_footer(text=f"{record['win']}W - {record['draw']}D - {record['lose']}L")
                await message.edit(embed=embed)
        await self.jankenpon_record.update_one(
            {"id": ctx.author.id},
            {"$set": {"win": record["win"], "draw": record["draw"], "lose": record["lose"]}}
        )

    async def ping(self, target):
        try:
            start = time.perf_counter()
            await target.trigger_typing()
            end = time.perf_counter()
            await target.send(content=f"pong (ws: {int(1000*self.bot.latency)}ms, typing: {int(1000*(end-start))}ms)")
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            pass
        elif message.guild.id in self.auto_rep_disabled:
            return
        inp = message.content
        if inp == "ping":
            await self.ping(message.channel)
        elif inp[:3] in self.owo:
            r = []
            index = 0
            l = len(inp)
            while index < l:
                current = inp[index:index+3]
                if current in self.owo:
                    r.append(self.owo[current])
                    index += 3
                else:
                    index += 1
            try:
                await message.channel.send(" ".join(r))
            except:
                pass

    @modding.help(brief="Get your or a user avatar", category="Misc", field="Commands", paragraph=1)
    @commands.command(aliases=["av"])
    async def avatar(self, ctx, *, member: discord.Member=None):
        '''
            `>>avatar <optional: member>`
            Show <member>'s avatar.
            If <member> is not specified, show your avatar instead.
        '''
        member = member or ctx.author
        embed = discord.Embed(title=f"{member.display_name}'s avatar", url=member.avatar_url)
        embed.set_image(url=member.avatar_url_as(static_format="png"))
        await ctx.send(embed=embed)

    @modding.help(brief="Roll dices", category="Misc", field="Commands", paragraph=0)
    @commands.command()
    async def dice(self, ctx, dice_type):
        '''
            `>>dice ndM`
            Roll dices, with max side M and number of dices n.
            Max side must be between 4 and 120 and number of dices must be between 1 and 100.
        '''
        d = dice_type.partition("d")
        try:
            max_side = int(d[2])
            number_of_dices = int(d[0])
        except:
            return await ctx.send("Must be in ndM format.")
        if 120 >= max_side > 3 and 0 < number_of_dices <= 100:
            rng = board_game.Dices(max_side, number_of_dices)
            roll_result = rng.roll()
            counter = collections.Counter(roll_result)
            await ctx.send(
                "```\nRoll result:\n{}\n\nDistribution:\nValue│Count\n─────┼─────\n{}\n```"
                .format(", ".join((str(r) for r in roll_result)), "\n".join((f"{i: 4d} │{counter[i]: 4d}" for i in range(1, max_side+1))))
            )
        else:
            await ctx.send("Max side must be between 4 and 120 and number of dices must be between 1 and 100.")

    @modding.help(brief="\U0001f1eb \U0001f1e6 \U0001f1f3 \U0001f1e8 \U0001f1fe", category="Misc", field="Commands", paragraph=0)
    @commands.command()
    async def fancy(self, ctx, *, textin):
        '''
            `>>fancy <text goes here>`
            Emojified text.
        '''
        textin = textin.upper()
        await ctx.send(" ".join((FANCY_CHARS.get(charin, charin) for charin in textin)))

    @commands.command(aliases=["hello",])
    async def hi(self, ctx):
        '''
            `>>hi`
            No.
        '''
        await ctx.send("Go away.")

    @modding.help(brief="Echo text", category=None, field="Other", paragraph=0)
    @commands.group(invoke_without_command=True)
    async def say(self, ctx, *, something: commands.clean_content):
        '''
            `>>say <text goes here>`
            Echo text.
            Also to test send message permissions.
        '''
        await ctx.send(something)

    @say.command(name="hi", aliases=["hello",])
    async def say_hi(self, ctx):
        '''
            `>>say hi`
            Go away.
        '''
        await ctx.send("No.")

    @say.command(name="welcome")
    async def say_welcome(self, ctx):
        '''
            `>>say welcome`
            Leave me alone.
        '''
        await ctx.send("Welcome to Leave Me Alone village. The exit is right there.")

    @modding.help(brief="Get unicode character info", category="Misc", field="Commands", paragraph=2)
    @commands.command()
    async def char(self, ctx, *, characters):
        '''
            `>>char <characters>`
            Check unicode codepoint and name of characters.
        '''
        characters = "".join(characters.split())
        if len(characters) > 20:
            await ctx.send("Too many characters.")
        else:
            def codepoint_generator(characters):
                for c in characters:
                    o = ord(c)
                    s = f"\\U{o:08x}" if o > 0xffff else f"\\u{o:04x}"
                    yield f"`{s}` - `{c}` - {unicodedata.name(c, 'No name found.')}"
            await ctx.send("\n".join(codepoint_generator(characters)))

    @modding.help(brief="Make a poll", category="Misc", field="Commands", paragraph=0)
    @commands.command()
    async def poll(self, ctx, *, data):
        '''
            `>>poll <question and choices>`
            Make a quick poll.
            Question and choices are separated by newline.
            The default (and shortest) duration is 60 seconds. You can specify more in question, i.e. `in 60 minutes`.
        '''
        stuff = data.strip().splitlines()
        question, duration = utils.extract_time(stuff[0])
        duration = duration.total_seconds()
        if duration < 60:
            duration = 60
        elif duration > 3600:
            return await ctx.send("Duration too long.")
        items = stuff[1:10]
        if not items:
            return await ctx.send("You must specify choices.")
        int_to_emoji = {}
        emoji_to_int = {}
        for i in range(len(items)):
            e = FANCY_CHARS[str(i+1)]
            int_to_emoji[i+1] = e
            emoji_to_int[e] = i+1
        embed = discord.Embed(title=f"Polling: {question}", description="\n".join((f"{int_to_emoji[i+1]} {s}" for i, s in enumerate(items))), colour=discord.Colour.dark_green())
        embed.set_footer(text=f"Poll will close in {utils.seconds_to_text(duration)}.")
        message = await ctx.send(embed=embed)
        for i in range(len(items)):
            self.bot.loop.create_task(message.add_reaction(int_to_emoji[i+1]))
        await asyncio.sleep(duration)
        message = await ctx.get_message(message.id)
        result = {}
        for r in message.reactions:
            if r.emoji in emoji_to_int.keys():
                result[r.emoji] = r.count
        embed.set_footer(text="Poll ended.")
        await message.edit(embed=embed)
        try:
            await message.clear_reactions()
        except:
            pass
        max_result = []
        max_number = max(result.values())
        for key, value in result.items():
            if value == max_number:
                max_result.append(items[emoji_to_int[key]-1])
        await ctx.send(f"Poll ended.\nHighest vote: {' and '.join(max_result)} with {max_number} votes.")

    @modding.help(brief="Z̜͍̊ă̤̥ḷ̐́ģͮ͛ò̡͞ ͥ̉͞ť͔͢e̸̷̅x̠ͯͧt̰̱̾", category="Misc", field="Commands", paragraph=1)
    @commands.group(invoke_without_command=True)
    async def glitch(self, ctx, *, data: modding.KeyValue(escape=False, clean=False)):
        '''
            `>>glitch <optional: weight> <text>`
            Generate Zalgo text.
            More weight, more weird.
            Default weight is 20.
        '''
        text = data.getall("", [])
        weight = data.getone("weight", None)
        try:
            weight = int(weight)
        except:
            weight = 20
        if 0 < weight <= 50:
            if text:
                await ctx.send("".join(("".join((c, "".join((random.choice(GLITCH_ALL) for i in range(weight))))) for c in "\n".join(text))))
            else:
                await ctx.send("No input text given.")
        else:
            await ctx.send("Weight value can only be between 1 and 50.")

    @modding.help(brief="ĜþŞ¶ōÙđĔł ĝĖĘ Ùľ© ¼Ħâ Ŗėēů®³ĸ¤²", category="Misc", field="Commands", paragraph=1)
    @glitch.command(aliases=["m"])
    async def meaningless(self, ctx, length: int=0):
        '''
            `>>glitch meaningless <optional: length>`
            Generate meaningless text. ~~Monika is that you~~
            Default length is a random number between 20 and 50.
        '''
        if 0 <= length <= 500:
            if length == 0:
                length = random.randrange(20, 50)
            try:
                await ctx.message.delete()
            except:
                pass
            text_body = "".join((random.choice(GLITCH_TEXT) for i in range(length)))
            await ctx.send("\n".join((text_body[i:i+50] for i in range(0, len(text_body), 50))))
        else:
            await ctx.send("Wha hold your horse with the length.")

    def get_rgb(self, rgb):
        rg, b = divmod(rgb, 256)
        r, g = divmod(rg, 256)
        if r < 0 or r > 255:
            raise checks.CustomError("RGB value out of range.")
        else:
            return r, g, b

    def rgb_to_cmyk(self, r, g, b, *, scale=100):
        if (r == 0) and (g == 0) and (b == 0):
            return 0, 0, 0, scale

        c = 1 - r / 255
        m = 1 - g / 255
        y = 1 - b / 255

        k = min(c, m, y)
        c = (c - k) / (1 - k)
        m = (m - k) / (1 - k)
        y = (y - k) / (1 - k)

        return tuple(int(round(i*scale)) for i in (c, m, y, k))

    @modding.help(brief="Color visualize", category="Misc", field="Commands", paragraph=2)
    @commands.command(aliases=["colour"])
    async def color(self, ctx, *args):
        '''
            `>>color <int, hex code or rgb>`
            Send an image filled with the color in question.
        '''
        if len(args) == 3:
            try:
                rgb = (int(args[0]), int(args[1]), int(args[2]))
            except ValueError:
                return await ctx.send("Oi, what's this format?")
        elif len(args) == 1:
            i = args[0]
            if i.startswith("0x"):
                i = i[2:]
            elif i.startswith("#"):
                i = i[1:]
            try:
                rgb = int(i, 16)
            except ValueError:
                return await ctx.send("Oi this is not color code at all.")
            else:
                rgb = self.get_rgb(rgb)
        else:
            return await ctx.send("Do you even try?")
        pic = Image.new("RGB", (50, 50), rgb)
        bytes_ = BytesIO()
        pic.save(bytes_, "png")

        rgb_value = rgb[0] * 256 * 256 + rgb[1] * 256 + rgb[2]
        f = discord.File(bytes_.getvalue(), filename="color.png")
        e = discord.Embed(title=f"#{rgb_value:X}", colour=rgb_value)
        e.set_thumbnail(url="attachment://color.png")
        e.add_field(name="RGB", value=", ".join((str(v) for v in rgb)))

        hsv = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
        hsv = tuple(int(round(i)) for i in (hsv[0]*360, hsv[2]*100, hsv[1]*100))
        e.add_field(name="HSV", value=f"{hsv[0]}\u00b0, {hsv[1]}%, {hsv[2]}%")

        hls = colorsys.rgb_to_hls(rgb[0]/255, rgb[1]/255, rgb[2]/255)
        hsl = tuple(int(round(i)) for i in (hls[0]*360, hls[2]*100, hls[1]*100))
        e.add_field(name="HSL", value=f"{hsl[0]}\u00b0, {hsl[1]}%, {hsl[2]}%")

        cmyk = self.rgb_to_cmyk(*rgb)
        e.add_field(name="CMYK", value=", ".join((f"{v}%" for v in cmyk)))
        await ctx.send(file=f, embed=e)

    @commands.command()
    async def pyfuck(self, ctx, *, data):
        '''
            `>>pyfuck <code>`
            Oh look, that fuckery is actually runable python code!
            Return a python program written with only 9 characters `e x c ( ) " % + <` that is equivalent to <code>.
            And yep, no newline.
        '''
        data = utils.clean_codeblock(data)
        char_group = ("e", "x", "c", "%", "+", "<", "(", ")")
        one = lambda: f"(\"\"<\"{random.choice(char_group)}\")"
        pf = []
        for char in data:
            if char in char_group:
                pf.append(f"\"{char}\"")
            else:
                base = f"{ord(char):b}"
                l = len(base)
                gr = []
                for i, v in enumerate(base):
                    if v == "1":
                        g = "<<".join((one() for j in range(l-i)))
                        gr.append(f"({g})")
                number = "+".join(gr)
                pf.append(f"\"%c\"%({number})")
        code = "+".join(pf)
        code = f"exec({code})"
        if len(code) < 2000:
            await ctx.send(code)
        else:
            await ctx.send(file=discord.File(code.encode("utf-8"), filename="fuck_this.py"))

    @modding.help(brief="Random choice", category="Misc", field="Commands", paragraph=2)
    @commands.command(name="choose")
    async def cmd_choose(self, ctx, *, choices):
        '''
            `>>choose <choices>`
            Choose a random item out of <choices>.
            List of choices is separated by "or".
        '''
        choices = choices.split(" or ")
        await ctx.send(random.choice(choices))

    @commands.command(name="embed")
    async def cmd_embed(self, ctx, *, kwargs: modding.KeyValue(escape=True)):
        '''
            `>>embed <data>`
            Display an embed.
            Data input is kwargs-like multiline, which each line has the format of `key=value`.
            Acceptable key: title, author, author_icon, description, url, colour (in hex), thumbnail, image, footer (text), field (each line add one field in final embed, using format `name|value|optional inline`)
        '''
        Empty = discord.Embed.Empty
        embed = discord.Embed(
            title=kwargs.get("title") or Empty,
            description=kwargs.geteither("description", "desc") or Empty,
            url=kwargs.get("url") or Empty,
            colour=utils.to_int(kwargs.geteither("colour", "color"), 16) or Empty,
        )

        author = kwargs.get("author")
        if author:
            embed.set_author(name=author, url=kwargs.get("author_url") or Empty, icon_url=kwargs.get("author_icon") or Empty)

        thumbnail = kwargs.get("thumbnail")
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        image = kwargs.get("image")
        if image:
            embed.set_image(url=image)

        footer = kwargs.get("footer")
        if footer:
            embed.set_footer(text=footer)

        fields = kwargs.getall("field", [])
        if len(fields) > 25:
            return await ctx.send("Too many fields.")
        for f in fields:
            items = tuple(utils.split_iter(f, check=lambda c: c=="|", keep_delimiters=False))
            if len(items) > 1:
                name = items[0].strip()
                value = items[1].strip()
                inline = utils.get_element(items, 2, default="true").strip().lower() in ("1", "true", "inline")
                if len(name) > 0 and len(value) > 0:
                    embed.add_field(name=name, value=value, inline=inline)

        try:
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(e)

    @commands.group(name="quote", invoke_without_command=True)
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def cmd_quote(self, ctx, msg_id: int, channel: discord.TextChannel=None):
        '''
            `>>quote <message ID> <optional: channel>`
            Display message.
        '''
        target = channel or ctx
        try:
            message = await target.get_message(msg_id)
        except discord.NotFound:
            await ctx.send("Can't find message.")
        except discord.Forbidden:
            await ctx.send(f"I don't have permissions to access {channel.mention}")
        else:
            embed = discord.Embed(title=f"ID: {msg_id}", description=message.content, colour=0x36393E)
            embed.add_field(name="Jump url", value=message.jump_url, inline=False)
            embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
            embed.set_footer(text=utils.format_time(message.created_at))
            if message.attachments:
                embed.set_image(url=message.attachments[0].url)
            await ctx.send(embed=embed)

    @cmd_quote.command(name="raw")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def cmd_quote_raw(self, ctx, msg_id: int, channel: discord.TextChannel=None):
        '''
            `>>quote raw <message ID> <optional: channel>`
            Display message with escaped characters.
        '''
        target = channel or ctx
        try:
            message = await ctx.get_message(msg_id)
        except discord.NotFound:
            await ctx.send("Can't find message.")
        except discord.Forbidden:
            await ctx.send(f"I don't have permissions to access {channel.mention}")
        else:
            embed = discord.Embed(title=f"ID: {msg_id}", description=utils.split_page(message.content, 2000, safe_mode=True)[0], colour=0x36393E)
            embed.add_field(name="Jump url", value=message.jump_url, inline=False)
            embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
            embed.set_footer(text=utils.format_time(message.created_at))
            if message.attachments:
                embed.set_image(url=message.attachments[0].url)
            await ctx.send(embed=embed)

    def to_ascii(self, image, width, height):
        image = image.resize((width, height)).convert("L")

        pixels = image.getdata()
        chars = [ASCII[int(p/RANGE)] for p in pixels]

        t = lstrip_generator(("".join(chars[i:i+width]).rstrip() for i in range(0, len(chars), width)))
        return "\n".join(t)

    @modding.help(brief="Grayscale ascii art", category="Misc", field="Processing", paragraph=2)
    @commands.group(invoke_without_command=True)
    async def ascii(self, ctx, *, data: modding.KeyValue({("", "member", "m"): discord.Member}, clean=False, multiline=False)=modding.EMPTY):
        '''
            `>>ascii <optional: member>`
            ASCII art of member avatar.
            If no member is specified, use your avatar.
        '''
        target = data.geteither("", "member", "m", default=ctx.author)
        url = strip_url(data.get("url", target.avatar_url))

        await ctx.trigger_typing()
        try:
            bytes_ = await self.bot.fetch(url)
        except aiohttp.InvalidURL:
            return await ctx.send("Invalid URL.")
        try:
            image = Image.open(BytesIO(bytes_))
        except OSError:
            return await ctx.send("Cannot identify image.")
        image = Image.open(BytesIO(bytes_))
        text = self.to_ascii(image, 64, 30)
        await ctx.send(f"```\n{text}\n```")

    @modding.help(brief="Bigger grayscale ascii art", category="Misc", field="Processing", paragraph=2)
    @ascii.command(name="big", aliases=["bigger", "biggur"])
    async def big_ascii(self, ctx, *, data: modding.KeyValue({("", "member", "m"): discord.Member, ("width", "w"): int}, clean=False, multiline=False)=modding.EMPTY):
        '''
            `>>ascii big <keyword: _|member|m> <keyword: width|w>`
            Bigger size ASCII art of member avatar, send as txt file due to discord's 2000 characters limit.
            If no member is specified, use your avatar. Default width is 256.
        '''
        target = data.geteither("", "member", "m", default=ctx.author)
        url = strip_url(data.get("url", target.avatar_url_as(format="png")))
        width = data.geteither("width", "w", default=256)
        if width > 1024:
            return await ctx.send("Width should be 1024 or less.")
        elif width < 64:
            return await ctx.send("Width should be 64 or more.")

        await ctx.trigger_typing()
        try:
            bytes_ = await self.bot.fetch(url)
        except aiohttp.InvalidURL:
            return await ctx.send("Invalid URL.")
        try:
            image = Image.open(BytesIO(bytes_))
        except OSError:
            return await ctx.send("Cannot identify image.")
        text = await self.bot.loop.run_in_executor(None, self.to_ascii, image, width, width//2)
        await ctx.send(file=discord.File(text.encode("utf-8"), filename=f"ascii_{len(text)}_chars.txt"))

    def setup_ascii_chars(self):
        self.chars = {}
        size = int(CHAR_SIZE[0] / 0.5894)
        font = ImageFont.truetype(f"{config.DATA_PATH}/font/consola.ttf", size)
        ts = font.getsize("A")
        from_top = (CHAR_SIZE[1] - ts[1] - 1) // 2
        for c in (
            " ", "'", "(", ")", "*", "+", ",", "-", ".", "/", ":", ";", "<", "=", ">", "?", "A", "C", "D", "H", "I",
            "J", "K", "L", "M", "N", "O", "S", "T", "U", "V", "W", "X", "Y", "Z", "[", "\\", "]", "^", "_", "|", "~"
        ):
            self.chars[c] = CharImage(c, font=font, pos=(0, from_top))

        self.chars["\\"].weight = 1.8
        self.chars["/"].weight = 1.8
        self.chars["_"].weight = 1.8
        self.chars["-"].weight = 1.8
        self.chars["<"].weight = 1.3
        self.chars[">"].weight = 1.3
        self.chars["|"].weight = 1.8
        self.chars["("].weight = 1.4
        self.chars[")"].weight = 1.4
        self.chars[";"].weight = 0.7
        self.chars["["].weight = 0.6
        self.chars["]"].weight = 0.6
        self.chars["~"].weight = 0.6
        self.chars["*"].weight = 0.6

        for c in ("A", "C", "D", "H", "I", "J", "K", "L", "M", "N", "O", "S", "T", "U", "V", "W", "X", "Y", "Z"):
            self.chars[c].weight = 0.6

    def convert_image_to_ascii(self, image, image_proc, per_cut, width, height, char_width, char_height, threshold, inverse):
        width = width
        height = height
        char_width = char_width
        char_height = char_height
        full_width = width * char_width
        full_height = height * char_height

        raw = []
        image = image.resize((full_width, full_height)).convert("L")
        if image_proc:
            image = image_proc(image)
        raw_pixels = np.array(image)
        pixels = np.where(raw_pixels>threshold, 1-inverse, inverse)
        range_height = range(char_height)
        range_width = range(char_width)

        for y in range(0, full_height, char_height):
            for x in range(0, full_width, char_width):
                cut = pixels[y:y+char_height, x:x+char_width]
                raw.append(per_cut(cut))

        t = lstrip_generator(("".join(raw[i:i+width]).rstrip() for i in range(0, width*height, width)))
        return "\n".join(t)

    def check_threshold(self, threshold, *, max=255):
        if threshold > max:
            raise checks.CustomError("Threshold is too big.")
        elif threshold < 0:
            raise checks.CustomError("Threshold should be a non-negative number.")

    def get_params(self, threshold, size):
        self.check_threshold(threshold)

        width, sep, height = size.partition("x")
        try:
            width = int(width.strip())
            height = int(height.strip())
        except ValueError:
            raise checks.CustomError("Please use `width x height` format for size.")
        else:
            if height < 5 or width < 5:
                raise checks.CustomError("Size too small.")
            if (width+1)*height > 1980:
                raise checks.CustomError("Size too large.")

        return threshold, width, height

    @modding.help(brief="Edge-detection ascii art", category="Misc", field="Processing", paragraph=2)
    @ascii.command(name="edge")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def ascii_edge(self, ctx, *, data: modding.KeyValue({("", "member", "m"): discord.Member, ("threshold", "t", "blur", "b"): int, ("weight", "w"): float, ("edge", "e", "inverse", "i"): bool}, clean=False, multiline=False)=modding.EMPTY):
        '''
            `>>ascii edge <keyword: _|member|m> <keyword: threshold|t> <keyword: blur|b> <keyword: weight> <keyword: size|s>`
            Edge-detection ASCII art of member avatar.
            If no member is specified, use your avatar.
            Less threshold, more dense. Default threshold is 32. Maximum threshold is 255.
            Less blur, more sharp. Default blur is 2. Maximum blur is 10.
            Less weight, bigger characters, default weight is 5.0
            Default size is 64x30.
            Has cooldown due to heavy processing (someone give me good algorithm pls).
        '''
        target = data.geteither("", "member", "m", default=ctx.author)
        url = strip_url(data.get("url", target.avatar_url_as(format="png")))
        size = data.geteither("size", "s", default="64x30")
        threshold = data.geteither("threshold", "t", default=32)
        blur = data.geteither("blur", "b", default=2)
        inverse_weight = data.geteither("weight", "w", default=5.0)
        edge = data.geteither("edge", "e", default=True)
        inverse = data.geteither("inverse", "i", default=0)

        threshold, width, height = self.get_params(threshold, size)
        if blur > 10:
            return await ctx.send("Blur value is too big.")
        elif blur < 0:
            return await ctx.send("Blur value should be a non-negative number.")
        if inverse_weight > 10:
            return await ctx.send("Inverse weight value is too big.")
        elif inverse_weight < 0:
            return await ctx.send("Inverse weight value should be a non-negative number.")

        await ctx.trigger_typing()
        try:
            bytes_ = await self.bot.fetch(url)
        except aiohttp.InvalidURL:
            return await ctx.send("Invalid URL.")
        try:
            image = Image.open(BytesIO(bytes_))
        except OSError:
            return await ctx.send("Cannot identify image.")

        def image_proc(image):
            if edge:
                image = image.filter(ImageFilter.FIND_EDGES)
            if blur > 0:
                image = image.filter(ImageFilter.GaussianBlur(radius=blur))
            return image

        chars = self.chars.items()
        inf = -float("inf")
        def per_cut(cut):
            best_weight = inf
            best_char = None
            for c, im in chars:
                weight = im.compare(cut, inverse_weight)
                if weight > best_weight:
                    best_weight = weight
                    best_char = c
            return best_char

        def do_stuff():
            start = time.perf_counter()
            ret = self.convert_image_to_ascii(image, image_proc, per_cut, width, height, *CHAR_SIZE, threshold, inverse)
            end = time.perf_counter()
            return ret, end-start

        result, time_taken = await self.bot.loop.run_in_executor(None, do_stuff)
        await ctx.send(f"Result in {time_taken*1000:.2f}ms```\n{result}\n```")

    @ascii_edge.error
    async def ascii_edge_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                "Woah slow down your command request.\n"
                "Remember that ascii edge has heavy processing so you can only use it once every 10 seconds.",
                delete_after=10
            )

    @modding.help(brief="Block ascii art", category="Misc", field="Processing", paragraph=2)
    @ascii.command(name="block")
    async def ascii_block(self, ctx, *, data: modding.KeyValue({("", "member", "m"): discord.Member, ("threshold", "t"): int, ("inverse", "i"): bool}, clean=False, multiline=False)=modding.EMPTY):
        '''
            `>>ascii block <keyword: _|member|m> <keyword: threshold|t> <keyword: inverse|i> <keyword: size|s>`
            Block ~~unicode~~ ASCII art of member avatar.
            If no member is specified, use your avatar.
            Threshold defines dark/light border. More threshold, more black pixels.
            Default threshold is 128. Max threshold is 255.
            Default size is 64x30.
        '''
        target = data.geteither("", "member", "m", default=ctx.author)
        url = strip_url(data.get("url", target.avatar_url_as(format="png")))
        size = data.geteither("size", "s", default="64x30")
        threshold = data.geteither("threshold", "t", default=128)
        inverse = data.geteither("inverse", "i", default=0)

        threshold, width, height = self.get_params(threshold, size)

        await ctx.trigger_typing()
        try:
            bytes_ = await self.bot.fetch(url)
        except aiohttp.InvalidURL:
            return await ctx.send("Invalid URL.")
        try:
            image = Image.open(BytesIO(bytes_))
        except OSError:
            return await ctx.send("Cannot identify image.")

        def per_cut(cut):
            return BOX_PATTERN[tuple(cut.flatten())]

        result = self.convert_image_to_ascii(image, None, per_cut, width, height, 1, 2, threshold, inverse)
        await ctx.send(f"```\n{result}\n```")

    @modding.help(brief="Braille dot ascii art", category="Misc", field="Processing", paragraph=2)
    @ascii.command(name="dot")
    async def ascii_dot(self, ctx, *, data: modding.KeyValue({("", "member", "m"): discord.Member, ("threshold", "t"): int, ("inverse", "i"): bool}, clean=False, multiline=False)=modding.EMPTY):
        '''
            `>>ascii dot <keyword: _|member|m> <keyword: threshold|t> <keyword: inverse|i> <keyword: size|s>`
            Braille dot ~~unicode~~ ASCII art of member avatar.
            If no member is specified, use your avatar.
            Threshold defines dark/light border. More threshold, more black pixels.
            Default threshold is 128. Max threshold is 255.
            Default size is 64x30.
        '''
        target = data.geteither("", "member", "m", default=ctx.author)
        url = strip_url(data.get("url", target.avatar_url_as(format="png")))
        size = data.geteither("size", "s", default="56x32")
        threshold = data.geteither("threshold", "t", default=128)
        inverse = data.geteither("inverse", "i", default=0)

        threshold, width, height = self.get_params(threshold, size)

        await ctx.trigger_typing()
        try:
            bytes_ = await self.bot.fetch(url)
        except aiohttp.InvalidURL:
            return await ctx.send("Invalid URL.")
        try:
            image = Image.open(BytesIO(bytes_))
        except OSError:
            return await ctx.send("Cannot identify image.")

        def per_cut(cut):
            cut = cut.flatten()
            pos = [str(p) for i, p in enumerate(DOT_PATTERN) if cut[i] == 1]
            if pos:
                pos.sort()
                return unicodedata.lookup(f"BRAILLE PATTERN DOTS-{''.join(pos)}")
            else:
                return next(blank_chars)

        result = await self.bot.loop.run_in_executor(None, self.convert_image_to_ascii, image, None, per_cut, width, height, 2, 4, threshold, inverse)
        if result.isspace():
            await ctx.send("Result is all blank. Maybe you should try tweaking threshold a little?")
        else:
            await ctx.send(f"\u200b{result}")

    @modding.help(brief="Moon emoji art", category="Misc", field="Processing", paragraph=2)
    @ascii.command(name="moon")
    async def ascii_moon(self, ctx, *, data: modding.KeyValue({("", "member", "m"): discord.Member, ("threshold", "t"): int, ("inverse", "i"): bool}, clean=False, multiline=False)=modding.EMPTY):
        '''
            `>>ascii moon <keyword: _|member|m> <keyword: threshold|t> <keyword: inverse|i> <keyword: size|s>`
            Moon ~~emoji~~ ASCII art of member avatar.
            If no member is specified, use your avatar.
            Threshold defines dark/light border. More threshold, more black pixels.
            Default threshold is 128. Max threshold is 255.
            Default size is 20x24.
        '''
        target = data.geteither("", "member", "m", default=ctx.author)
        url = strip_url(data.get("url", target.avatar_url_as(format="png")))
        size = data.geteither("size", "s", default="20x24")
        threshold = data.geteither("threshold", "t", default=128)
        inverse = data.geteither("inverse", "i", default=0)

        threshold, width, height = self.get_params(threshold, size)

        await ctx.trigger_typing()
        try:
            bytes_ = await self.bot.fetch(url)
        except aiohttp.InvalidURL:
            return await ctx.send("Invalid URL.")
        try:
            image = Image.open(BytesIO(bytes_))
        except OSError:
            return await ctx.send("Cannot identify image.")

        def per_cut(cut):
            pt = (np.sum(cut[:, 0:2])//3, np.sum(cut[:, 2:4])//3)
            return MOON_PATTERN[pt]

        result = await self.bot.loop.run_in_executor(None, self.convert_image_to_ascii, image, None, per_cut, width, height, 4, 4, threshold, inverse)
        await ctx.send(f"```\n{result}\n```")

    @modding.help(brief="pong", category=None, field="Other", paragraph=0)
    @commands.command(name="ping")
    async def cmd_ping(self, ctx):
        '''
            `>>ping`
            Ping the current channel.
        '''
        await self.ping(ctx)

    async def fetch_auto_rep_settings(self):
        async for data in self.guild_data.aggregate([
            {
                "$match": {
                    "no_auto_rep": True
                }
            },
            {
                "$group": {
                    "_id": None,
                    "guild_ids": {"$push": "$guild_id"}
                }
            }
        ]):
            self.auto_rep_disabled.update(data["guild_ids"])

    @modding.help(brief="Enable/disable auto-reply", field="Other", paragraph=0)
    @commands.command()
    @checks.guild_only()
    @checks.manager_only()
    async def autorep(self, ctx):
        '''
            `>>autorep`
            Enable/disable auto-reply.
            This includes ping, \\o\\ /o/ \\o/ /o\\ and stickers.
        '''
        guild_id = ctx.guild.id
        if guild_id in self.auto_rep_disabled:
            self.auto_rep_disabled.discard(guild_id)
            await self.guild_data.update_one({"guild_id": guild_id}, {"$unset": {"no_auto_rep": True}})
            await ctx.send("Auto-reply has been enabled.")
        else:
            self.auto_rep_disabled.add(guild_id)
            await self.guild_data.update_one({"guild_id": guild_id}, {"$set": {"no_auto_rep": True}, "$setOnInsert": {"guild_id": guild_id}}, upsert=True)
            await ctx.send("Auto-reply has been disabled.")

    @modding.help(brief="Monochrome transformation", category="Misc", field="Processing", paragraph=1)
    @commands.command(aliases=["ct"])
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def transform(self, ctx, *, data: modding.KeyValue({("member", "m", ""): discord.Member, ("threshold", "t"): int}, clean=False, multiline=False)=modding.EMPTY):
        '''
            `>>transform <keyword: _|member|m> <keyword: rgb> <keyword: threshold|t>`
            Apply a monochrome transformation to member avatar.
            Default member is command invoker.
            Rgb is in hex format, default is 7289da (blurple).
            Threshold defines how dark the target image is, default is 150.
        '''
        target = data.geteither("member", "m", "", default=ctx.author)
        url = strip_url(data.get("url", target.avatar_url_as(format="png")))
        rgb = data.get("rgb", "7289da").lstrip("#").lower()
        try:
            rgb = int(rgb, 16)
        except ValueError:
            return await ctx.send("Input is not RGB in hex format.")
        else:
            r, g, b = self.get_rgb(rgb)
        threshold = data.geteither("threshold", "t", default=150)
        self.check_threshold(threshold, max=255*4)
        size = data.geteither("size", "s")
        if size:
            try:
                width, height = (int(s.strip()) for s in size.split("x"))
            except ValueError:
                return await ctx.send("Size must be in widthxheight format.")

        await ctx.trigger_typing()
        bytes_ = await self.bot.fetch(url)

        def do_stuff():
            image = Image.open(BytesIO(bytes_)).convert("RGBA")
            if size:
                image = image.resize((width, height))
            a = np.array(image)
            t = np.dot(a[:, :, :3], [0.2989, 0.5870, 0.1140])
            t = np.array((r/threshold, g/threshold, b/threshold), dtype=np.float32) * t[:, :, None]
            if a.shape[2] == 4:
                t = np.concatenate((t, a[:, :, [3]]), axis=2)
            t[t>255] = 255
            t = t.astype(np.uint8)
            image = Image.fromarray(t)

            bio = BytesIO()
            image.save(bio, "png")
            return bio.getvalue()

        bytes_2 = await self.bot.loop.run_in_executor(None, do_stuff)
        await ctx.send(file=discord.File(bytes_2, "monochrome.png"))

    def rgb_to_hsv(self, rgb):
        rgb = rgb.astype("float")
        hsv = np.zeros_like(rgb)
        hsv[..., 3:] = rgb[..., 3:]
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        maxc = np.max(rgb[..., :3], axis=-1)
        minc = np.min(rgb[..., :3], axis=-1)
        hsv[..., 2] = maxc
        mask = maxc != minc
        hsv[mask, 1] = (maxc - minc)[mask] / maxc[mask]
        rc = np.zeros_like(r)
        gc = np.zeros_like(g)
        bc = np.zeros_like(b)
        rc[mask] = (maxc - r)[mask] / (maxc - minc)[mask]
        gc[mask] = (maxc - g)[mask] / (maxc - minc)[mask]
        bc[mask] = (maxc - b)[mask] / (maxc - minc)[mask]
        hsv[..., 0] = np.select([r==maxc, g==maxc], [bc-gc, 2.0+rc-bc], default=4.0+gc-rc)
        hsv[..., 0] = (hsv[..., 0] / 6.0) % 1.0
        return hsv

    def hsv_to_rgb(self, hsv):
        rgb = np.empty_like(hsv)
        rgb[..., 3:] = hsv[..., 3:]
        h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        i = (h * 6.0).astype("uint8")
        f = (h * 6.0) - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        i = i % 6
        conditions = [s == 0.0, i == 1, i == 2, i == 3, i == 4, i == 5]
        rgb[..., 0] = np.select(conditions, [v, q, p, p, t, v], default=v)
        rgb[..., 1] = np.select(conditions, [v, v, v, q, p, p], default=t)
        rgb[..., 2] = np.select(conditions, [v, p, t, v, v, q], default=p)
        return rgb.astype("uint8")

    def curve_reform(self, arr, v):
        if v == 0:
            arr = np.where(arr<=255, 0, 255)
        elif v == 1:
            pass
        else:
            m = 255 * v ** 2 / (4 - 4 * v)
            arr = m * (255 + m) / (255 + m - arr) - m
        return arr

    def linear_reform(self, arr, v):
        iv =  255 * (1 - v / 2)
        arr = np.where(arr<=iv, arr*(255-iv)/iv, (arr-iv)*iv/(255-iv)+255-iv)
        return arr

    @modding.help(brief="Monochrome transformation", category="Misc", field="Processing", paragraph=1)
    @commands.command(aliases=["ct2"])
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def transform2(self, ctx, *, data: modding.KeyValue({("member", "m", ""): discord.Member}, clean=False, multiline=False)=modding.EMPTY):
        '''
            `>>transform2 <keyword: _|member|m> <keyword: rgb> <keyword: mode>`
            Apply a monochrome transformation to member avatar.
            Default member is command invoker.
            Rgb is in hex format, default is 7289da (blurple).
            Mode is either linear or curve, default is linear.
        '''
        target = data.geteither("member", "m", "", default=ctx.author)
        url = strip_url(data.get("url", target.avatar_url_as(format="png")))
        rgb = data.get("rgb", "7289da").lstrip("#").lower()
        try:
            rgb = int(rgb, 16)
        except ValueError:
            return await ctx.send("Input is not RGB in hex format.")
        else:
            r, g, b = self.get_rgb(rgb)
        threshold = data.geteither("threshold", "t", default=150)
        self.check_threshold(threshold, max=255*4)
        mode = data.get("mode", "linear")
        mode_func = getattr(self, f"{mode}_reform", None)
        if mode_func is None:
            return await ctx.send("Mode must be either linear or curve.")
        size = data.geteither("size", "s")
        if size:
            try:
                width, height = (int(s.strip()) for s in size.split("x"))
            except ValueError:
                return await ctx.send("Size must be in widthxheight format.")

        await ctx.trigger_typing()
        bytes_ = await self.bot.fetch(url)

        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)

        def do_stuff():
            image = Image.open(BytesIO(bytes_)).convert("RGBA")
            a = np.array(image)
            hsv = self.rgb_to_hsv(a)
            hsv[..., 0] = h
            hsv[..., 2] = mode_func(hsv[..., 2], v)
            rgb = self.hsv_to_rgb(hsv)
            image = Image.fromarray(rgb)

            bio = BytesIO()
            image.save(bio, "png")
            return bio.getvalue()

        bytes_2 = await self.bot.loop.run_in_executor(None, do_stuff)
        await ctx.send(file=discord.File(bytes_2, "monochrome.png"))

    @modding.help(brief="Turn avatar into sketch", category="Misc", field="Processing", paragraph=1)
    @commands.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def sketch(self, ctx, *, data: modding.KeyValue({("member", "m", ""): discord.Member, ("sigma", "s"): int}, clean=False, multiline=False)=modding.EMPTY):
        '''
            `>>sketch <keyword: _|member|m> <keyword: sigma|s>`
            Turn member avatar into pencil sketch.
            Result is clearer with more sigma. Default sigma is 5, max sigma is 10.
        '''
        target = data.geteither("member", "m", "", default=ctx.author)
        url = strip_url(data.get("url", target.avatar_url_as(format="png")))
        sigma = data.geteither("sigma", "s", default=5)
        if sigma > 10:
            return await ctx.send("Max sigma is 10.")
        elif sigma <= 0:
            return await ctx.send("Sigma must be a positive number.")

        await ctx.trigger_typing()
        bytes_ = await self.bot.fetch(url)

        def dodge(front, back):
            result = front * 255 / (255 - back)
            result[result>255] = 255
            result[back==255] = 255
            return result.astype("uint8")

        def do_stuff():
            image = Image.open(BytesIO(bytes_)).convert("RGB")
            a = np.array(image)
            gray = np.dot(a[:, :, :3], [0.2989, 0.5870, 0.1140])
            invert = 255 - gray
            blur = scipy.ndimage.filters.gaussian_filter(invert, sigma=sigma)
            final = dodge(blur, gray)
            image = Image.fromarray(final)

            bio = BytesIO()
            image.save(bio, "png")
            return bio.getvalue()

        bytes_2 = await self.bot.loop.run_in_executor(None, do_stuff)
        await ctx.send(file=discord.File(bytes_2, "sketch.png"))

    @modding.help(brief="Turn avatar into sketch", category="Misc", field="Processing", paragraph=1)
    @commands.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def sketch2(self, ctx, *, data: modding.KeyValue({("member", "m", ""): discord.Member, ("depth", "d"): int}, clean=False, multiline=False)=modding.EMPTY):
        '''
            `>>sketch2 <keyword: _|member|m> <keyword: depth|d>`
            Turn member avatar into pencil sketch.
            Result is more dense with more depth. Default depth is 10, max depth is 100.
        '''
        target = data.geteither("member", "m", "", default=ctx.author)
        url = strip_url(data.get("url", target.avatar_url_as(format="png")))
        depth = data.geteither("depth", "d", default=10)
        if depth > 100:
            return await ctx.send("Max depth is 100.")
        elif depth <= 0:
            return await ctx.send("Depth must be a positive number.")

        await ctx.trigger_typing()
        bytes_ = await self.bot.fetch(url)

        ele = np.pi/2.2
        azi = np.pi/4

        def do_stuff():
            image = Image.open(BytesIO(bytes_)).convert("L")
            a = np.array(image).astype("float")
            grad = np.gradient(a)
            grad_x, grad_y = grad
            gd = np.cos(ele)
            dx = gd * np.cos(azi)
            dy = gd * np.sin(azi)
            dz = np.sin(ele)
            grad_x = grad_x * depth / 100
            grad_y = grad_y * depth / 100
            leng = np.sqrt(grad_x**2 + grad_y**2 + 1)
            uni_x = grad_x / leng
            uni_y = grad_y / leng
            uni_z = 1 / leng
            a2 = 255 * (dx*uni_x + dy*uni_y + dz*uni_z)
            a2 = a2.clip(0, 255)
            image = Image.fromarray(a2.astype("uint8"))

            bio = BytesIO()
            image.save(bio, "png")
            return bio.getvalue()

        bytes_2 = await self.bot.loop.run_in_executor(None, do_stuff)
        await ctx.send(file=discord.File(bytes_2, "sketch2.png"))

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Misc(bot))
