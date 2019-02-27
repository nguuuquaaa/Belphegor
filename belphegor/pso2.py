import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from . import utils
from .utils import config, checks, data_type, token, modding
import aiohttp
import asyncio
import re
import html
from bs4 import BeautifulSoup as BS, NavigableString as NS
import json
from datetime import datetime, timedelta
import traceback
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
    "takt":         "Takt",
    "rear":         "Rear",
    "arm":          "Arm",
    "leg":          "Leg",
    "sub":          "Sub Unit"
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
    "takt":         "https://pso2.arks-visiphone.com/wiki/Simple_Takts_List"
}
WEAPON_SORT = tuple(WEAPON_URLS.keys())
SSA_SLOTS = {
    "Tier 2":               ["s1", "s2"],
    "Tier 3":               ["s1", "s2", "s3"],
    "Tier 4":               ["s1", "s2", "s3", "s4"],
    "S Class Ability 1":    ["s1"],
    "S Class Ability 2":    ["s2"],
    "S Class Ability 3":    ["s3"],
    "S Class Ability 4":    ["s4"]
}
DEF_EMOJIS = ("sdef", "rdef", "tdef")
RESIST_EMOJIS = ("s_res", "r_res", "t_res")
ELEMENTAL_RESIST_EMOJIS = ("fire_res", "ice_res", "lightning_res", "wind_res", "light_res", "dark_res")

OLD_LAYOUT_UNIT_URLS = {
    "rear":     "https://pso2.arks-visiphone.com/wiki/Unit_List:_Rear",
    "arm":      "https://pso2.arks-visiphone.com/wiki/Unit_List:_Arm",
    "leg":      "https://pso2.arks-visiphone.com/wiki/Unit_List:_Leg",
    "sub":      "https://pso2.arks-visiphone.com/wiki/Unit_List:_Sub"
}
NEW_LAYOUT_UNIT_URLS = {
    "rear":     "https://pso2.arks-visiphone.com/wiki/Rear_Units_List",
    "arm":      "https://pso2.arks-visiphone.com/wiki/Arm_Units_List",
    "leg":      "https://pso2.arks-visiphone.com/wiki/Leg_Units_List",
    "sub":      "https://pso2.arks-visiphone.com/wiki/Sub_Units_List"
}
UNIT_URLS = OLD_LAYOUT_UNIT_URLS

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

iso_time_regex = re.compile(r"([0-9]{4})\-([0-9]{2})\-([0-9]{2})T([0-9]{2})\:([0-9]{2})\:([0-9]{2}\.?[0-9]{0,6})(Z|[+-]([0-9]{2})\:([0-9]{2}))")

UNIT_FORMAT = {
    "S-ATK":            "satk",
    "R-ATK":            "ratk",
    "T-ATK":            "tatk",
    "DEX":              "dex",
    "Strike Resist":    "s_res",
    "Range Resist":     "r_res",
    "Tech Resist":      "t_res",
    "Fire Resist":      "fire_res",
    "Ice Resist":       "ice_res",
    "Lightning Resist": "lightning_res",
    "Wind Resist":      "wind_res",
    "Light Resist":     "light_res",
    "Dark Resist":      "dark_res"
}

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
        description = self.star_display(cog, self.rarity)
        if self.classes == "all_classes":
            usable_classes = "".join((str(emojis[cl]) for cl in CLASS_DICT.values()))
        else:
            usable_classes = "".join((str(emojis[cl]) for cl in self.classes))
        description = f"{description}\n{usable_classes}"
        if self.ssa_slots:
            slots = "".join((str(emojis[s]) for s in self.ssa_slots))
            embed.description = f"{description}\n**Slots:** {slots}"
        else:
            embed.description = description
        if self.pic_url:
            embed.set_thumbnail(url=self.pic_url)
        rq = self.requirement
        embed.add_field(name="Requirement", value=f"{emojis.get(rq['type'], '')}{rq['value']}" or "?")
        max_atk = self.atk["max"]
        embed.add_field(name="ATK", value="\n".join((f"{emojis[e]}{max_atk[e]}" for e in ATK_EMOJIS)))
        for prp in self.properties:
            embed.add_field(name=f"{emojis[prp['type']]}{prp['name']}", value=prp["description"], inline=False)
        return embed

    @staticmethod
    def star_display(cog, rarity):
        emojis = cog.emojis
        stars = []
        most = rarity//3
        for i in range(most):
            emoji = emojis.get(f"star_{i}", None)
            stars.extend((emoji, emoji, emoji))
        if rarity > most*3:
            emoji = emojis.get(f"star_{most}", None)
            for i in range(rarity - most*3):
                stars.append(emoji)
        return "".join((str(s) for s in stars))

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
        max_def = self.defs["max"]
        embed.add_field(name="DEF", value="\n".join((f"{emojis[e]}{max_def[e]}" for e in DEF_EMOJIS)))
        stats = self.stats
        stats_des = "\n".join((f"**{s.upper()}** + {stats[s]}" for s in ("hp", "pp") if stats.get(s)))
        embed.add_field(name="Stats", value=f"\n".join((stats_des, "\n".join((f"{emojis[s]}+ {stats[s]}" for s in ("satk", "ratk", "tatk", "dex") if stats.get(s))))).strip() or "None")
        resist = self.resist
        res_des = "\n".join((f"{emojis[e]}+ {resist[e]}%" for e in RESIST_EMOJIS if resist.get(e)))
        if res_des:
            embed.add_field(name="Resist", value=res_des)
        ele_res_des = "\n".join((f"{emojis[e]}+ {resist[e]}%" for e in ELEMENTAL_RESIST_EMOJIS if resist.get(e)))
        if ele_res_des:
            embed.add_field(name="Elemental resist", value=ele_res_des)
        return embed

#==================================================================================================================================================

class PSO2(commands.Cog):
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
            "pa", "saf", "star_0", "star_1", "star_2", "star_3", "star_4", "rappy"
        ):
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild.emojis)
        for emoji_name in WEAPON_SORT:
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild.emojis)
        for emoji_name in (
            "sdef", "rdef", "tdef", "dex", "rear", "arm", "leg", "sub", "s_res", "r_res", "t_res",
            "fire_res", "ice_res", "lightning_res", "wind_res", "light_res", "dark_res",
            "s_class", "s1", "s2", "s3", "s4"
        ):
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild_2.emojis)
        self.emojis["set_effect"] = self.emojis["rear"]
        self.last_eq_data = None
        self.api_data = {}
        self.eq_alert_forever = weakref.ref(bot.loop.create_task(self.eq_alert()))
        self.daily_order_pattern = bot.db.daily_order_pattern
        self.calendar = build("calendar", "v3", developerKey=token.GOOGLE_CLIENT_API_KEY)
        self.incoming_events = data_type.Observer()
        self.boost_remind_forever = weakref.ref(bot.loop.create_task(self.boost_remind()))

    def cog_unload(self):
        try:
            self.eq_alert_forever().cancel()
        except:
            traceback.print_exc()
        try:
            self.boost_remind_forever().cancel()
        except:
            traceback.print_exc()

    @commands.command(aliases=["c"])
    async def chip(self, ctx, *, name):
        '''
            `>>chip <name>`
            Display a PSO2es chip info.
            Chip name is case-insensitive and can be either EN or JP.
            I'm not maintaining this anymore.
        '''
        chip = await ctx.search(
            name, self.chip_library,
            cls=Chip, colour=discord.Colour.blue(),
            atts=["en_name", "jp_name"], name_att="en_name", emoji_att="element"
        )
        if not chip:
            return
        await ctx.send(embed=chip.embed_form(self))

    @modding.help(brief="Display weapon info", category="PSO2", field="Database", paragraph=0)
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
            atts=["en_name", "jp_name", "category"], name_att="en_name", emoji_att="category", sort={"category": WEAPON_SORT}
        )
        if not weapon:
            return
        await ctx.send(embed=weapon.embed_form(self))

    async def _search_att(self, attrs):
        result = []
        query = {}
        check_type = None
        projection = {"_id": False, "category": True, "en_name": True, "jp_name": True}
        special = None
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
                args_list = value.split()
                re_value = ".*?".join(map(re.escape, args_list))
                p = None
                if orig_att in ("properties", "affix", "abi", "ability", "potential", "pot", "latent", "pa", "saf", "s_class", "ssa_saf"):
                    p = {"properties": True}
                    if orig_att == "properties":
                        t = {"$exists": True}
                    elif orig_att in ("affix", "abi"):
                        t = "ability"
                    elif orig_att in ("pot", "latent"):
                        t = "potential"
                    elif orig_att in ("ssa_saf",):
                        t = "s_class"
                    else:
                        t = orig_att
                    special = t
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
                elif orig_att in ("ssa_slots", "slots", "slot", "classes", "class"):
                    if orig_att in ("ssa_slots", "slots", "slot"):
                        t = "ssa_slots"
                        q = {"$and": [{t: a} for a in args_list]}
                    elif orig_att in ("classes", "class"):
                        t = "classes"
                        q = {"$or": [{t: {"$all": args_list}}, {t: "all_classes"}]}
                    p = {t: True}
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
            ret = []
            for key, value in weapon.items():
                if key == "properties":
                    for v in value:
                        if v["type"] == special:
                            break
                    else:
                        continue
                    value = v
                    desc = f"{value['name']}\n{value['description']}"
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
                    if len(desc) > 200:
                        if key == "potential":
                            desc = f"{desc[:400]}"
                        elif key not in ("ssa_slots", "classes"):
                            desc = f"{desc[:200]}..."
                except:
                    pass
                if key == "properties":
                    ret.append(f"{self.emojis[value['type']]}{desc}")
                elif key in ("atk", "ssa_slots", "classes"):
                    ret.append(desc)
                elif key == "rarity":
                    icon = self.emojis[f"star_{(value-1)//3}"]
                    ret.append(f"`{value}` {icon}")
                else:
                    ret.append(f"{key}: {desc}")
            new_weapon["value"] = "\n".join(ret)
            result.append(new_weapon)
        return result

    @modding.help(brief="Search weapons with given conditions", category="PSO2", field="Database", paragraph=0)
    @cmd_weapon.command(name="filter")
    async def w_filter(self, ctx, *, data: modding.KeyValue()):
        '''
            `>>w filter <criteria>`
            Find all weapons with <criteria>.
            Criteria can contain multiple lines, each with format `<attribute>=<value>`.
            Available attributes:
            - en_name
            - jp_name
            - category (note: look for the weapon emojis' name)
            - rarity
            - atk
            - properties/potential(pot)/ability(abi)/pa/saf/s_class(ssa_saf)
            - classes(class)
            - ssa_slots(slots/slot)
        '''
        attrs = [(k.lower(), v.lower()) for k, v in data.items()]
        result = await self._search_att(attrs)
        if result:
            paging = utils.Paginator(
                result, 5, separator="\n\n",
                title=f"Search result: {len(result)} results",
                description=lambda i, x: f"{self.emojis[x['category']]}**{x['en_name']}**\n{x['value']}",
                colour=discord.Colour.blue()
            )
            await paging.navigate(ctx)
        else:
            await ctx.send("No result found.")

    def weapon_parse(self, category, bytes_):
        category_weapons = []
        soup = BS(bytes_.decode("utf-8"), "lxml")
        table = soup.find(lambda x: x.name=="table" and "wikitable" in x.get("class", []) and "sortable" in x.get("class", [])).find_all(True, recursive=False)[1:]
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
                        weapon["ssa_slots"].extend(SSA_SLOTS.get(a, ()))
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
            try:
                category_weapons = await self.bot.loop.run_in_executor(None, self.weapon_parse, category, bytes_)
            except:
                await ctx.send(f"Error parsing {CATEGORY_DICT[category]}.")
                raise
            else:
                weapons.extend(category_weapons)
        await self.weapon_list.delete_many({"category": {"$in": tuple(urls.keys())}})
        await self.weapon_list.insert_many(weapons)
        await msg.edit(content="Done.")

    @modding.help(brief="Search for items", category="PSO2", field="Database", paragraph=1)
    @commands.command(name="item", aliases=["i"])
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def cmd_item(self, ctx, *, data: modding.KeyValue(multiline=False, clean=False)):
        '''
            `>>item <name> <keyword: desc|description>`
            Find PSO2 items.
            Name given is case-insensitive, and can be either EN or JP.
            Description is used to filtered result.
        '''
        await ctx.trigger_typing()
        name = data.getall("", None)
        if not name:
            return await ctx.send("How do I find item without knowing its name?")
        name = " ".join(name)
        desc = data.geteither("description", "desc")
        params = {"name": name}
        bytes_ = await utils.fetch(self.bot.session, "http://db.kakia.org/item/search", params=params)
        result = json.loads(bytes_)
        if not result:
            return await ctx.send("Can't find any item with that name.")
        if desc:
            regex = re.compile(".*?".join((re.escape(w) for w in desc.split())), re.I)
            filtered = []
            for r in result:
                if regex.search(r["EnDesc"]):
                    filtered.append(r)
        else:
            filtered = result

        nl = "\n"
        paging = utils.Paginator(
            filtered, 5, separator="\n\n",
            title=f"Search result: {len(filtered)} results",
            description=lambda i, x: f"**EN:** {x['EnName']}\n**JP:** {utils.unifix(x['JpName'])}\n{x['EnDesc'].replace(nl, ' ')}",
            colour=discord.Colour.blue()
        )
        await paging.navigate(ctx)

    @modding.help(brief="Check item price", category="PSO2", field="Database", paragraph=1)
    @commands.command(name="price")
    async def cmd_price(self, ctx, *, name):
        '''
            `>>price <name>`
            Check the price of an item.
            Quite outdated, better just go ingame.
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

    async def check_for_new_version(self):
        bytes_ = await self.bot.fetch(
            "https://pso2.acf.me.uk/PSO2Alert/PSO2Alert.json",
            headers={
                "User-Agent": "PSO2.Alert.v3.0.6.3",
                "Connection": "Keep-Alive",
                "Host": "pso2.acf.me.uk"
            }
        )
        data = json.loads(bytes_)[0]
        self.api_data["version"] = data["Version"]
        self.api_data["url"] = data["EQAPI"]
        self.api_data["headers"] = {"User-Agent": f"PSO2.Alert.v{data['Version']} you_thought_its_eq_alert_but_its_actually_me_nguuuquaaa", "Host": "pso2.acf.me.uk"}

    async def eq_alert(self):
        _loop = self.bot.loop
        async def try_it(coro):
            try:
                await coro
            except:
                pass
        try:
            await self.check_for_new_version()
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
                bytes_ = await self.bot.fetch(self.api_data["url"], headers=self.api_data["headers"])
                data = json.loads(bytes_)[0]
                self.last_eq_data = data
                now_time = utils.now_time(utils.jp_timezone)
                jst = int(data["JST"])
                start_time = now_time.replace(minute=0, second=0) + timedelta(hours=jst-1-now_time.hour)
                full_desc = []
                simple_desc = []
                ship_gen = (f"Ship{ship_number}" for ship_number in range(1, 11))
                random_eq = "\n".join((f"`Ship {ship[4:]}:` {data[ship]}" for ship in ship_gen if data[ship]))

                for index, key in enumerate(TIME_LEFT):
                    if data[key]:
                        sched_time = start_time + timedelta(minutes=30*index)
                        time_left = int(round((sched_time - now_time).total_seconds(), -1))
                        if time_left == 0:
                            full_desc.append(f"\u2694 **Now**\n`All ships:` {data[key]}")
                        elif time_left > 0:
                            if time_left in (900, 2700, 6300, 9900):
                                text = f"\u23f0 **In {utils.seconds_to_text(time_left)}:**\n`All ships:` {data[key]}"
                                full_desc.append(text)
                                if time_left in (2700, 6300):
                                    simple_desc.append(text)
                    if index == 2:
                        if random_eq:
                            sched_time = start_time + timedelta(hours=1)
                            time_left = int(round((sched_time - now_time).total_seconds(), -1))
                            if time_left == 0:
                                full_desc.append(f"\u2694 **Now:**\n{random_eq}")
                            elif time_left > 0:
                                if time_left in (900, 2700, 6300, 9900):
                                    req_text = f"\u23f0 **In {utils.seconds_to_text(time_left)}:**\n{random_eq}"
                                    full_desc.append(req_text)
                                    if time_left in (2700, 6300):
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
        except (ConnectionError, json.JSONDecodeError):
            await asyncio.sleep(60)
            self.eq_alert_forever = weakref.ref(_loop.create_task(self.eq_alert()))
        except:
            await self.bot.error_hook.execute(f"```\n{traceback.format_exc()}\n```")

    def get_emoji(self, dt_obj):
        if dt_obj.minute == 0:
            m = ""
        else:
            m = 30
        h = dt_obj.hour % 12
        if h == 0:
            h = 12
        return f":clock{h}{m}:"

    @modding.help(brief="Display EQ schedule for the next 3 hours", category="PSO2", field="EQ", paragraph=0)
    @commands.command(name="eq")
    async def nexteq(self, ctx):
        '''
            `>>eq`
            Display eq schedule for the next 3 hours.
        '''
        if not self.last_eq_data:
            bytes_ = await self.bot.fetch(self.api_data["url"], headers=self.api_data["headers"])
            self.last_eq_data = json.loads(bytes_)[0]
        data = self.last_eq_data
        now_time = utils.now_time(utils.jp_timezone)
        jst = int(data["JST"])
        start_time = now_time.replace(minute=0, second=0) + timedelta(hours=jst-1-now_time.hour)
        ship_gen = (f"Ship{ship_number}" for ship_number in range(1, 11))
        random_eq = "\n".join((f"`Ship {ship[4:]}:` {data[ship]}" for ship in ship_gen if data[ship]))
        sched_eq = []
        for index, key in enumerate(TIME_LEFT):
            if data[key]:
                sched_time = start_time + timedelta(minutes=30*index)
                wait_time = (int((sched_time-now_time).total_seconds())//60) * 60
                if wait_time < 0:
                    sched_eq.append(f"{self.get_emoji(sched_time)} **At {sched_time.strftime('%I:%M %p')}**\n{data[key]}")
                else:
                    sched_eq.append(f"{self.get_emoji(sched_time)} **In {utils.seconds_to_text(wait_time)}**\n{data[key]}")

        embed = discord.Embed(colour=discord.Colour.red())
        embed.set_footer(text=utils.jp_time(now_time))
        if random_eq or sched_eq:
            if random_eq:
                sched_time = start_time + timedelta(hours=1)
                wait_time = (int((sched_time-now_time).total_seconds())//60) * 60
                if wait_time <= 0:
                    embed.add_field(name="Random EQ", value=f"{self.get_emoji(sched_time)} **At {sched_time.strftime('%I:%M %p')}**\n{random_eq}", inline=False)
                else:
                    embed.add_field(name="Random EQ", value=f"{self.get_emoji(sched_time)} **In {utils.seconds_to_text(wait_time)}**\n{random_eq}", inline=False)
            if sched_eq:
                embed.add_field(name="Schedule EQ", value="\n\n".join(sched_eq), inline=False)
        else:
            embed.description = "There's no EQ for the next 3 hours."
        await ctx.send(embed=embed)

    @modding.help(brief="Display unit info", category="PSO2", field="Database", paragraph=0)
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
            atts=["en_name", "jp_name", "category"], name_att="en_name", emoji_att="category"
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
            try:
                category_units = await self.bot.loop.run_in_executor(None, self.unit_parse, category, bytes_)
            except:
                await ctx.send(f"Error parsing {CATEGORY_DICT[category]}.")
                raise
            else:
                units.extend(category_units)
        await self.unit_list.delete_many({"category": {"$in": tuple(urls.keys())}})
        await self.unit_list.insert_many(units)
        print("Done everything.")
        await msg.edit(content = "Done.")

    def unit_parse(self, category, bytes_):
        category_units = []
        soup = BS(bytes_.decode("utf-8"), "lxml")

        if True: #category == "sub":
            table = soup.find("table", class_="sortable").find_all(True, recursive=False)[3:]
            for item in table:
                unit = {"category": category}
                relevant = item.find_all(True, recursive=False)
                third_column = relevant[2]
                try:
                    unit["en_name"] = utils.unifix(third_column.find("a").get_text())
                    unit["jp_name"] = utils.unifix("".join((t.get_text() for t in third_column.find_all("span", style="font-size:75%"))))
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
                    "base": {DEF_EMOJIS[i]: 0 for i in range(3)},
                    "max":  {DEF_EMOJIS[i]: utils.to_int(relevant[10+i].get_text().strip(), default=0) for i in range(3)}
                }
                unit["stats"] = {}
                for i, s in enumerate(("hp", "pp", "satk", "ratk", "tatk", "dex")):
                    unit["stats"][s] = utils.to_int(relevant[4+i].get_text().strip(), default=0)
                unit["resist"] = {}
                for i, s in enumerate(RESIST_EMOJIS):
                    unit["resist"][s] = utils.to_int(relevant[13+i].get_text().replace("%", "").strip(), default=0)
                ele_res_tag = relevant[16].find_all("td")
                for i, s in enumerate(ELEMENTAL_RESIST_EMOJIS):
                    unit["resist"][s] = utils.to_int(ele_res_tag[i].get_text().replace("%", "").strip(), default=0)
                category_units.append(unit)
            return category_units
        else:
            table = soup.find(lambda x: x.name=="table" and "wikitable" in x.get("class", []) and "sortable" in x.get("class", [])).find_all(True, recursive=False)[2:]
            for item in table:
                unit = {"category": category}
                relevant = item.find_all(True, recursive=False)
                third_column = relevant[2]
                try:
                    unit["en_name"] = utils.unifix(third_column.find("a").get_text())
                    unit["jp_name"] = utils.unifix(third_column.find("p").get_text())
                except:
                    continue
                unit["rarity"] = utils.to_int(relevant[0].find("img")["alt"])
                try:
                    unit["pic_url"] = f"https://pso2.arks-visiphone.com{relevant[1].find('img')['src'].replace('64px-', '96px-')}"
                except:
                    unit["pic_url"] = None
                rq = utils.unifix(relevant[3].text).partition(" ")
                unit["requirement"] = {"type": rq[2].replace("-", "").lower(), "value": rq[0]}
                unit["defs"] = {
                    "base": {DEF_EMOJIS[i]: utils.to_int(l.strip()) for i, l in enumerate(relevant[5].find_all(text=True))},
                    "max":  {DEF_EMOJIS[i]: utils.to_int(l.strip()) for i, l in enumerate(relevant[6].find_all(text=True))}
                }

                unit["stats"] = {}
                unit["resist"] = {}
                tn = None
                for tag in relevant[7].children:
                    if tag.name == "br":
                        continue
                    elif tag.name == "img":
                        tn = UNIT_FORMAT[tag["alt"]]
                    elif tag:
                        if tn is None:
                            stat, delim, value = tag.lower().partition("+")
                            unit["stats"][utils.unifix(stat)] = utils.to_int(value.strip())
                        else:
                            value = tag.replace("+", "").replace("%", "").strip()
                            if tn in ATK_EMOJIS:
                                unit["stats"][tn] = value
                            else:
                                unit["resist"][tn] = value
                            tn = None

                category_units.append(unit)
            return category_units

    @modding.help(brief="Display daily orders/featured quests", category="PSO2", field="EQ", paragraph=0)
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
            title = item["summary"].lower()
            if "pso2 day" in title:
                item["boost_type"] = "rappy"
            elif "arks league" in title:
                item["boost_type"] = "league"
            elif "eq" in title:
                item["boost_type"] = "eq"
            elif "boost" in title:
                item["boost_type"] = "casino"
            else:
                item["boost_type"] = None
                continue
            results.append(item)
        results.sort(key=lambda x: x["start"]["dateTime"])
        return results

    async def update_events(self):
        events = await self.bot.loop.run_in_executor(None, self.get_calendar_events, "pso2emgquest@gmail.com")
        self.incoming_events.assign(events)

    @modding.help(brief="Display current week's boost events", category="PSO2", field="EQ", paragraph=0)
    @commands.group(name="boost")
    async def cmd_boost(self, ctx):
        '''
            `>>boost`
            Display current week's casino boost, PSO2 Day and ARKS League.
        '''
        if ctx.invoked_subcommand is None:
            def process_date(i, x):
                start_date = iso_time_regex.fullmatch(x["start"]["dateTime"])
                end_date = iso_time_regex.fullmatch(x["end"]["dateTime"])
                txt = \
                    f"From {start_date.group(4)}:{start_date.group(5)}, {start_date.group(3)}-{start_date.group(2)}\n" \
                    f"To {end_date.group(4)}:{end_date.group(5)}, {end_date.group(3)}-{end_date.group(2)}"
                return x["summary"], txt, False

            events = self.incoming_events.item
            if events:
                paging = utils.Paginator(
                    events, 5, separator="\n\n",
                    title="Boosto",
                    fields=process_date,
                    footer=utils.jp_time(utils.now_time())
                )
                await paging.navigate(ctx)
            else:
                await ctx.send("No more event until the end of this week, oof.")

    @cmd_boost.command(name="update", hidden=True)
    @checks.owner_only()
    async def cmd_boost_update(self, ctx):
        await self.update_events()
        await ctx.confirm()

    async def boost_remind(self):
        if not self.incoming_events:
            await self.update_events()

        while True:
            self.incoming_events.clear()
            now_time = utils.now_time(utils.jp_timezone)
            if self.incoming_events:
                next_event = self.incoming_events.item[0]

                start_date = iso_time_regex.fullmatch(next_event["start"]["dateTime"])
                end_date = iso_time_regex.fullmatch(next_event["end"]["dateTime"])
                marks = []
                for d in (start_date, end_date):
                    marks.append(utils.jp_timezone.localize(datetime(
                        int(d.group(1)), int(d.group(2)), int(d.group(3)),
                        int(d.group(4)), int(d.group(5))
                    )))
                start_time, end_time = marks
                period = int((end_time - start_time).total_seconds())
                wait_time = (start_time - now_time).total_seconds()
                if wait_time > 2700:
                    try:
                        await asyncio.wait_for(self.incoming_events.wait(), wait_time-2700)
                    except asyncio.TimeoutError:
                        pass
                    else:
                        continue
                else: #if wait_time < 0:
                    self.incoming_events.call("pop", 0)
                    continue

                now_time = utils.now_time(utils.jp_timezone)
                embed = discord.Embed(
                    title="(Not) EQ Alert",
                    colour=discord.Colour.red()
                )
                boost_type = next_event["boost_type"]
                if boost_type == "rappy":
                    embed.description = f"{self.emojis['rappy']} **{next_event['summary']}**"
                    embed.set_image(url="https://i.imgur.com/FV7a52s.jpg")
                elif boost_type == "league":
                    embed.description = f"\U0001f3c6 **In 45 minutes:**\n`[{utils.seconds_to_text(period)}]` {next_event['summary']}"
                elif boost_type == "casino":
                    embed.description = f"\U0001f3b0 **In 45 minutes:**\n`[{utils.seconds_to_text(period)}]` {next_event['summary']}"
                elif boost_type == "eq":
                    embed.description = f"\u2694 **In 45 minutes:**\n{next_event['summary']}"
                else:
                    embed.description = f"\u2753 **In 45 minutes:**\n`[{utils.seconds_to_text(period)}]` {next_event['summary']}"
                embed.set_footer(text=utils.jp_time(now_time))

                async for gd in self.guild_data.find(
                    {"eq_channel_id": {"$exists": True}},
                    projection={"_id": False, "eq_channel_id": True}
                ):
                    channel = self.bot.get_channel(gd["eq_channel_id"])
                    if channel:
                        self.bot.loop.create_task(channel.send(embed=embed))
                self.incoming_events.call("pop", 0)
            else:
                days_ahead = (2 - now_time.weekday()) % 7
                next_time = (now_time + timedelta(days=days_ahead)).replace(hour=17, minute=0, second=0)
                wait_time = (next_time - now_time).total_seconds() % (86400 * 7)
                try:
                    await asyncio.wait_for(self.incoming_events.wait(), wait_time)
                except asyncio.TimeoutError:
                    await self.update_events()
                else:
                    continue

    @modding.help(brief="ARKS language", category="PSO2", field="Database", paragraph=1)
    @commands.command(aliases=["pt"])
    async def pso2text(self, ctx, *, text):
        '''
            `>>pso2text <text>`
            You play PSO2, you know ARKS language.
            Send an image with text written in ARKS language.
        '''
        if len(text) > 50:
            return await ctx.send("Text too long.")
        for c in text:
            if c.isalnum() or c in "!%&*+;:/?., '-":
                continue
            else:
                return await ctx.send(f"Text contains unaccepted character {c}")
        font = ImageFont.truetype(f"{config.DATA_PATH}/font/pso2_font.ttf", size=30)
        x, y = font.getsize(text)
        image = Image.new("RGBA", (x+6, y+6), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        draw.text((3, 3), text, font=font, fill=(255, 255, 255, 255))
        b = BytesIO()
        image.save(b, "png")
        await ctx.send(file=discord.File(b.getvalue(), "pso2.png"))

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(PSO2(bot))
