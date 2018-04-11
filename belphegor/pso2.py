import discord
from discord.ext import commands
from PIL import Image
from io import BytesIO
from . import utils
from .utils import config, checks, data_type, token
import aiohttp
import asyncio
import re
import html
from bs4 import BeautifulSoup as BS
import json
from datetime import datetime, timedelta
import traceback
from textwrap import indent
from apiclient.discovery import build
import weakref

#==================================================================================================================================================

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
    "tact":         "Tact",
    "rear":         "Rear",
    "arm":          "Arm",
    "leg":          "Leg",
    "sub_unit":     "Sub Unit"
}
ATK_EMOJIS = ("satk", "ratk", "tatk")
WEAPON_URLS = {
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
WEAPON_SORT = tuple(WEAPON_URLS.keys())
SSA_SLOTS = {
    "Tier 3":               ["s1", "s2", "s3"],
    "Tier 4":               ["s1", "s2", "s3", "s4"],
    "S Class Ability 1":    ["s1"],
    "S Class Ability 2":    ["s2"],
    "S Class Ability 3":    ["s3"]
}
DEF_EMOJIS = ("sdef", "rdef", "tdef")
RESIST_EMOJIS = ("s_res", "r_res", "t_res")
ELEMENTAL_RESIST_EMOJIS = ("fire_res", "ice_res", "lightning_res", "wind_res", "light_res", "dark_res")
UNIT_URLS = {
    "rear":     "https://pso2.arks-visiphone.com/wiki/Unit_List:_Rear",
    "arm":      "https://pso2.arks-visiphone.com/wiki/Unit_List:_Arm",
    "leg":      "https://pso2.arks-visiphone.com/wiki/Unit_List:_Leg",
    "sub_unit": "https://pso2.arks-visiphone.com/wiki/Unit_List:_Sub"
}
UNIT_SORT = tuple(UNIT_URLS.keys())
ICON_DICT = {
    "Ability.png":              "ability",
    "SpecialAbilityIcon.PNG":   "saf",
    "Special Ability":          "saf",
    "Potential.png":            "potential",
    "PA":                       "pa",
    "Set Effect":               "set_effect",
    "SClassAbilityIcon.png":    "s_class"
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
TIME_LEFT = ("Now", "HalfHour", "OneLater", "OneHalfLater", "TwoLater", "TwoHalfLater", "ThreeLater", "ThreeHalfLater")

no_html_regex = re.compile("\<\/?\w+?\>")
def _match_this(match):
    if match.group(0) in ("<br>", "</br>"):
        return "\n"
    elif match.group(0) == "<li>":
        return "\u2022 "
    else:
        return ""

simple_time_regex = re.compile(r"([0-9]{1,2})[-/]([0-9]{1,2})[-/]?([0-9]{2,4})?")

iso_time_regex = re.compile(r"([0-9]{4})\-([0-9]{2})\-([0-9]{2})T([0-9]{2})\:([0-9]{2})\:([0-9]{2})(Z|[+-]([0-9]{2})\:([0-9]{2}))")

#==================================================================================================================================================

class Chip(data_type.BaseObject):
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

class Weapon(data_type.BaseObject):
    def embed_form(self, cog):
        emojis = cog.emojis
        ctgr = self.category
        embed = discord.Embed(title=f"{emojis[ctgr]}{self.en_name}", url=WEAPON_URLS[ctgr], colour=discord.Colour.blue())
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
        description = f"{description}\n{usable_classes}"
        if self.ssa_slots:
            slots = "".join((str(emojis[s]) for s in self.ssa_slots))
            embed.description = f"{description}\n**Slots:** {slots}"
        else:
            embed.description = description
        if self.pic_url:
            embed.set_thumbnail(url=self.pic_url)
        rq = self.requirement
        embed.add_field(name="Requirement", value=f"{emojis[rq['type']]}{rq['value']}")
        max_atk = self.atk['max']
        embed.add_field(name="ATK", value="\n".join((f"{emojis[e]}{max_atk[e]}" for e in ATK_EMOJIS)))
        for prp in self.properties:
            embed.add_field(name=f"{emojis[prp['type']]}{prp['name']}", value=prp["description"], inline=False)
        return embed

#==================================================================================================================================================

class Unit(data_type.BaseObject):
    def embed_form(self, cog):
        emojis = cog.emojis
        ctgr = self.category
        embed = discord.Embed(title=f"{emojis[ctgr]}{self.en_name}", url=UNIT_URLS[ctgr], colour=discord.Colour.blue())
        description = ""
        most = self.rarity//3
        for i in range(most):
            emoji = emojis.get(f"star_{i}", None)
            description = f"{description}{emoji}{emoji}{emoji}"
        if self.rarity > most*3:
            emoji = emojis.get(f"star_{most}", None)
            for i in range(self.rarity - most*3):
                description = f"{description}{emoji}"
        embed.description = description
        if self.pic_url:
            embed.set_thumbnail(url=self.pic_url)
        rq = self.requirement
        embed.add_field(name="Requirement", value=f"{emojis[rq['type']]}{rq['value']}")
        max_def = self.defs['max']
        embed.add_field(name="DEF", value="\n".join((f"{emojis[e]}{max_def[e]}" for e in DEF_EMOJIS)))
        stats = self.stats
        stats_des = "\n".join((f"**{s.upper()}** + {stats[s]}" for s in ("hp", "pp") if stats[s]))
        embed.add_field(name="Stats", value=f"\n".join((stats_des, "\n".join((f"{emojis[s]}+ {stats[s]}" for s in ("satk", "ratk", "tatk", "dex") if stats[s])))))
        resist = self.resist
        res_des = "\n".join((f"{emojis[e]}+ {resist[e]}%" for e in RESIST_EMOJIS if resist[e]))
        if res_des:
            embed.add_field(name="Resist", value=res_des)
        ele_res_des = "\n".join((f"{emojis[e]}+ {resist[e]}%" for e in ELEMENTAL_RESIST_EMOJIS if resist[e]))
        if ele_res_des:
            embed.add_field(name="Elemental resist", value=ele_res_des)
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
        self.unit_list = bot.db.unit_list
        self.guild_data = bot.db.guild_data
        test_guild = self.bot.get_guild(config.TEST_GUILD_ID)
        test_guild_2 = self.bot.get_guild(config.TEST_GUILD_2_ID)
        self.emojis = {}
        for emoji_name in (
            "fire", "ice", "lightning", "wind", "light", "dark",
            "hu", "fi", "ra", "gu", "fo", "te", "br", "bo", "su", "hr",
            "satk", "ratk", "tatk", "ability", "potential",
            "pa", "saf", "star_0", "star_1", "star_2", "star_3", "star_4"
        ):
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild.emojis)
        for emoji_name in WEAPON_SORT:
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild.emojis)
        for emoji_name in (
            "sdef", "rdef", "tdef", "dex", "rear", "arm", "leg", "sub_unit", "s_res", "r_res", "t_res",
            "fire_res", "ice_res", "lightning_res", "wind_res", "light_res", "dark_res",
            "s_class", "s1", "s2", "s3", "s4"
        ):
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild_2.emojis)
        self.emojis["set_effect"] = self.emojis["rear"]
        self.eq_alert_forever = weakref.ref(bot.loop.create_task(self.eq_alert()))
        self.last_eq_data = None
        self.daily_order_pattern = bot.db.daily_order_pattern
        self.calendar = build("calendar", "v3", developerKey=token.GOOGLE_CLIENT_API_KEY)

    def cleanup(self):
        self.eq_alert_forever().cancel()

    @commands.command(aliases=["c"])
    async def chip(self, ctx, *, name):
        '''
            `>>chip <name>`
            Display a PSO2es chip info.
            Chip name is case-insensitive and can be either EN or JP.
        '''
        chip = await ctx.search(
            name, self.chip_library,
            cls=Chip, colour=discord.Colour.blue(),
            atts=["en_name", "jp_name"], name_att="en_name", emoji_att="element"
        )
        if not chip:
            return
        await ctx.send(embed=chip.embed_form(self))

    @commands.group(name="weapon", aliases=["w",], invoke_without_command=True)
    async def cmd_weapon(self, ctx, *, name):
        '''
            `>>weapon <name>`
            Display a PSO2 weapon info.
            Weapon name is case-insensitive and can be either EN or JP.
        '''
        weapon = await ctx.search(
            name, self.weapon_list,
            cls=Weapon, colour=discord.Colour.blue(),
            atts=["en_name", "jp_name"], name_att="en_name", emoji_att="category", sort={"category": WEAPON_SORT}
        )
        if not weapon:
            return
        await ctx.send(embed=weapon.embed_form(self))

    @cmd_weapon.command(hidden=True, name="update")
    @checks.owner_only()
    async def wupdate(self, ctx, *args):
        msg = await ctx.send("Fetching...")
        if not args:
            urls = WEAPON_URLS
        else:
            urls = {key: value for key, value in WEAPON_URLS.items() if key in args}
        weapons = []
        for category, url in urls.items():
            bytes_ = await utils.fetch(self.bot.session, url)
            category_weapons = await self.bot.loop.run_in_executor(None, self.weapon_parse, category, bytes_)
            weapons.extend(category_weapons)
            print(f"Done parsing {CATEGORY_DICT[category]}.")
        await self.weapon_list.delete_many({"category": {"$in": tuple(urls.keys())}})
        await self.weapon_list.insert_many(weapons)
        print("Done everything.")
        await msg.edit(content = "Done.")

    async def _search_att(self, attrs):
        result = []
        query = {}
        check_type = None
        projection = {"_id": False, "category": True, "en_name": True, "jp_name": True}
        for attr in attrs:
            orig_att = attr[0]
            value = attr[1]
            try:
                re_value = int(value)
                if orig_att == "atk":
                    q = {
                            "$or": [
                                {
                                    "atk.max.satk": re_value
                                },
                                {
                                    "atk.max.ratk": re_value
                                },
                                {
                                    "atk.max.tatk": re_value
                                }
                            ]
                        }
                else:
                    q = {orig_att: re_value}
                p = {orig_att: True}
            except:
                re_value = ".*?".join(map(re.escape, value.split()))
                p = None
                if orig_att in ("properties", "affix", "abi", "ability", "potential", "pot", "latent", "saf", "s_class"):
                    p = {"properties.$": True}
                    if orig_att == "properties":
                        t = {"$exists": True}
                    elif orig_att in ("affix", "abi", "ability"):
                        t = "ability"
                    elif orig_att in ("potential", "pot", "latent"):
                        t = "potential"
                    elif orig_att == "saf":
                        t = "saf"
                    elif orig_att == "s_class":
                        t = "s_class"
                    q = {
                        "properties": {
                            "$elemMatch": {
                                "$or": [
                                    {
                                        "name": {
                                            "$regex": re_value,
                                            "$options": "i"
                                        }
                                    },
                                    {
                                        "description": {
                                            "$regex": re_value,
                                            "$options": "i"
                                        }
                                    }
                                ],
                                "type": t
                            }
                        }
                    }
                elif orig_att in ("ssa_slots", "classes"):
                    q = {"$or": [{orig_att: {"$all": value.split()}}, {orig_att: "all_classes"}]}
                    p = {orig_att: True}
                else:
                    q = {orig_att: {"$regex": re_value, "$options": "i"}}
                    p = {orig_att: True}
            query.update(q)
            projection.update(p)

        async for weapon in self.weapon_list.find(query, projection=projection):
            new_weapon = {}
            new_weapon["category"] = weapon.pop("category")
            new_weapon["en_name"] = weapon.pop("en_name")
            new_weapon["jp_name"] = weapon.pop("jp_name")
            r = ""
            for key, value in weapon.items():
                if key == "properties":
                    value = value[0]
                    desc = f"{value['name']}\n{indent(value['description'], '     ')}"
                elif key == "atk":
                    desc = f"{self.emojis['satk']}{value['max']['satk']} {self.emojis['ratk']}{value['max']['ratk']} {self.emojis['tatk']}{value['max']['tatk']}"
                elif key in ("ssa_slots", "classes"):
                    if value == "all_classes":
                        desc = "".join((str(self.emojis[c]) for c in CLASS_DICT.values()))
                    else:
                        desc = "".join((str(self.emojis[s]) for s in value))
                else:
                    desc = value
                try:
                    if len(desc) > 200 and key not in ("ssa_slots", "classes"):
                        desc = f"{desc[:200]}..."
                except:
                    pass
                if key == "properties":
                    r = f"{r}\n   {self.emojis[value['type']]}{desc}"
                elif key == "atk":
                    r = f"{r}\n   {desc}"
                else:
                    r = f"{r}\n   {key}: {desc}"
            new_weapon["value"] = r
            result.append(new_weapon)
        return result

    @cmd_weapon.command(name="filter")
    async def w_filter(self, ctx, *, data):
        '''
            `>>w filter <criteria>`
            Find all weapons with <criteria>.
            Criteria can contain multiple lines, each with format `<attribute> <value>`.
            Available attributes:
            - en_name
            - jp_name
            - category
            - rarity
            - atk
            - properties/potential/ability/saf/s_class
            - classes
            - ssa_slots
        '''
        data = data.strip().splitlines()
        attrs = []
        for d in data:
            stuff = d.partition(" ")
            attrs.append((stuff[0].lower(), stuff[2].lower()))
        result = await self._search_att(attrs)
        if not result:
            return await ctx.send("No result found.")
        embeds = utils.embed_page_format(
            result, 5, separator="\n\n",
            title=f"Search result: {len(result)} results",
            description=lambda i, x: f"{self.emojis[x['category']]}**{x['en_name']}**{x['value']}",
            colour=discord.Colour.blue()
        )
        await ctx.embed_page(embeds)

    def weapon_parse(self, category, bytes_):
        category_weapons = []
        data = BS(bytes_.decode("utf-8"), "lxml")
        table = data.find("table", class_="wikitable sortable").find_all(True, recursive=False)[1:]
        for item in table:
            weapon = {"category": category}
            relevant = item.find_all(True, recursive=False)
            try:
                weapon["en_name"] = utils.unifix(relevant[2].find("a").get_text())
                weapon["jp_name"] = utils.unifix(relevant[2].find("p").get_text())
            except:
                continue
            weapon["rarity"] = utils.to_int(relevant[0].find("img")["alt"])
            try:
                weapon["pic_url"] = f"https://pso2.arks-visiphone.com{relevant[1].find('img')['src'].replace('64px-', '96px-')}"
            except:
                weapon["pic_url"] = None
            rq = utils.unifix(relevant[3].get_text()).partition(" ")
            weapon["requirement"] = {"type": rq[2].replace("-", "").lower(), "value": rq[0]}
            weapon["atk"] = {
                "base": {ATK_EMOJIS[i]: utils.to_int(l.strip()) for i, l in enumerate(relevant[5].find_all(text=True))},
                "max":  {ATK_EMOJIS[i]: utils.to_int(l.strip()) for i, l in enumerate(relevant[6].find_all(text=True))}
            }
            weapon["properties"] = []
            weapon["ssa_slots"] = []
            for child in relevant[7].find_all(True, recursive=False):
                if child.name == "img":
                    a = child["alt"]
                    t = ICON_DICT.get(a)
                    if t:
                        cur = {"type": t}
                    else:
                        weapon["ssa_slots"] = SSA_SLOTS[a]
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
        '''
            `>>item <name>`
            Find PSO2 items.
            Name given is case-insensitive, and can be either EN or JP.
        '''
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

    @commands.command(name="price")
    async def cmd_price(self, ctx, *, name):
        '''
            `>>price <name>`
            Check the price of an item.
        '''
        async with ctx.typing():
            params = {"name": name}
            bytes_ = await utils.fetch(self.bot.session, "http://db.kakia.org/item/search", params=params)
            result = json.loads(bytes_)
            if result:
                item = result[0]
                ship_field = []
                price_field = []
                last_updated_field = []
                for ship in range(1, 11):
                    ship_data = utils.get_element(item["PriceInfo"], lambda i: i["Ship"]==ship)
                    ship_field.append(str(ship))
                    if ship_data:
                        price_field.append(f"{ship_data['Price']:n}")
                        last_updated_field.append(ship_data["LastUpdated"])
                    else:
                        price_field.append("N/A")
                        last_updated_field.append("N/A")
                embed = discord.Embed(
                    title="Price info",
                    colour=discord.Colour.blue()
                )
                embed.add_field(name="Ship", value="\n".join(ship_field))
                embed.add_field(name="Price", value="\n".join(price_field))
                embed.add_field(name="Last updated", value="\n".join(last_updated_field))
                await ctx.send(embed=embed)
            else:
                await ctx.send("Can't find any item with that name.")

    @commands.command()
    async def jptime(self, ctx):
        '''
            `>>jptime`
            Current time in JP.
        '''
        await ctx.send(utils.jp_time(utils.now_time()))

    async def check_for_updates(self):
        bytes_ = await utils.fetch(
            self.bot.session,
            "https://pso2.acf.me.uk/PSO2Alert.json",
            headers={
                "User-Agent": "PSO2Alert_3.0.5.3",
                "Connection": "Keep-Alive",
                "Host": "pso2.acf.me.uk"
            }
        )
        data = json.loads(bytes_)[0]
        return data

    async def eq_alert(self):
        _loop = self.bot.loop
        acf_headers = {
            "User-Agent": "PSO2Alert",
            "Host": "pso2.acf.me.uk"
        }
        async def try_it(coro):
            try:
                await coro
            except:
                pass
        try:
            initial_data = await self.check_for_updates()
            print(f"Latest PSO2 Alert version: {initial_data['Version']}")
            while True:
                now_time = utils.now_time()
                if now_time.minute < 45:
                    delta = timedelta()
                    next_minute = 15 * (now_time.minute // 15 + 1)
                elif now_time.minute >= 45:
                    delta = timedelta(hours=1)
                    next_minute = 0
                next_time = now_time.replace(minute=next_minute, second=0) + delta
                await asyncio.sleep((next_time - now_time).total_seconds())
                now_time = utils.now_time()
                if now_time.minute != next_time.minute:
                    await asyncio.sleep((next_time - now_time).total_seconds())
                bytes_ = await utils.fetch(self.bot.session, initial_data["API"], headers=acf_headers)
                data = json.loads(bytes_)[0]
                self.last_eq_data = data
                now_time = utils.now_time(utils.jp_timezone)
                jst = int(data["JST"])
                start_time = now_time.replace(minute=0, second=0) + timedelta(hours=jst-1-now_time.hour)
                full_desc = []
                simple_desc = []
                ship_gen = (f"Ship{ship_number}" for ship_number in range(1, 11))
                random_eq = "\n".join((f"   `Ship {ship[4:]}:` {data[ship]}" for ship in ship_gen if data[ship]))

                for index, key in enumerate(TIME_LEFT):
                    if data[key]:
                        sched_time = start_time + timedelta(minutes=30*index)
                        time_left = int(round((sched_time - next_time).total_seconds(), -1))
                        if time_left == 0:
                            full_desc.append(f"\u2694 **Now**\n   `All ships:` {data[key]}")
                            if random_eq and index == 2:
                                full_desc.append(f"\u2694 **Now:**\n{random_eq}")
                        elif time_left > 0:
                            text = f"\u23f0 **In {utils.seconds_to_text(time_left)}:**\n   `All ships:` {data[key]}"
                            if random_eq and index == 2:
                                req_text = f"\u23f0 **In {utils.seconds_to_text(time_left)} minutes:**\n{random_eq}"
                            if time_left in (900, 2700, 6300, 9900):
                                full_desc.append(text)
                                if random_eq and index == 2:
                                    full_desc.append(req_text)
                            if time_left  in (2700, 6300):
                                simple_desc.append(text)
                                if random_eq and index == 2:
                                    simple_desc.append(req_text)

                if full_desc:
                    full_embed = discord.Embed(title="EQ Alert", description="\n\n".join(full_desc), colour=discord.Colour.red())
                    full_embed.set_footer(text=utils.jp_time(now_time))
                    async for gd in self.guild_data.find(
                        {"eq_channel_id": {"$exists": True}, "eq_alert_minimal": {"$ne": True}},
                        projection={"_id": False, "eq_channel_id": True}
                    ):
                        channel = self.bot.get_channel(gd["eq_channel_id"])
                        if channel:
                            _loop.create_task(try_it(channel.send(embed=full_embed)))
                if simple_desc:
                    simple_embed = discord.Embed(title="EQ Alert", description="\n\n".join(simple_desc), colour=discord.Colour.red())
                    simple_embed.set_footer(text=utils.jp_time(now_time))
                    async for gd in self.guild_data.find(
                        {"eq_channel_id": {"$exists": True}, "eq_alert_minimal": {"$eq": True}},
                        projection={"_id": False, "eq_channel_id": True}
                    ):
                        channel = self.bot.get_channel(gd["eq_channel_id"])
                        if channel:
                            _loop.create_task(try_it(channel.send(embed=simple_embed)))
        except asyncio.CancelledError:
            return
        except Exception as e:
            await asyncio.sleep(10)
            print(e)
            self.eq_alert_forever = _loop.create_task(self.eq_alert())

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
        '''
            `>>eq`
            Display eq schedule for the next 3 hours.
        '''
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
        for index, key in enumerate(TIME_LEFT):
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

    @commands.group(name="unit", aliases=["u"], invoke_without_command=True)
    async def cmd_unit(self, ctx, *, name):
        '''
            `>>unit <name>`
            Check a PSO2 unit info.
            Name given is case-insensitive, and can be either EN or JP.
        '''
        unit = await ctx.search(
            name, self.unit_list,
            cls=Unit, colour=discord.Colour.blue(),
            atts=["en_name", "jp_name"], name_att="en_name", emoji_att="category"
        )
        if not unit:
            return
        await ctx.send(embed=unit.embed_form(self))

    @cmd_unit.command(hidden=True, name="update")
    @checks.owner_only()
    async def uupdate(self, ctx, *args):
        msg = await ctx.send("Fetching...")
        if not args:
            urls = UNIT_URLS
        else:
            urls = {key: value for key, value in UNIT_URLS.items() if key in args}
        units = []
        for category, url in urls.items():
            bytes_ = await utils.fetch(self.bot.session, url)
            category_units = await self.bot.loop.run_in_executor(None, self.unit_parse, category, bytes_)
            units.extend(category_units)
            print(f"Done parsing {CATEGORY_DICT[category]}.")
        await self.unit_list.delete_many({"category": {"$in": tuple(urls.keys())}})
        await self.unit_list.insert_many(units)
        print("Done everything.")
        await msg.edit(content = "Done.")

    def unit_parse(self, category, bytes_):
        category_units = []
        data = BS(bytes_.decode("utf-8"), "lxml")
        table = data.find("table", class_="sortable").find_all(True, recursive=False)[3:]
        for item in table:
            unit = {"category": category}
            relevant = item.find_all(True, recursive=False)
            third_column = relevant[2]
            try:
                unit["en_name"] = utils.unifix(third_column.find("a").get_text())
                unit["jp_name"] = utils.unifix("".join((t.get_text() for t in third_column.find_all("span"))))
            except:
                continue
            unit["rarity"] = utils.to_int(relevant[0].find("img")["alt"])
            try:
                unit["pic_url"] = f"https://pso2.arks-visiphone.com{relevant[1].find('img')['src'].replace('64px-', '96px-')}"
            except:
                unit["pic_url"] = None
            rq_img_tag = third_column.find("img")
            unit["requirement"] = {"type": rq_img_tag["alt"].replace(" ", "").lower(), "value": int(rq_img_tag.next_sibling.strip())}
            unit["defs"] = {
                "base": {DEF_EMOJIS[i]: int(relevant[3+i].get_text().strip()) for i in range(3)},
                "max":  {DEF_EMOJIS[i]: int(relevant[6+i].get_text().strip()) for i in range(3)}
            }
            unit["stats"] = {}
            for i, s in enumerate(("hp", "pp", "satk", "ratk", "tatk", "dex")):
                unit["stats"][s] = utils.to_int(relevant[9+i].get_text().strip(), default=0)
            unit["resist"] = {}
            for i, s in enumerate(RESIST_EMOJIS):
                unit["resist"][s] = utils.to_int(relevant[15+i].get_text().replace("%", "").strip(), default=0)
            ele_res_tag = relevant[18].find_all("td")
            for i, s in enumerate(ELEMENTAL_RESIST_EMOJIS):
                unit["resist"][s] = utils.to_int(ele_res_tag[i].get_text().replace("%", "").strip(), default=0)
            category_units.append(unit)
        return category_units

    @commands.command(name="daily", aliases=["dailyorder"])
    async def cmd_daily_order(self, ctx, query_date=""):
        '''
            `>>daily <optional: date>`
            Display daily orders/featured quests schedule of the specified date.
            If no date is provided, today is used.
        '''
        m = simple_time_regex.fullmatch(query_date)
        jp_time = utils.now_time(utils.jp_timezone)
        if not m:
            do_time = datetime(jp_time.year, jp_time.month, jp_time.day, 1)
        else:
            try:
                do_time = datetime(utils.to_int(m.group(3), default=jp_time.year), int(m.group(2)), int(m.group(1)), 1)
            except:
                return await ctx.send("Uhh... that is not a valid date.")
        today_fq = []
        today_do = []
        async for doc in self.daily_order_pattern.aggregate([
            {
                "$project": {
                    "name": "$name",
                    "days": {
                        "$floor": {
                            "$mod": [
                                {
                                    "$divide": [
                                        {
                                            "$subtract": [do_time, "$first_day"]
                                        },
                                        1000 * 86400
                                    ]
                                },
                                "$interval"
                            ]
                        }
                    },
                    "interval_accumulate": "$interval_accumulate",
                    "type": "$type"
                }
            },
            {
                "$redact": {
                    "$cond": {
                        "if": {
                            "$in": ["$days", "$interval_accumulate"]
                        },
                        "then": "$$KEEP",
                        "else": "$$PRUNE"
                    }
                }
            }
        ]):
            if doc["type"] == "fq":
                today_fq.append(doc["name"])
            else:
                today_do.append(doc["name"])
        embed=discord.Embed(
            title=f"Daily Orders/Quests ({do_time.day:02d}-{do_time.month:02d}-{do_time.year:02d})",
            colour=discord.Colour.blue()
        )
        embed.add_field(name="Featured Quests", value="\n".join(today_fq) or "None", inline=False)
        embed.add_field(name="Daily Orders", value="\n".join(today_do) or "None", inline=False)
        embed.set_footer(text=utils.jp_time(jp_time))
        await ctx.send(embed=embed)

    def get_calendar_events(self, calendar_id, time_min=None):
        time_min = time_min or (utils.now_time(utils.jp_timezone)- timedelta(hours=1)).isoformat("T", "seconds")
        response = self.calendar.events().list(calendarId=calendar_id, timeMin=time_min).execute()
        results = []
        for item in response.get("items", []):
            title = item.get("summary").lower()
            if title.startswith(("pso2 day", "arks league")) or title.endswith("boost"):
                results.append(item)
        return results

    @commands.command(name="boost")
    @checks.owner_only()
    async def cmd_boost(self, ctx):
        incoming_events = await self.bot.loop.run_in_executor(None, self.get_calendar_events, "pso2emgquest@gmail.com")

        def process_date(i, x):
            start_date = iso_time_regex.fullmatch(x['start']['dateTime'])
            end_date = iso_time_regex.fullmatch(x['end']['dateTime'])
            txt = \
                f"From {start_date.group(4)}:{start_date.group(5)}, {start_date.group(3)}-{start_date.group(2)}\n" \
                f"To {end_date.group(4)}:{end_date.group(5)}, {end_date.group(3)}-{end_date.group(2)}"
            return x['summary'], txt, False

        embeds = utils.embed_page_format(
            incoming_events, 10, separator="\n\n",
            title="Boosto",
            fields=process_date,
            footer=utils.jp_time(utils.now_time())
        )
        await ctx.embed_page(embeds)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(PSO2(bot))
