import discord
from discord.ext import commands
from PIL import Image
from io import BytesIO
from . import utils
from .utils import config, checks
import aiohttp
import asyncio
import re
import html
from bs4 import BeautifulSoup as BS
import json
from datetime import datetime, timedelta
import traceback

CATEGORY_DICT = {
    "sword":        "Sword",
    "wl":           "Wired Lance",
    "partisan":     "Partisan",
    "td":           "Twin Dagger",
    "ds":           "Double Saber",
    "knuckle":      "Knuckle",
    "katana":       "Katana",
    "db":           "Dual Blade",
    "gs":           "Gunslash",
    "rifle":        "Assault Rifle",
    "launcher":     "Launcher",
    "tmg":          "Twin Machine Gun",
    "bow":          "Bullet Bow",
    "rod":          "Rod",
    "talis":        "Talis",
    "wand":         "Wand",
    "jb":           "Jet Boot",
    "tact":         "Tact"
}
ATK_EMOJI = ("satk", "ratk", "tatk")
URLS = {
    "sword":        "https://pso2.arks-visiphone.com/wiki/Simple_Swords_List",
    "wl":           "https://pso2.arks-visiphone.com/wiki/Simple_Wired_Lances_List",
    "partisan":     "https://pso2.arks-visiphone.com/wiki/Simple_Partizans_List",
    "td":           "https://pso2.arks-visiphone.com/wiki/Simple_Twin_Daggers_List",
    "ds":           "https://pso2.arks-visiphone.com/wiki/Simple_Double_Sabers_List",
    "knuckle":      "https://pso2.arks-visiphone.com/wiki/Simple_Knuckles_List",
    "katana":       "https://pso2.arks-visiphone.com/wiki/Simple_Katanas_List",
    "db":           "https://pso2.arks-visiphone.com/wiki/Simple_Dual_Blades_List",
    "gs":           "https://pso2.arks-visiphone.com/wiki/Simple_Gunslashes_List",
    "rifle":        "https://pso2.arks-visiphone.com/wiki/Simple_Assault_Rifles_List",
    "launcher":     "https://pso2.arks-visiphone.com/wiki/Simple_Launchers_List",
    "tmg":          "https://pso2.arks-visiphone.com/wiki/Simple_Twin_Machine_Guns_List",
    "bow":          "https://pso2.arks-visiphone.com/wiki/Simple_Bullet_Bows_List",
    "rod":          "https://pso2.arks-visiphone.com/wiki/Simple_Rods_List",
    "talis":        "https://pso2.arks-visiphone.com/wiki/Simple_Talises_List",
    "wand":         "https://pso2.arks-visiphone.com/wiki/Simple_Wands_List",
    "jb":           "https://pso2.arks-visiphone.com/wiki/Simple_Jet_Boots_List",
    "tact":         "https://pso2.arks-visiphone.com/wiki/Simple_Takts_List"
}
SORT_ORDER = tuple(CATEGORY_DICT.keys())
ICON_DICT = {
    "Ability.png":            "ability",
    "SpecialAbilityIcon.PNG": "saf",
    "Special Ability":        "saf",
    "Potential.png":          "potential",
    "PA":                     "pa",
    "Set Effect":             "set_effect"
}
for ele in ("Fire", "Ice", "Lightning", "Wind", "Light", "Dark"):
    ICON_DICT[ele] = ele.lower()
SPECIAL_DICT = {
    "color:purple": "arena",
    "color:red":    "photon",
    "color:orange": "fuse",
    "color:green":  "weaponoid"
}
CLASS_DICT = {
    "Hunter":   "hu",
    "Fighter":  "fi",
    "Ranger":   "ra",
    "Gunner":   "gu",
    "Force":    "fo",
    "Techer":   "te",
    "Braver":   "br",
    "Bouncer":  "bo",
    "Summoner": "su",
    "Hero":     "hr"
}
no_html_regex = re.compile("\<\/?\w+?\>")
def _match_this(match):
    if match.group(0) in ("<br>", "</br>"):
        return "\n"
    elif match.group(0) == "<li>":
        return "\u2022 "
    else:
        return ""

#==================================================================================================================================================

class Chip:
    def __init__(self, data):
        for key, value in data.items():
            if key[0] != "_":
                setattr(self, key, value)

    def embed_form(self, cog, la_form="en"):
        form = getattr(self, f"{la_form}_data")
        emojis = cog.emojis
        embed = discord.Embed(title=getattr(self, f"{la_form}_name"), url=self.url, colour=discord.Colour.blue())
        embed.set_thumbnail(url=self.pic_url)
        embed.add_field(name=self.category.capitalize(),
                        value=f"**Rarity** {self.rarity}\*\n**Class bonus** {emojis[self.class_bonus[0]]}{emojis[self.class_bonus[1]]}\n**HP/CP** {self.hp}/{self.cp}")
        embed.add_field(name="Active" if self.active else "Passive",
                        value=f"**Cost** {self.cost}\n**Element** {emojis[self.element]}{self.element_value}\n**Multiplication** {form['frame']}")
        abi = form["ability"]
        embed.add_field(name="Ability", value=f"**{abi['name']}**\n{abi['description']}", inline=False)
        embed.add_field(name="Duration", value=abi["effect_time"])
        for item in abi["value"]:
            sp_value = item.get("sp_value")
            if sp_value:
                desc = f"{item['value']}/{sp_value}"
            else:
                desc = item['value']
            embed.add_field(name=item["type"], value=desc)
        embed.add_field(name="Released ability", value=form['released_ability'], inline=False)
        embed.add_field(name="Illustrator", value=form['illustrator'])
        embed.add_field(name="CV", value=form['cv'])
        return embed

#==================================================================================================================================================

class Weapon:
    def __init__(self, data):
        for key, value in data.items():
            if key[0] != "_":
                setattr(self, key, value)

    def embed_form(self, cog):
        emojis = cog.emojis
        ctgr = self.category
        embed = discord.Embed(title=f"{emojis[ctgr]}{self.en_name}", url= URLS[ctgr], colour=discord.Colour.blue())
        description = ""
        most = self.rarity//3
        for i in range(most):
            emoji = emojis.get(f"star_{i}", None)
            description = f"{description}{emoji}{emoji}{emoji}"
        if self.rarity > most*3:
            emoji = emojis.get(f"star_{most}", None)
            for i in range(self.rarity - most*3):
                description = f"{description}{emoji}"
        if self.classes == "all_classes":
            usable_classes = ''.join((str(emojis[cl]) for cl in CLASS_DICT.values()))
        else:
            usable_classes = ''.join((str(emojis[cl]) for cl in self.classes))
        embed.description = f"{description}\n{usable_classes}"
        if self.pic_url:
            embed.set_thumbnail(url=self.pic_url)
        rq = self.requirement
        embed.add_field(name="Requirement", value=f"{emojis[rq['type']]}{rq['value']}")
        max_atk = self.atk['max']
        embed.add_field(name="ATK", value="\n".join([f"{emojis[e]}{max_atk[e]}" for e in ATK_EMOJI]))
        for prp in self.properties:
            embed.add_field(name=f"{emojis[prp['type']]}{prp['name']}", value=prp['description'], inline=False)
        return embed

#==================================================================================================================================================

class PSO2:
    '''
    PSO2 info.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.chip_library = bot.db.chip_library
        self.weapon_list = bot.db.weapon_list
        self.guild_data = bot.db.guild_data
        test_guild = self.bot.get_guild(config.TEST_GUILD_ID)
        test_guild_2 = self.bot.get_guild(config.TEST_GUILD_2_ID)
        self.emojis = {}
        for emoji_name in (
            "fire", "ice", "lightning", "wind", "light", "dark",
            "hu", "fi", "ra", "gu", "fo", "te", "br", "bo", "su", "hr",
            "satk", "ratk", "tatk", "ability", "potential", "set_effect",
            "pa", "saf", "star_0", "star_1", "star_2", "star_3", "star_4"
        ):
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild.emojis)
        for emoji_name in ("sdef", "rdef", "tdef", "dex"):
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild_2.emojis)
        for emoji_name in CATEGORY_DICT:
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild.emojis)

        self.eq_alert_forever = bot.loop.create_task(self.eq_alert())
        self.last_eq_data = None

    def cleanup(self):
        self.eq_alert_forever.cancel()

    @commands.command(aliases=["c", "chip"])
    async def chipen(self, ctx, *, name):
        chip = await ctx.search(name, self.chip_library, cls=Chip, atts=["en_name", "jp_name"], name_att="en_name", emoji_att="element")
        if not chip:
            return
        await ctx.send(embed=chip.embed_form(self))

    @commands.command(aliases=["cjp",])
    async def chipjp(self, ctx, *, name):
        chip = await ctx.search(name, self.chip_library, cls=Chip, atts=["en_name", "jp_name"], name_att="jp_name", emoji_att="element")
        if not chip:
            return
        await ctx.send(embed=chip.embed_form(self, "jp"))

    @commands.group(aliases=["w",], invoke_without_command=True)
    async def weapon(self, ctx, *, name):
        weapon = await ctx.search(
            name, self.weapon_list, cls=Weapon, atts=["en_name", "jp_name"],
            name_att="en_name", emoji_att="category", sort={"category": SORT_ORDER}
        )
        if not weapon:
            return
        await ctx.send(embed=weapon.embed_form(self))

    @weapon.command(name="update")
    @checks.owner_only()
    async def wupdate(self, ctx, *args):
        msg = await ctx.send("Fetching...")
        if not args:
            urls = URLS
        else:
            urls = {key: value for key, value in URLS.items() if key in args}
        weapons = []
        for category, url in urls.items():
            bytes_ = await utils.fetch(self.bot.session, url)
            category_weapons = await self.bot.loop.run_in_executor(None, self.bs_parse, category, bytes_)
            weapons.extend(category_weapons)
            print(f"Done parsing {CATEGORY_DICT[category]}.")
        await self.weapon_list.delete_many({"category": {"$in": tuple(urls.keys())}})
        await self.weapon_list.insert_many(weapons)
        print("Done everything.")
        await msg.edit(content = "Done.")

    def bs_parse(self, category, bytes_):
        def to_int(any_string):
            try:
                return int(any_string)
            except:
                return None
        category_weapons = []
        data = BS(bytes_.decode("utf-8"), "lxml")
        table = tuple(data.find("table", class_="wikitable sortable").find_all(True, recursive=False))[1:]
        for item in table:
            weapon = {"category": category}
            relevant = item.find_all(True, recursive=False)
            try:
                weapon["en_name"] = utils.unifix(relevant[2].find("a").get_text())
                weapon["jp_name"] = utils.unifix(relevant[2].find("p").get_text())
            except:
                continue
            try:
                weapon["rarity"] = int(relevant[0].find("img")["alt"])
            except:
                weapon["rarity"] = None
            try:
                weapon["pic_url"] = f"https://pso2.arks-visiphone.com{relevant[1].find('img')['src'].replace('64px-', '96px-')}"
            except:
                weapon["pic_url"] = None
            rq = utils.unifix(relevant[3].get_text()).partition(" ")
            weapon["requirement"] = {"type": rq[2].replace("-", "").lower(), "value": rq[0]}
            weapon["atk"] = {
                "base": {ATK_EMOJI[i]: to_int(l.strip()) for i, l in enumerate(relevant[5].find_all(text=True))},
                "max":  {ATK_EMOJI[i]: to_int(l.strip()) for i, l in enumerate(relevant[6].find_all(text=True))}
            }
            weapon["properties"] = []
            for child in relevant[7].find_all(True, recursive=False):
                if child.name == "img":
                    cur = {"type": ICON_DICT[child["alt"]]}
                elif child.name == "span":
                    cur["name"] = utils.unifix(child.get_text())
                    cur["description"] = utils.unifix(no_html_regex.sub(_match_this, html.unescape(child["data-simple-tooltip"])))
                    color = child.find("span")
                    if color:
                        cur["special"] = SPECIAL_DICT[color["style"]]
                    weapon["properties"].append(cur)
            weapon["classes"] = []
            for ctag in relevant[8].find_all("img"):
                cl = ctag["alt"]
                if cl == "All Class":
                    weapon["classes"] = "all_classes"
                    break
                else:
                    weapon["classes"].append(CLASS_DICT[cl])
            category_weapons.append(weapon)
        return category_weapons

    @commands.command(name="item", aliases=["i"])
    async def cmd_item(self, ctx, *, name):
        async with ctx.typing():
            params = {"name": name}
            bytes_ = await utils.fetch(self.bot.session, "http://db.kakia.org/item/search", params=params)
            result = json.loads(bytes_)
            number_of_items = len(result)
            embeds = []
            max_page = (number_of_items - 1) // 5 + 1
            nl = "\n"
            for index in range(0, number_of_items, 5):
                desc = "\n\n".join((
                    f"**EN:** {item['EnName']}\n**JP:** {utils.unifix(item['JpName'])}\n{item['EnDesc'].replace(nl, ' ')}"
                    for item in result[index:index+5]
                ))
                embed = discord.Embed(
                    title=f"Search result: {number_of_items} results",
                    description=f"{desc}\n\n(Page {index//5+1}/{max_page})",
                    colour=discord.Colour.blue()
                )
                embeds.append(embed)
            if not embeds:
                return await ctx.send("Can't find any item with that name.")
        await ctx.embed_page(embeds)

    @commands.command()
    async def jptime(self, ctx):
        await ctx.send(utils.jp_time(utils.now_time()))

    async def check_for_updates(self):
        bytes_ = await utils.fetch(
            self.bot.session,
            "https://pso2.acf.me.uk/PSO2Alert.json",
            headers={
                "User-Agent": "PSO2Alert_3.0.5.1",
                "Connection": "Keep-Alive",
                "Host": "pso2.acf.me.uk"
            }
        )
        data = json.loads(bytes_)[0]
        return data

    async def eq_alert(self):
        _loop = self.bot.loop
        initial_data = await self.check_for_updates()
        print(f"Latest PSO2 Alert version: {initial_data['Version']}")
        acf_headers = {
            "User-Agent": "PSO2Alert",
            "Host": "pso2.acf.me.uk"
        }
        try:
            while True:
                now_time = utils.now_time()
                if 0 <= now_time.minute < 15:
                    delta = timedelta()
                    next_minute = 15
                elif 15 <= now_time.minute < 30:
                    delta = timedelta()
                    next_minute = 30
                elif 30 <= now_time.minute < 45:
                    delta = timedelta()
                    next_minute = 45
                elif 45 <= now_time.minute < 60:
                    delta = timedelta(hours=1)
                    next_minute = 0
                next_time = now_time.replace(minute=next_minute, second=5) + delta
                while now_time.minute != next_time.minute:
                    await asyncio.sleep((next_time - now_time).total_seconds())
                    now_time = utils.now_time()
                bytes_ = await utils.fetch(self.bot.session, initial_data["API"], headers=acf_headers)
                data = json.loads(bytes_)[0]
                self.last_eq_data = data
                jst = int(data["JST"])
                now_time = utils.now_time(utils.jp_timezone)
                if now_time.hour == (jst - 1) % 24 or (now_time.hour == jst and now_time.minute == 0):
                    desc = []
                    ship_gen = (f"Ship{ship_number}" for ship_number in range(1, 11))
                    random_eq = "\n".join((f"   `Ship {ship[4]}:` {data[ship]}" for ship in ship_gen if data[ship]))
                    if now_time.minute == 0:
                        if data["OneLater"]:
                            desc.append(f"\u2694 **Now:**\n   `All ships:` {data['OneLater']}")
                        elif random_eq:
                            desc.append(f"\u2694 **Now:**\n{random_eq}")
                    elif now_time.minute == 15:
                        if data["HalfHour"]:
                            desc.append(f"\u23f0 **In 15 minutes:**\n   `All ships:` {data['HalfHour']}")
                        if data["OneLater"]:
                            desc.append(f"\u23f0 **In 45 minutes:**\n   `All ships:` {data['OneLater']}")
                        elif random_eq:
                            desc.append(f"\u23f0 **In 45 minutes:**\n{random_eq}")
                        if data["TwoLater"]:
                            desc.append(f"\u23f0 **In 1 hour 45 minutes:**\n   `All ships:` {data['TwoLater']}")
                        if data["ThreeLater"]:
                            desc.append(f"\u23f0 **In 2 hours 45 minutes:**\n   `All ships:` {data['ThreeLater']}")
                    elif now_time.minute == 30:
                        if data["HalfHour"]:
                            desc.append(f"\u2694 **Now:**\n   `All ships:` {data['HalfHour']}")
                    elif now_time.minute == 45:
                        if data["OneLater"]:
                            desc.append(f"\u23f0 **In 15 minutes:**\n   `All ships:` {data['OneLater']}")
                        elif random_eq:
                            desc.append(f"\u23f0 **In 15 minutes:**\n{random_eq}")
                        if data["OneHalfLater"]:
                            desc.append(f"\u23f0 **In 45 minutes:**\n   `All ships:` {data['OneHalfLater']}")
                        if data["TwoHalfLater"]:
                            desc.append(f"\u23f0 **In 1 hour 45 minutes:**\n   `All ships:` {data['TwoHalfLater']}")
                        if data["ThreeHalfLater"]:
                            desc.append(f"\u23f0 **In 2 hours 45 minutes:**\n   `All ships:` {data['ThreeHalfLater']}")
                    if desc:
                        embed = discord.Embed(title="EQ Alert", description="\n\n".join(desc), colour=discord.Colour.red())
                        embed.set_footer(text=utils.jp_time(now_time))
                        cursor = self.guild_data.aggregate([
                            {
                                "$group": {
                                    "_id": None,
                                    "eq_channel_ids": {
                                        "$addToSet": "$eq_channel_id"
                                    }
                                }
                            }
                        ])
                        async for d in cursor:
                            for cid in d["eq_channel_ids"]:
                                channel = self.bot.get_channel(cid)
                                if channel:
                                    _loop.create_task(channel.send(embed=embed))
                            break
        except asyncio.CancelledError:
            return
        except:
            print(traceback.format_exc())

    def get_emoji(self, dt_obj):
        if dt_obj.minute == 0:
            m = ""
        else:
            m = 30
        h = dt_obj.hour % 12
        if h == 0:
            h = 12
        return f":clock{h}{m}:"

    @commands.command(name="eq")
    async def nexteq(self, ctx):
        if not self.last_eq_data:
            bytes_ = await utils.fetch(self.bot.session, "https://pso2.acf.me.uk/api/eq.json", headers={"User-Agent": "PSO2Alert", "Host": "pso2.acf.me.uk"})
            self.last_eq_data = json.loads(bytes_)[0]
        data = self.last_eq_data
        now_time = utils.now_time(utils.jp_timezone)
        jst = int(data["JST"])
        start_time = now_time.replace(minute=0, second=0) + timedelta(hours=jst-1-now_time.hour)
        ship_gen = (f"Ship{ship_number}" for ship_number in range(1, 11))
        random_eq = "\n".join((f"`   Ship {ship[4]}:` {data[ship]}" for ship in ship_gen if data[ship]))
        sched_eq = []
        for index, key in enumerate(("Now", "HalfHour", "OneLater", "OneHalfLater", "TwoLater", "TwoHalfLater", "ThreeLater", "ThreeHalfLater")):
            if data[key]:
                sched_time = start_time + timedelta(minutes=30*index)
                sched_eq.append(f"{self.get_emoji(sched_time)} **At {sched_time.strftime('%I:%M %p')}**\n   {data[key]}")
        embed = discord.Embed(colour=discord.Colour.red())
        embed.set_footer(text=utils.jp_time(now_time))
        if random_eq or sched_eq:
            if random_eq:
                sched_time = start_time + timedelta(hours=1)
                embed.add_field(name="Random EQ", value="{self.get_emoji(sched_time)} **At {sched_time.strftime('%I:%M %p')}\n{random_eq}", inline=False)
            if sched_eq:
                embed.add_field(name="Schedule EQ", value="\n\n".join(sched_eq), inline=False)
        else:
            embed.description = "There's no EQ for the next 3 hours."
        await ctx.send(embed=embed)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(PSO2(bot))
