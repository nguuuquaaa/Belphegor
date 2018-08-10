import discord
from discord.ext import commands
import random
from . import utils, board_game
from .utils import config, checks
from bs4 import BeautifulSoup as BS
import asyncio
import unicodedata
import re
from pymongo import ReturnDocument
import json
from urllib.parse import quote
from io import BytesIO
import aiohttp
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import traceback
import collections
import time
import copy

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

#==================================================================================================================================================

class CharImage:
    def __init__(self, char, *, font, weight=None):
        image = Image.new("L", CHAR_SIZE, 0)
        draw = ImageDraw.Draw(image)
        draw.text((0, 0), char, font=font, fill=255)
        self.weight = weight or 1
        self.raw = tuple(1 if i > 127 else 0 for i in image.getdata())

    def compare(self, other):
        rating = 0
        inverse_rating = 0
        for char_value, other_value in zip(self.raw, other):
            rating += char_value * other_value
            inverse_rating += char_value * (1 - other_value)
        rating = (rating - self.INVERSE_WEIGHT * inverse_rating) * self.weight
        return rating

#==================================================================================================================================================

class Misc:
    '''
    Stuff that makes no difference if they aren't there.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.jankenpon_record = bot.db.jankenpon_record
        self.google_regex = re.compile(r"\<input name\=\"rlz\" value\=\"([a-zA-Z0-9_])\" type\=\"hidden\">")
        self.google_lock = asyncio.Lock()
        self.owo = {"/o/": "\\o\\", "\\o\\": "/o/", "\\o/": "/o\\", "/o\\": "\\o/"}
        self.setup_ascii_chars()

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

    async def on_message(self, message):
        if message.author.bot:
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

    @commands.command()
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

    @commands.command()
    async def fancy(self, ctx, *, textin: str):
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

    @commands.group(invoke_without_command=True)
    async def say(self, ctx, *, something: commands.clean_content):
        '''
            `>>say <text goes here>`
            Echo text.
        '''
        await ctx.send(something)

    @say.command(aliases=["hello",], name="hi")
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

    def parse_google(self, bytes_):
        data = BS(bytes_.decode("utf-8"), "lxml")
        for script in data("script"):
            script.decompose()

        search_results = []
        all_tags = data.find_all(lambda x: x.name=="div" and x.get("class")==["g"] and len(x.attrs)==1)
        for tag in all_tags:
            a = tag.find("a")
            a["href"] = utils.safe_url(a["href"])
            search_results.append(a)
            if len(search_results) > 4:
                break

        if not search_results:
            return None

        #video
        tag = data.find("div", class_="FGpTBd")
        if tag:
            other = '\n\n'.join([f"<{t['href']}>" for t in search_results[:4]])
            return f"**Search result:**\n{tag.find('a')['href']}\n\n**See also:**\n{other}"

        g_container = data.find(lambda x: x.name=="div" and "obcontainer" in x.get("class", []))
        if g_container:
            #unit convert
            if "WsjYwc" in g_container["class"]:
                try:
                    results = g_container.find_all(True, recursive=False)
                    embed = discord.Embed(title="Search result:", description=f"**Unit convert - {results[0].find('option', selected=1).text}**", colour=discord.Colour.dark_orange())
                    embed.add_field(name=results[1].find("option", selected=1).text, value=results[1].find("input")["value"])
                    embed.add_field(name=results[3].find("option", selected=1).text, value=results[3].find("input")["value"])
                    if search_results:
                        embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[:4])), inline=False)
                    return embed
                except:
                    pass

            #timezone convert
            zone_data = g_container.find("div", class_="sL6Rbf")
            if zone_data:
                try:
                    text = []
                    for stuff in zone_data.find_all(True, recursive=False):
                        table = stuff.find("table")
                        if table:
                            for tr in table.find_all(True, recursive=False):
                                text.append(tr.get_text())
                        else:
                            text.append(stuff.get_text().strip())
                    outtxt = "\n".join(text)
                    embed = discord.Embed(
                        title="Search result:",
                        description=f"**Timezone**\n{outtxt}",
                        colour=discord.Colour.dark_orange()
                    )
                    if search_results:
                        embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[:4])), inline=False)
                    return embed
                except:
                    pass

            #currency convert
            input_value = g_container.find("input", id="knowledge-currency__src-input")
            input_type = g_container.find("select", id="knowledge-currency__src-selector")
            output_value = g_container.find("input", id="knowledge-currency__tgt-input")
            output_type = g_container.find("select", id="knowledge-currency__tgt-selector")
            if all((input_value, input_type, output_value, output_type)):
                try:
                    embed = discord.Embed(title="Search result:", description="**Currency**", colour=discord.Colour.dark_orange())
                    embed.add_field(name=input_type.find("option", selected=1).text, value=input_value["value"])
                    embed.add_field(name=output_type.find("option", selected=1).text, value=output_value["value"])
                    if search_results:
                        embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[:4])), inline=False)
                    return embed
                except:
                    pass

            #calculator
            inp = data.find("span", class_="cwclet")
            out = data.find("span", class_="cwcot")
            if inp or out:
                try:
                    embed = discord.Embed(title="Search result:", description=f"**Calculator**\n{inp.text}\n\n {out.text}", colour=discord.Colour.dark_orange())
                    if search_results:
                        embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[:4])), inline=False)
                    return embed
                except:
                    pass

        #wiki
        tag = data.find("div", class_="knowledge-panel")
        if tag:
            try:
                title = tag.find("div", class_="kno-ecr-pt").span.text
                desc = tag.find('div', class_='kno-rdesc')
                if desc:
                    url_tag = desc.find("a")
                    if url_tag:
                        url = f"\n[{url_tag.text}]({utils.safe_url(url_tag['href'])})"
                    else:
                        url = ""
                    description = f"**{title}**\n{desc.find('span').text.replace('MORE', '').replace('…', '')}{url}"
                else:
                    description = f"**{title}**"
                embed = discord.Embed(title="Search result:", description=description, colour=discord.Colour.dark_orange())
                embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[:4])), inline=True)
                return embed
            except:
                pass

        #definition
        tag = data.find("div", class_="lr_container")
        if tag:
            try:
                relevant_data = tag.find_all(
                    lambda t:
                        (
                            t.name=="div"
                            and (
                                t.get("data-dobid")=="dfn"
                                or t.get("class") in (["lr_dct_sf_h"], ["xpdxpnd", "vk_gy"], ["vmod", "vk_gy"])
                                or t.get("style")=="float:left"
                            )
                        )
                        or
                        (
                            t.name=="span"
                            and (
                                t.get("data-dobid")=="hdw"
                                or t.get("class")==["lr_dct_ph"]
                            )
                        )
                )
                word = ""
                pronoun = ""
                current_page = -1
                defines = []
                for t in relevant_data:
                    if t.name == "span":
                        if t.get("data-dobid") == "hdw":
                            word = t.text
                        else:
                            pronoun = t.text
                    else:
                        if t.get("class") == ["lr_dct_sf_h"]:
                            current_page += 1
                            defines.append(f"**{word}**\n/{pronoun}\n")
                        elif "vk_gy" in t.get("class", []):
                            form = ""
                            for child_t in t.find_all(True):
                                if child_t.name == "b":
                                    form = f"{form}*{child_t.find(text=True, recursive=False)}*"
                                else:
                                    form = f"{form}{child_t.find(text=True, recursive=False)}"
                            defines[current_page] = f"{defines[current_page]}\n{form}"
                        elif t.get("style") == "float:left":
                            defines[current_page] = f"{defines[current_page]}\n**{t.text}**"
                        else:
                            defines[current_page] = f"{defines[current_page]}\n- {t.text}"
                see_also = '\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[1:5]))
                embeds = []
                max_page = len(defines)
                for i, d in enumerate(defines):
                    embed = discord.Embed(title="Search result:", description=f"{defines[i]}\n\n(Page {i+1}/{max_page})", colour=discord.Colour.dark_orange())
                    embed.add_field(name="See also:", value=see_also, inline=False)
                    embeds.append(embed)
                return embeds
            except:
                pass

        #weather
        tag = data.find("div", class_="card-section", id="wob_wc")
        if tag:
            try:
                more_link = tag.next_sibling.find("a")
                embed = discord.Embed(
                    title="Search result:",
                    description=f"**Weather**\n[{more_link.text}]({utils.safe_url(more_link['href'])})",
                    colour=discord.Colour.dark_orange()
                )
                embed.set_thumbnail(url=f"https:{tag.find('img', id='wob_tci')['src']}")
                embed.add_field(
                    name=tag.find("div", class_="vk_gy vk_h").text,
                    value=f"{tag.find('div', id='wob_dts').text}\n{tag.find('div', id='wob_dcp').text}",
                    inline=False
                )
                embed.add_field(name="Temperature", value=f"{tag.find('span', id='wob_tm').text}°C | {tag.find('span', id='wob_ttm').text}°F")
                embed.add_field(name="Precipitation", value=tag.find('span', id='wob_pp').text)
                embed.add_field(name="Humidity", value=tag.find('span', id='wob_hm').text)
                embed.add_field(name="Wind", value=tag.find('span', id='wob_ws').text)
                embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[1:5])), inline=False)
                return embed
            except:
                pass

        #simple wiki
        tag = data.find(lambda x: x.name=="div" and x.get("class")==["mod"] and x.get("style")=="clear:none")
        if tag:
            try:
                embed = discord.Embed(title="Search result:", description=f"{tag.text}\n[{search_results[0].text}]({search_results[0]['href']})", colour=discord.Colour.dark_orange())
                embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[1:5])), inline=False)
                return embed
            except:
                pass

        #translate
        tag = data.find("div", id="tw-container")
        if tag:
            try:
                s = tag.find("div", id="tw-source")
                inp = s.find("textarea", id="tw-source-text-ta")
                inp_lang = s.find("div", class_="tw-lang-selector-wrapper").find("option", selected="1")
                t = tag.find("div", id="tw-target")
                out = t.find("pre", id="tw-target-text")
                out_lang = t.find("div", class_="tw-lang-selector-wrapper").find("option", selected="1")
                link = tag.next_sibling.find("a")
                embed = discord.Embed(title="Search result:", description=f"[Google Translate]({link['href']})", colour=discord.Colour.dark_orange())
                embed.add_field(name=inp_lang.text, value=inp.text)
                embed.add_field(name=out_lang.text, value=out.text)
                embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[0:4])), inline=False)
                return embed
            except:
                pass

        #non-special search
        other = '\n\n'.join((f"<{r['href']}>" for r in search_results[1:5]))
        return f"**Search result:**\n{search_results[0]['href']}\n**See also:**\n{other}"

    @commands.command(aliases=["g"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def google(self, ctx, *, search):
        '''
            `>>google <query>`
            Google search.
            Safe search is enabled in non-nsfw channels and disabled in nsfw channels.
            There's a 10-second cooldown per user.
        '''
        await ctx.trigger_typing()
        params = {
            "q": quote(search),
            "safe": "active",
            "lr": "lang_en",
            "hl": "en"
        }
        if ctx.channel.is_nsfw():
            params.pop("safe")
        async with self.google_lock:
            bytes_ = await self.bot.fetch("https://www.google.com/search", params=params)

        result = await self.bot.loop.run_in_executor(None, self.parse_google, bytes_)
        if isinstance(result, discord.Embed):
            await ctx.send(embed=result)
        elif isinstance(result, str):
            await ctx.send(result)
        elif not result:
            await ctx.send("No result found.\nEither query yields nothing or Google blocked me (REEEEEEEEEEEEEEEEEEEEEEEE)")
        elif isinstance(result, list):
            paging = utils.Paginator(result, render=False)
            await paging.navigate(ctx)
        else:
            await ctx.send("I-it's not an error I tell ya! It's a feature!")

    @google.error
    async def google_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Whoa slow down your Google search! You can only search once every 10 seconds.")

    @commands.command(aliases=["translate", "trans"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def gtrans(self, ctx, *, search):
        '''
            `>>gtrans <text>`
            Google translate.
            Input is automatically detected, output is English.
            There's a 10-second cooldown per user.
        '''
        await ctx.trigger_typing()
        params = {
            "tl": "en",
            "hl": "en",
            "sl": "auto",
            "ie": "UTF-8",
            "q": quote(search)
        }
        async with self.google_lock:
            bytes_ = await self.bot.fetch("http://translate.google.com/m", params=params)

        data = BS(bytes_.decode("utf-8"), "lxml")
        tag = data.find("div", class_="t0")
        embed = discord.Embed(colour=discord.Colour.dark_orange())
        embed.add_field(name="Detect", value=search)
        embed.add_field(name="English", value=tag.get_text())
        await ctx.send(embed=embed)

    @gtrans.error
    async def gtrans_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Whoa slow down your Google translate! You can only do it once every 10 seconds.")

    @commands.command()
    async def char(self, ctx, *, characters):
        '''
            `>>char <characters>`
            Check unicode codepoint and name of characters.
        '''
        characters = re.sub(r"\s", "", characters)
        if len(characters) > 20:
            await ctx.send("Too many characters.")
        else:
            await ctx.send("\n".join([f"`\\U{ord(c):08x}` - `{c}` - {unicodedata.name(c, 'No name found.')}" for c in characters]))

    @commands.command()
    async def poll(self, ctx, *, data):
        '''
            `>>poll <question and choices>`
            Make a poll.
            Question and choices are separated by newline.
            The default (and shortest) duration is 60 seconds. You can specify more in question, i.e. `in 60 minutes`.
        '''
        stuff = data.strip().splitlines()
        question, duration = utils.extract_time(stuff[0])
        duration = duration.total_seconds()
        if duration < 60:
            duration = 60
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

    @commands.group(invoke_without_command=True)
    async def glitch(self, ctx, *, text):
        '''
            `>>glitch <optional: weight> <text>`
            Generate Zalgo text.
            More weight, more weird.
            Default weight is 20.
        '''
        if ctx.invoked_subcommand is None:
            data = text.partition(" ")
            try:
                weight = int(data[0])
            except:
                weight = 20
            else:
                text = data[2]
            if 0 < weight <= 50:
                await ctx.send("".join(("".join((c, "".join((random.choice(GLITCH_ALL) for i in range(weight))))) for c in text)))
            else:
                await ctx.send("Weight value can only be between 1 and 50.")

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

    @commands.command(aliases=["colour"])
    async def color(self, ctx, *args):
        '''
            `>>color <int or hex code>`
            Send an image filled with the color in question.
        '''
        if len(args) == 3:
            try:
                rgb = (int(args[0]), int(args[1]), int(args[2]))
            except:
                return await ctx.send("Oi, that's not RGB format at all.")
        elif len(args) == 1:
            i = args[0]
            if i.startswith("0x"):
                i = i[2:]
            elif i.startswith("#"):
                i = i[1:]
            try:
                c = discord.Colour(int(i, 16))
            except:
                return await ctx.send("Oi, that's not color code at all.")
        else:
            return await ctx.send("Do you even try?")
        pic = Image.new("RGB", (50, 50), c.to_rgb())
        bytes_ = BytesIO()
        pic.save(bytes_, "png")
        f = discord.File(bytes_.getvalue(), filename="color.png")
        e = discord.Embed(title=f"#{c.value:06X}", colour=c)
        e.set_image(url="attachment://color.png")
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

    @commands.command(name="choose")
    async def cmd_choose(self, ctx, *, choices):
        '''
            `>>choose <choices>`
            Choose a random item out of <choices>.
            List of choices is separated by "or".
        '''
        choices = choices.split(" or ")
        await ctx.send(random.choice(choices))

    @commands.command(name="embed", hidden=True)
    async def cmd_embed(self, ctx, *, data):
        data = data.splitlines()
        kwargs = {"fields": []}
        for item in data:
            p = item.partition("=")
            k = p[0].strip()
            try:
                v = p[2].strip().encode("raw_unicode_escape").decode("unicode_escape")
            except:
                return await ctx.send("Unicode coding error.")
            if k == "field":
                kwargs["fields"].append(v.split("||"))
            else:
                kwargs[k] = v

        Empty = discord.Embed.Empty
        embed = discord.Embed(
            title=kwargs.get("title") or Empty,
            description=kwargs.get("description") or Empty,
            url=kwargs.get("url") or Empty,
            colour=utils.to_int(kwargs.get("colour", kwargs.get("color")), 16) or Empty,
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

        fields = kwargs["fields"]
        if len(fields) > 25:
            return await ctx.send("Too many fields.")
        for f in fields:
            if len(f) > 1:
                if len(f[0]) > 0 and len(f[1]) > 0:
                    embed.add_field(name=f[0].strip(), value=f[1].strip(), inline=utils.get_element(f, 2, default="true").strip() in ("True", "1", "true", "inline"))

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
        except:
            await ctx.send("Can't find message.")
        else:
            embed = discord.Embed(title=f"ID: {msg_id}", description=message.content)
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
        except:
            await ctx.send("Can't find message.")
        else:
            embed = discord.Embed(title=f"ID: {msg_id}", description=utils.split_page(message.content, 2000, safe_mode=True)[0])
            embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
            embed.set_footer(text=utils.format_time(message.created_at))
            if message.attachments:
                embed.set_image(url=message.attachments[0].url)
            await ctx.send(embed=embed)

    def to_ascii(self, image_bytes, width, height):
        raw = Image.open(BytesIO(image_bytes))
        image = raw.resize((width, height)).convert("L")

        pixels = image.getdata()
        chars = [ASCII[int(p/RANGE)] for p in pixels]

        t = ("".join(chars[i:i+width]) for i in range(0, len(chars), width))
        return "\n".join(t)

    @commands.group(invoke_without_command=True)
    async def ascii(self, ctx, member: discord.Member=None):
        '''
            `>>ascii <optional: member>`
            ASCII art of member avatar.
            If no member is specified, use your avatar.
        '''
        await ctx.trigger_typing()
        target = member or ctx.author
        bytes_ = await self.bot.fetch(target.avatar_url)
        text = self.to_ascii(bytes_, 64, 30)
        await ctx.send(f"```\n{text}\n```")

    @ascii.command(name="big", aliases=["bigger", "biggur"])
    async def big_ascii(self, ctx, member: discord.Member=None, width=256):
        '''
            `>>ascii big <optional: member> <optional: width>`
            Bigger size ASCII art of member avatar, send as txt file due to discord 2000 characters limit.
            If no member is specified, use your avatar. Default width is 256.
        '''
        await ctx.trigger_typing()
        target = member or ctx.author
        if width > 1024:
            return await ctx.send("Width should be 1024 or less.")
        elif width < 64:
            return await ctx.send("Width should be 64 or more.")
        bytes_ = await self.bot.fetch(target.avatar_url)
        text = await self.bot.loop.run_in_executor(None, self.to_ascii, bytes_, width, width//2)
        await ctx.send(file=discord.File(text.encode("utf-8"), filename=f"ascii_{len(text)}_chars.txt"))

    @ascii.command(name="block")
    async def ascii_block(self, ctx, member: discord.Member=None):
        '''
            `>>ascii block <optional: member>`
            Block ~~unicode~~ ASCII art of member avatar.
            If no member is specified, use your avatar.
        '''
        target = member or ctx.author
        bytes_ = await self.bot.fetch(target.avatar_url)

        def do_stuff():
            image = Image.open(BytesIO(bytes_))

            height = 30
            width = 64
            proc = image.resize((width, 2*height)).convert("L")

            pixels = proc.getdata()
            output = []
            for i in range(height):
                for j in range(width):
                    upper = 255 - pixels[i*2*width+j]
                    lower = 255 - pixels[(i*2+1)*width+j]
                    if upper-lower>=128:
                        output.append("▀")
                    elif lower-upper>=128:
                        output.append("▄")
                    else:
                        if upper+lower>=320:
                            output.append("█")
                        elif upper+lower>=256:
                            output.append("▓")
                        elif upper+lower>=192:
                            output.append("▒")
                        elif upper+lower>=96:
                            output.append("░")
                        else:
                            output.append(" ")

            t = ("".join(output[i:i+width]) for i in range(0, len(output), width))
            return "\n".join(t)

        result = await self.bot.loop.run_in_executor(None, do_stuff)
        await ctx.send(f"```\n{result}\n```")

    def setup_ascii_chars(self):
        CharImage.INVERSE_WEIGHT = 4
        self.chars = {}
        font = ImageFont.truetype(f"{config.DATA_PATH}/font/consola.ttf", CHAR_SIZE[1])
        for c in (
            " ", "'", "(", ")", "*", "+", ",", "-", ".", "/", ":", ";", "<", "=", ">", "?", "A", "C", "D", "H", "I",
            "J", "K", "L", "M", "N", "O", "S", "T", "U", "V", "W", "X", "Y", "Z", "[", "\\", "]", "^", "_", "|", "~"
        ):
            self.chars[c] = CharImage(c, font=font)

        self.chars["\\"].weight = 2
        self.chars["/"].weight = 2
        self.chars["_"].weight = 2
        self.chars["-"].weight = 2
        self.chars["<"].weight = 1.3
        self.chars[">"].weight = 1.3
        self.chars["|"].weight = 1.8
        self.chars["("].weight = 1.4
        self.chars[")"].weight = 1.4
        self.chars[";"].weight = 0.7
        self.chars["["].weight = 0.6
        self.chars["]"].weight = 0.6
        self.chars["~"].weight = 0.6

        for c in ("A", "C", "D", "H", "I", "J", "K", "L", "M", "N", "O", "S", "T", "U", "V", "W", "X", "Y", "Z"):
            self.chars[c].weight = 0.6

    @ascii.command(name="edge")
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def ascii_edge(self, ctx, member: discord.Member=None, threshold: int=32, blur: int=2):
        '''
            `>>ascii edge <optional: member> <optional: threshold> <optional: blur>`
            Edge-detection ASCII art of member avatar.
            If no member is specified, use your avatar.
            Less threshold, more dense. Default threshold is 32. Maximum threshold is 255.
            Less blur, more sharp. Default blur is 2. Maximum blur is 10.
            Has 10s cooldown due to heavy processing (someone give me good algorithm pls).
        '''
        if threshold > 255:
            return await ctx.send("Threshold is too big.")
        elif threshold < 0:
            return await ctx.send("Threshold should be a non-negative number.")
        if blur > 10:
            return await ctx.send("Blur value is too big.")
        elif blur < 0:
            return await ctx.send("Blur value should be a non-negative number.")
        await ctx.trigger_typing()
        target = member or ctx.author
        bytes_ = await self.bot.fetch(target.avatar_url)

        def do_stuff():
            width = 64
            height = 30
            char_width, char_height = CHAR_SIZE
            full_width = width * char_width
            full_height = height * char_height

            start = time.perf_counter()
            image = Image.open(BytesIO(bytes_)).resize((full_width, full_height)).convert("L").filter(ImageFilter.FIND_EDGES)
            if blur > 0:
                image = image.filter(ImageFilter.GaussianBlur(radius=blur))
            raw = []
            pixels = tuple(1 if p > threshold else 0 for p in image.getdata())
            inf = -float("inf")
            chars = self.chars.items()
            range_height = range(char_height)
            range_width = range(char_width)

            for y in range(0, full_height, char_height):
                for x in range(0, full_width, char_width):
                    cut = tuple(pixels[x+i+(y+j)*full_width] for j in range_height for i in range_width)
                    best_weight = inf
                    best_char = None
                    for c, im in chars:
                        weight = im.compare(cut)
                        if weight > best_weight:
                            best_weight = weight
                            best_char = c
                    raw.append(best_char)
            end = time.perf_counter()

            t = ("".join(raw[i:i+width]) for i in range(0, width*height, width))
            return "\n".join(t), end-start

        result, time_taken = await self.bot.loop.run_in_executor(None, do_stuff)
        await ctx.send(f"Result in {time_taken*1000:.2f}ms```\n{result}\n```")

    @commands.command(name="ping")
    async def cmd_ping(self, ctx):
        await self.ping(ctx)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Misc(bot))
