import discord
from discord.ext import commands
from . import utils
from .utils import data_type, wiki, checks, config, modding, token
import json
from bs4 import BeautifulSoup as BS
import re
import json
import traceback
from urllib.parse import quote
import hashlib

#==================================================================================================================================================

INF = float("inf")

GFWIKI_BASE = "https://iopwiki.com"
GFWIKI_API = f"{GFWIKI_BASE}/api.php"

GFLANALYSIS_BASE = "https://www.gflanalysis.com"
GFLANALYSIS_API = f"{GFLANALYSIS_BASE}/w/api.php"

MOBILITY = {
    "AR":   10,
    "SMG":  12,
    "HG":   15,
    "RF":   7,
    "MG":   4,
    "SG":   6
}

CRIT_RATE = {
    "AR":   20,
    "SMG":  5,
    "HG":   20,
    "RF":   40,
    "MG":   5,
    "SG":   20
}

AMMO_COST = {
    "AR":   (20, 60),
    "SMG":  (30, 90),
    "HG":   (10, 30),
    "RF":   (30, 90),
    "MG":   (40, 140),
    "SG":   (30, 90)
}

RATION_COST = {
    "AR":   (20, 60),
    "SMG":  (20, 60),
    "HG":   (10, 30),
    "RF":   (15, 55),
    "MG":   (30, 90),
    "SG":   (40, 140)
}

ARMOR_PENETRATION = 15

STANDARD_EQUIPMENTS = {
    "AR": {
        "accessory": ["telescopic_sight", "red_dot_sight", "holographic_sight", "silencer", "night_equipment"],
        "magazine": ["hv_ammo"],
        "doll": ["exoskeleton", "chip"]
    },
    "SMG": {
        "accessory": ["telescopic_sight", "red_dot_sight", "holographic_sight", "silencer", "night_equipment"],
        "magazine": ["hp_ammo"],
        "doll": ["exoskeleton", "chip"]
    },
    "HG": {
        "accessory": ["silencer", "night_equipment"],
        "magazine": ["hp_ammo"],
        "doll": ["exoskeleton", "chip"]
    },
    "RF": {
        "accessory": ["telescopic_sight", "red_dot_sight", "holographic_sight", "silencer"],
        "magazine": ["ap_ammo"],
        "doll": ["camo_cape", "chip"]
    },
    "MG": {
        "accessory": ["telescopic_sight", "red_dot_sight", "holographic_sight"],
        "magazine": ["ap_ammo"],
        "doll": ["ammo_box", "chip"]
    },
    "SG": {
        "accessory": ["telescopic_sight", "red_dot_sight", "holographic_sight", "night_equipment"],
        "magazine": ["shotgun_ammo"],
        "doll": ["armor_plate", "chip"]
    },
}

EQUIPMENT_ORDER = {
    "AR": ["accessory", "magazine", "doll"],
    "SMG": ["doll", "magazine", "accessory"],
    "HG": ["accessory", "magazine", "doll"],
    "RF": ["magazine", "accessory", "doll"],
    "MG": ["magazine", "accessory", "doll"],
    "SG": ["doll", "magazine", "accessory"]
}

MOD_RARITY = {
    "2": 4,
    "3": 4,
    "4": 5,
    "5": 6
}

STATS_NORMALIZE = {
    "clipsize":                 "clip_size",
    "nightpenaltyreduction":    "peq",
    "criticaldamage":           "crit_dmg",
    "criticalhitdamage":        "crit_dmg",
    "armorpiercing":            "armor_penetration",
    "armorpenetration":         "armor_penetration",
    "armourpenetration":        "armor_penetration", 
    "armourpiercing":           "armor_penetration",
    "evasion":                  "evasion",
    "criticalhitrate":          "crit_rate",
    "criticalhitchance":        "crit_rate",
    "targets":                  "shotgun_ammo",
    "rateoffire":               "rof",
    "accuracy":                 "accuracy",
    "armor":                    "armor",
    "armour":                   "armor",
    "movementspeed":            "mobility",
    "damage":                   "damage",
    "boostabilityeffectiveness":"boost_skill_effect"
}

STAT_DISPLAY = {
    "damage":               ("DMG", ""),
    "rof":                  ("ROF", ""),
    "accuracy":             ("ACC", ""),
    "evasion":              ("EVA", ""),
    "crit_rate":            ("CRIT RATE", "%"),
    "crit_dmg":             ("CRIT DMG", "%"),
    "armor":                ("ARMOR", ""),
    "clip_size":            ("ROUNDS", ""),
    "armor_penetration":    ("AP", ""),
    "mobility":             ("MOBILITY", ""),
    "peq":                  ("NIGHT VISION", "%"),
    "shotgun_ammo":         ("TARGETS", "")
}

def get_equipment_slots(classification, order, *, add_ap=False, add_armor=False):
    eq = STANDARD_EQUIPMENTS[classification]
    ret = []
    for i in order:
        if add_ap and i == "magazine":
            e = eq[i] + ["ap_ammo"]
        elif add_armor and i == "doll":
            e = eq[i] + ["armor_plate"]
        else:
            e = eq[i]
        ret.append(e)
    return ret

wiki_timer_regex = re.compile(r"(\d{1,2})\:(\d{2})\:(\d{2})")
def timer_to_seconds(s):
    m = wiki_timer_regex.match(s)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60
    else:
        return None

timer_regex = re.compile(r"(\d{0,2})\:?(\d{2})")

def circle_iter(iterable, with_index=False):
    if iterable:
        if with_index:
            while True:
                for i, item in enumerate(iterable):
                    yield i, item
        else:
            while True:
                for item in iterable:
                    yield item
    else:
        raise ValueError("Cannot circle-iterate empty container.")

def get_either(container, *keys, default=None):
    for key in keys:
        try:
            return container[key]
        except (IndexError, KeyError):
            pass
    else:
        return default

def mod_keys(key):
    return "mod3_" + key, "mod2_" + key, "mod1_" + key, key

name_clean_regex = re.compile(r"[\.\-\s\/]")

def normalize(s):
    return s.replace("\u2215", "/")

shorten_regex = re.compile(r"(submachine\s?gun|assault\s?rifle|rifle|hand\s?gun|machine\sgun|shotgun)s?\s*(?:\(\w{2,3}\))?", re.I)
def shorten_repl(m):
    base = m.group(1).lower()
    if base.startswith("sub"):
        return "SMG"
    elif base.startswith("assault"):
        return "AR"
    elif base.startswith("hand"):
        return "HG"
    elif base.startswith("machine"):
        return "MG"
    elif base.startswith("rifle"):
        return "RF"
    elif base.startswith("shot"):
        return "SG"
    else:
        return m.group(0)

def shorten_types(text):
    return shorten_regex.sub(shorten_repl, text)

def to_float(any_obj, *, default=None):
    try:
        return float(any_obj)
    except:
        return default

def generate_image_url(filename, *, base=GFWIKI_BASE):
    filename = filename.replace(" ", "_")
    name_hash = hashlib.md5(filename.encode("utf-8")).hexdigest()
    return f"{base}/images/{name_hash[0]}/{name_hash[:2]}/{filename}"

#==================================================================================================================================================

parser = wiki.WikitextParser()

@parser.set_box_handler("PlayableUnit")
@parser.set_box_handler("Equipment")
@parser.set_box_handler("Fairy")
def handle_base_box(box, **kwargs):
    return kwargs

@parser.set_box_handler("voice actor name")
@parser.set_box_handler("artist name")
@parser.set_box_handler("icon")
def handle_creator(box, name):
    return name

@parser.set_box_handler("doll_server_alias")
def handle_alias(box, *, server, alias):
    if server == "EN":
        return alias
    else:
        return ""

@parser.set_box_handler("doll name")
@parser.set_box_handler("equip name")
@parser.set_box_handler("enemy name")
@parser.set_box_handler("fairy name")
def handle_name(box, name, *args, **kwargs):
    return name

@parser.set_box_handler("HG aura")
@parser.set_box_handler("HG_aura")
def handle_hg_aura(box, value):
    return value + "%"

@parser.set_box_handler("spoiler")
def handle_spoiler(box, value):
    return f"||{value}||"

@parser.set_box_handler("cite")
@parser.set_box_handler("cite ab1")
@parser.set_box_handler("stub")
@parser.set_box_handler("wip")
@parser.set_box_handler("Cleanup")
def handle_misc(box, *args, **kwargs):
    return ""

@parser.set_box_handler(None)
def default_handler(box, *args, **kwargs):
    raise ValueError(f"Handler for {box} doesn't exist.")

@parser.set_reference_handler
def handle_reference(box, *args, **kwargs):
    if box.startswith(":Category:"):
        return box[10:]
    else:
        return box

@parser.set_html_handler
def handle_html(tag, text, **kwargs):
    if tag == "ref":
        return ""
    elif kwargs.get("class") == "spoiler":
        return "||" + "".join(parser.parse(text)) + "||"
    else:
        return text

def maybe_int(nstr, default=0):
    try:
        n = float(nstr)
    except (ValueError, TypeError):
        return default
    else:
        intn = int(n)
        if n - intn == 0:
            return intn
        else:
            return n

skill_regex = re.compile(r"\(\$(\w+)\)")
simple_br_regex = re.compile(r"\<br\s*\/\>")
@parser.set_table_handler("gf-table")
def handle_skill_table(class_, table):
    parsed = {r[0]: r[1:] for r in table}
    effect = skill_regex.sub(lambda m: parsed[m.group(1)][9], parsed["text"][-1])
    effect = simple_br_regex.sub(lambda m: "\n", effect)
    return {
        "name": parsed["name"][-1],
        "effect": effect,
        "icd": maybe_int(parsed.get("initial", [None])[-1]),
        "cd": maybe_int(parsed.get("cooldown", [None])[-1])
    }

#==================================================================================================================================================

gflanalysis_parser = wiki.WikitextParser()

@gflanalysis_parser.set_html_handler
def handle_gfla_html(tag, text, **kwargs):
    if tag == "sup":
        return ""
    else:
        return text

@gflanalysis_parser.set_reference_handler
def handle_gfla_reference(box, *args, **kwargs):
    if box.startswith("Category:"):
        return ""
    else:
        return box

#==================================================================================================================================================

class Doll(data_type.BaseObject):
    @property
    def qual_name(self):
        return self.en_name or self.name

    def _base_info(self, ctx):
        emojis = ctx.cog.emojis
        embeds = []
        for skill_effect in utils.split_page(self.skill["effect"], 900, check=lambda s: s=="\n", fix=" \u27a1 "):
            embed = discord.Embed(
                title=f"#{self.index} {self.en_name or self.name}",
                color=discord.Color.green(),
                url=f"{GFWIKI_BASE}/wiki/{quote(self.name)}"
            )
            embed.add_field(name="Classification", value=f"{emojis[self.classification]} **{self.classification}**")
            embed.add_field(name="Rarity", value=str(emojis["rank"])*utils.to_int(self.rarity, default=0) or "**EXTRA**")
            embed.add_field(
                name="Production time",
                value=f"{self.craft_time//3600}:{self.craft_time%3600//60:0>2d}" if self.craft_time else "Non-craftable",
                inline=False
            )

            embed.add_field(
                name="Stats",
                value=
                    f"{emojis['hp']}**HP:** {self.max_hp} (x5)\n"
                    f"{emojis['damage']}**DMG:** {self.max_dmg}\n"
                    f"{emojis['accuracy']}**ACC:** {self.max_acc}"
                    +
                    (f"\n{emojis['armor']}**ARMOR:**  {self.max_armor}" if self.max_armor > 0 else "")
            )
            embed.add_field(
                name="\u200b",
                value=
                    f"{emojis['rof']}**ROF:** {self.max_rof}\n"
                    f"{emojis['evasion']}**EVA:** {self.max_eva}\n"
                    f"{emojis['crit_rate']}**CRIT RATE:** {self.crit_rate}%"
                    +
                    (f"\n{emojis['clip_size']}**ROUNDS:** {self.clip_size}" if self.clip_size > 0 else "")
            )

            tile = {
                k: emojis["blue_square"] if v==1 else emojis["white_square"] if v==0 else emojis["black_square"]
                for k, v in self.tile["shape"].items()
            }

            embed.add_field(
                name="Tile",
                value=
                    f"\u200b {tile['7']}{tile['8']}{tile['9']}\u2001{shorten_types(self.tile['target'])}\n"
                    f"\u200b {tile['4']}{tile['5']}{tile['6']}\u2001{self.tile['effect'][0]}\n"
                    f"\u200b {tile['1']}{tile['2']}{tile['3']}\u2001{self.tile['effect'][1]}",
                inline=False
            )

            skill = self.skill
            icd = f"Initial CD: {skill['icd']}s" if skill["icd"] else None
            cd = f"CD: {skill['cd']}s" if skill["cd"] else None
            if cd or icd:
                add = " (" + "/".join(filter(None, (icd, cd))) + ")"
            else:
                add = ""

            embed.add_field(
                name="Skill",
                value=
                    f"**{skill['name']}**{add}\n"
                    f"{skill_effect}",
                inline=False
            )
            embeds.append(embed)

        return embeds

    def _other_info(self, ctx):
        embeds = []
        for trivia in utils.split_page(self.trivia, 1000, check=lambda s: s=="\n", fix=" \u27a1 "):
            embed = discord.Embed(
                title=f"#{self.index} {self.en_name or self.name}",
                color=discord.Color.green(),
                url=f"{GFWIKI_BASE}/wiki/{quote(self.name)}"
            )
            embed.add_field(name="Full name", value=self.full_name)
            embed.add_field(name="Origin", value=self.origin)
            embed.add_field(name="Illustrator", value=self.artist)
            embed.add_field(name="Voice Actor", value=self.voice_actor or "None")
            embed.add_field(name="Trivia", value=trivia or "None", inline=False)
            embeds.append(embed)

        return embeds

    def _mod_info(self, ctx):
        emojis = ctx.cog.emojis
        mod = self.mod_data

        embeds = []
        for skill_index in range(2):
            for i, skill_effect in enumerate(utils.split_page(mod["skill"][skill_index]["effect"], 1000, check=lambda s:s=="\n", fix=" \u27a1 ")):
                while i > len(embeds) - 1:
                    embed = discord.Embed(
                        title=f"#{self.index} {self.en_name or self.name} Mod",
                        color=discord.Color.green(),
                        url=f"{GFWIKI_BASE}/wiki/{quote(self.name)}"
                    )
                    embed.add_field(name="Classification", value=f"{emojis[self.classification]} **{self.classification}**")
                    embed.add_field(name="Rarity", value=str(emojis["rank"])*MOD_RARITY[self.rarity])
                    embed.add_field(
                        name="Production time",
                        value=f"{self.craft_time//3600}:{self.craft_time%3600//60:0>2d}" if self.craft_time else "Non-craftable",
                        inline=False
                    )

                    embed.add_field(
                        name="Stats",
                        value=
                            f"{emojis['hp']}**HP:** {mod['max_hp']} (x5)\n"
                            f"{emojis['damage']}**DMG:** {mod['max_dmg']}\n"
                            f"{emojis['accuracy']}**ACC:** {mod['max_acc']}"
                            +
                            (f"\n{emojis['armor']}**ARMOR:**  {mod['max_armor']}" if mod["max_armor"] > 0 else "")
                    )
                    embed.add_field(
                        name="\u200b",
                        value=
                            f"{emojis['rof']}**ROF:** {mod['max_rof']}\n"
                            f"{emojis['evasion']}**EVA:** {mod['max_eva']}\n"
                            f"{emojis['crit_rate']}**CRIT RATE:** {self.crit_rate}%"
                            +
                            (f"\n{emojis['clip_size']}**ROUNDS:** {mod['clip_size']}" if mod["clip_size"] > 0 else "")
                    )

                    tile = {
                        k: emojis["blue_square"] if v==1 else emojis["white_square"] if v==0 else emojis["black_square"]
                        for k, v in mod["tile"]["shape"].items()
                    }

                    embed.add_field(
                        name="Tile",
                        value=
                            f"\u200b {tile['7']}{tile['8']}{tile['9']}\u2001{shorten_types(mod['tile']['target'])}\n"
                            f"\u200b {tile['4']}{tile['5']}{tile['6']}\u2001{mod['tile']['effect'][0]}\n"
                            f"\u200b {tile['1']}{tile['2']}{tile['3']}\u2001{mod['tile']['effect'][1]}",
                        inline=False
                    )
                    embeds.append(embed)

                cur = embeds[i]
                skill = mod["skill"][skill_index]
                icd = f"Initial CD: {skill['icd']}s" if skill["icd"] else None
                cd = f"CD: {skill['cd']}s" if skill["cd"] else None
                if cd or icd:
                    add = " (" + "/".join(filter(None, (icd, cd))) + ")"
                else:
                    add = ""

                cur.add_field(
                    name=f"Skill {skill_index+1}",
                    value=
                        f"**{skill['name']}**{add}\n"
                        f"{skill_effect}",
                    inline=False
                )

        return embeds

    async def display_info(self, ctx):
        emojis = ctx.cog.emojis
        paging = utils.Paginator([])
        base_info = self._base_info(ctx)
        other_info = self._other_info(ctx)
        skins = self.skins
        analysis = {}
        speq_info = await self.query_speq(ctx)

        saved = {
            "info": None,
            "info_iter": None,
            "skins": None,
            "skin_iter": None,
            "current_skin": (None, None)
        }

        def add_image():
            index, skin = saved["current_skin"]
            if index is None:
                saved["embed"].set_image(url=config.NO_IMG)
                saved["embed"].set_footer(text=discord.Embed.Empty)
            else:
                saved["embed"].set_footer(text=f"Skin: {skin['name']} ({skin['form']}) - ({index+1}/{len(saved['skins'])})")
                saved["embed"].set_image(url=skin["image_url"])

        def change_info_to(info, skins, state="original"):
            if saved["info"] is not info:
                saved["info"] = info
                saved["info_iter"] = circle_iter(info)
            if saved["skins"] is not skins:
                saved["skins"] = skins
                saved["skin_iter"] = circle_iter(skins, with_index=True)
                try:
                    saved["current_skin"] = next(saved["skin_iter"])
                except ValueError:
                    saved["current_skin"] = (None, None)
            saved["embed"] = next(saved["info_iter"])
            saved["state"] = state
            add_image()

        @paging.wrap_action(emojis["damage"])
        def change_base_info():
            change_info_to(base_info, skins)
            return saved["embed"]

        @paging.wrap_action("\U0001f5d2")
        def change_other_info():
            change_info_to(other_info, skins)
            return saved["embed"]

        if self.moddable:
            mod_info = self._mod_info(ctx)
            mod_skins = self.mod_data["skins"]

            @paging.wrap_action(emojis["mem_frag"])
            def change_mod3_info():
                change_info_to(mod_info, mod_skins, "mod")
                return saved["embed"]

        if speq_info["equipments"]:
            speq_iter = circle_iter(speq_info["equipments"])

            @paging.wrap_action(emojis["exoskeleton"])
            def change_speq_info():
                return next(speq_iter)

            digest_iter = circle_iter(speq_info["digest"])
            @paging.wrap_action("\U0001f52c")
            def change_digest_info():
                return next(digest_iter)

        @paging.wrap_action("\U0001f50e")
        async def change_analysis_info():
            if not analysis:
                analysis.update(await self.query_gflanalysis(ctx))
            if "mod" in analysis:
                state = saved["state"]
            else:
                state = "original"
            analysis_info = analysis[state]
            analysis_skins = mod_skins if state == "mod" else skins
            change_info_to(analysis_info, analysis_skins, state)
            return saved["embed"]

        @paging.wrap_action("\U0001f5bc")
        def change_image():
            saved["current_skin"] = next(saved["skin_iter"])
            add_image()
            return saved["embed"]

        await paging.navigate(ctx)

    async def query_gflanalysis(self, ctx):
        bytes_ = await ctx.bot.fetch(
            GFLANALYSIS_API,
            params={
                "action":       "ask",
                "query":        f"[[Name::~*{self.en_name}*]]|?Name|?Pros|?Cons|?Status|?Roles|?Analysis",
                "format":       "json",
                "redirects":    1
            }
        )
        data = json.loads(bytes_)

        results = data["query"]["results"]
        ret = {}
        if results:
            for name, raw in results.items():
                embeds = []

                if name == self.en_name:
                    ret["original"] = embeds
                elif name == f"{self.en_name}Mod":
                    ret["mod"] = embeds
                else:
                    continue

                pr = raw["printouts"]
                analysis = "".join(gflanalysis_parser.parse("\n".join(pr["Analysis"]).replace("&#8203;", "\n")))
                for a in utils.split_page(analysis, 900, check=lambda s: s=="\n", fix=" \u27a1 "):
                    embed = discord.Embed(
                        title=f"GFLAnalysis: {name}",
                        color=discord.Color.green(),
                        url=f"https:{raw['fullurl']}"
                    )
                    for key in ("Pros", "Cons", "Status", "Roles"):
                        embed.add_field(name=key, value="".join(gflanalysis_parser.parse("\n".join(pr[key]).replace("&#8203;", "\n"))), inline=False)

                    embed.add_field(name="Analysis", value=a, inline=False)
                    embeds.append(embed)

        if ret:
            return ret
        else:
            embed = discord.Embed(
                title=f"GFLAnalysis: {self.en_name}",
                color=discord.Color.green(),
                description="No analysis thus far."
            )
            return {"original": [embed]}

    async def query_speq(self, ctx):
        col = ctx.cog.special_equipments
        emojis = ctx.cog.emojis

        stat_bases = {"": self.__dict__}
        if self.moddable:
            stat_bases[" Mod"] = self.mod_data
        digest_tabs = []
        for suffix, base in stat_bases.items():
            embed = discord.Embed(
                title=f"{self.en_name}{suffix}",
                color=discord.Color.green(),
                url=f"{GFWIKI_BASE}/wiki/{quote(self.name)}"
            )
            embed.add_field(
                name="Stats",
                value=
                    f"{emojis['hp']}**HP:** {base['max_hp']} (x5)\n"
                    f"{emojis['damage']}**DMG:** {base['max_dmg']}\n"
                    f"{emojis['accuracy']}**ACC:** {base['max_acc']}"
                    +
                    (f"\n{emojis['armor']}**ARMOR:**  {base['max_armor']}" if base["max_armor"] > 0 else "")
            )
            embed.add_field(
                name="\u200b",
                value=
                    f"{emojis['rof']}**ROF:** {base['max_rof']}\n"
                    f"{emojis['evasion']}**EVA:** {base['max_eva']}\n"
                    f"{emojis['crit_rate']}**CRIT RATE:** {self.crit_rate}%"
                    +
                    (f"\n{emojis['clip_size']}**ROUNDS:** {base['clip_size']}" if base["clip_size"] > 0 else "")
            )
            digest_tabs.append(embed)

        embeds = []
        async for doc in col.find({"compatible": self.name}):
            stat_info = []
            for stat in doc["stats"]:
                name = stat["name"]
                if name == "boost_skill_effect":
                    stat_info.append("**BOOST SKILL EFFECT**")
                else:
                    display = STAT_DISPLAY[name]
                    stat_info.append(f"{emojis[name]}**{display[0]}** {stat['value']:+}{display[1]}")
            stat_desc = "\n".join(stat_info)
            embed = discord.Embed(
                title=doc["name"],
                color=discord.Color.green(),
                url=f"{GFWIKI_BASE}/wiki/{quote(doc['name'])}",
                description=stat_desc
            )
            embed.set_thumbnail(url=doc["image_url"])
            embeds.append(embed)

            for digest in digest_tabs:
                digest.add_field(
                    name=doc["name"],
                    value=stat_desc,
                    inline=False
                )

        max_page = len(embeds)
        for i, embed in enumerate(embeds):
            embed.set_footer(text=f"({i+1}/{max_page})")
    
        return {
            "equipments": embeds,
            "digest": digest_tabs
        }

#==================================================================================================================================================

class GirlsFrontline(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.doll_list = bot.db.doll_list
        self.special_equipments = bot.db.special_equipments
        self.fairy_list = bot.db.fairy_list

        test_guild_2 = bot.get_guild(config.TEST_GUILD_2_ID)
        self.emojis = {"white_square": "\u2b1c", "black_square": "\u2b1b", "blue_square": "\U0001f7e6"}
        for emoji_name in (
            "hp", "damage", "accuracy", "rof", "evasion", "armor",
            "crit_rate", "crit_dmg", "armor_penetration", "clip_size", "mobility",
            "HG", "RF", "AR", "SMG", "MG", "SG", "rank",
            "mem_frag", "exoskeleton", "battle_fairy", "strategy_fairy", "shotgun_ammo", "peq"
        ):
            self.emojis[emoji_name] = discord.utils.find(lambda e: e.name==emoji_name, test_guild_2.emojis)

        bot.loop.create_task(self.gfwiki_bot_login())

    async def gfwiki_bot_login(self):
        session = self.bot.session
        async with session.get(
            GFWIKI_API,
            params={
                "action": "query",
                "meta": "tokens",
                "type": "login",
                "format": "json"
            }
        ) as resp:
            data = json.loads(await resp.read())
            bot_token = data["query"]["tokens"]["logintoken"]

        async with session.post(
            GFWIKI_API,
            data={
                "action": "login",
                "format": "json",
                "lgname": token.GFWIKI_BOT_USERNAME,
                "lgpassword": token.GFWIKI_BOT_PASSWORD,
                "lgtoken": bot_token
            }
        ) as resp:
            data = json.loads(await resp.read())

    async def _search(self, ctx, name, *, prompt=None):
        return await ctx.search(
            name,
            self.doll_list,
            cls=Doll,
            colour=discord.Colour.green(),
            atts=["name", "full_name", "en_name", "classification", "aliases"],
            name_att="qual_name",
            emoji_att="classification",
            prompt=prompt,
            sort={"index": 1}
        )

    @modding.help(brief="Display t-doll info", category="GFL", field="Database", paragraph=0)
    @commands.group(aliases=["td"], invoke_without_command=True)
    async def doll(self, ctx, *, name):
        '''
            `>>doll <name>`
            Display a T-doll info.
            Name is case-insensitive.
        '''
        d = await self._search(ctx, name)
        if d:
            await d.display_info(ctx)

    @doll.group(name="update")
    @checks.in_certain_guild(607747682458402817)
    async def doll_update(self, ctx):
        pass

    @doll_update.command(aliases=["all"])
    async def everything(self, ctx):
        await ctx.trigger_typing()
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmprop": "title",
            "cmtitle": "Category:T-Dolls",
            "cmtype": "page",
            "cmlimit": 5000,
            "redirects": 1,
            "format": "json"
        }
        bytes_ = await self.bot.fetch(GFWIKI_API, params=params)
        data = json.loads(bytes_)
        names = []
        for cm in data["query"]["categorymembers"]:
            names.append(cm["title"])

        await self.update_dolls_with_names(ctx, names)

    @doll_update.command()
    async def many(self, ctx, *names):
        await ctx.trigger_typing()
        logs = await self.update_dolls_with_names(ctx, names)
        if logs:
            await ctx.send(file=discord.File.from_str(json.dumps(logs, indent=4, ensure_ascii=False)))

    async def update_dolls_with_names(self, ctx, names):
        await ctx.send(f"Total: {len(names)} dolls")
        msg = await ctx.send(f"Fetching...\n{utils.progress_bar(0)}")
        passed = []
        failed = []
        logs = {}
        count = len(names)
        for i, name in enumerate(names):
            try:
                doll = await self.search_gfwiki(name)
            except:
                logs[name] = traceback.format_exc()
                failed.append(name)
            else:
                passed.append(doll.name)
                await self.doll_list.update_one(
                    {"index": doll.index, "rarity": doll.rarity},
                    {"$set": doll.__dict__},
                    upsert=True
                )
            if (i+1)%10 == 0:
                await msg.edit(content=f"Fetching...\n{utils.progress_bar((i+1)/count)}")
        await msg.edit(content=f"Done.\n{utils.progress_bar(1)}")
        txt = json.dumps({"passed": passed, "failed": failed}, indent=4)
        if len(txt) > 1900:
            await ctx.send(
                f"Passed: {len(passed)}\nFailed: {len(failed)}",
                file=discord.File.from_str(txt)
            )
        else:
            await ctx.send(f"Passed: {len(passed)}\nFailed: {len(failed)}\n```json\n{txt}\n```")
        return logs

    async def search_gfwiki(self, name):
        bytes_ = await self.bot.fetch(
            GFWIKI_API,
            params={
                "action":       "parse",
                "prop":         "wikitext",
                "page":         name,
                "format":       "json",
                "redirects":    1
            }
        )
        raw = json.loads(bytes_)
        if "error" in raw:
            raise checks.CustomError(f"Page {name} doesn't exist.")

        raw_basic_info = raw["parse"]["wikitext"]["*"]
        ret = parser.parse(raw_basic_info)
        for r in ret:
            if "classification" in r:
                basic_info = r
                break

        dtype = basic_info["classification"]
        doll = Doll({})

        # basic section
        doll.name = raw["parse"]["title"]
        doll.full_name = normalize(basic_info["fullname"])
        doll.en_name = normalize(basic_info.get("releasedon", "").strip(" ,"))
        doll.aliases = name_clean_regex.sub("", normalize(doll.name))
        doll.index = int(basic_info["index"][-3:]) if basic_info["rarity"] == "EXTRA" else int(basic_info["index"])
        doll.classification = dtype
        doll.rarity = basic_info["rarity"]
        doll.artist = basic_info["artist"]
        doll.voice_actor = basic_info.get("voiceactor")
        doll.manufacturer = basic_info.get("manufacturer")
        doll.origin = basic_info.get("nationality")

        doll.max_hp = int(basic_info["max_hp"]) * 5
        doll.max_dmg = int(basic_info["max_dmg"])
        doll.max_eva = int(basic_info["max_eva"])
        doll.max_acc = int(basic_info["max_acc"])
        doll.max_rof = int(basic_info["max_rof"])
        doll.max_armor = utils.to_int(basic_info.get("max_armor"), default=0)
        doll.clip_size = utils.to_int(basic_info.get("clipsize"), default=0)

        doll.crit_rate = utils.to_int(basic_info.get("crit", "").rstrip("%"), default=CRIT_RATE[dtype])
        doll.mobility = int(basic_info.get("mov", MOBILITY[dtype]))
        doll.craft_time = timer_to_seconds(basic_info.get("craft", ""))
        order = EQUIPMENT_ORDER[dtype].copy()
        for i in range(3):
            cur = basic_info.get(f"slot{i+1}")
            if cur:
                order[i] = cur
        doll.equipment_slots = get_equipment_slots(
            dtype,
            order,
            add_ap=basic_info.get("use_armor-piercing_ammo", False),
            add_armor=basic_info.get("use_ballistic_plate", False)
        )

        tile = {}
        tile["shape"] = {str(i): utils.to_int(basic_info.get(f"tile{i}"), default=-1) for i in range(1, 10)}
        tile["target"] = basic_info.get("aura1")
        tile["effect"] = [
            basic_info.get("aura2", ""),
            basic_info.get("aura3", "")
        ]
        doll.tile = tile

        doll.trivia = basic_info.get("trivia")

        # mod 3 basic info section
        mod = {}
        if basic_info.get("moddable") or basic_info.get("mod1_max_hp"):
            doll.moddable = True
            mod["max_hp"] = int(get_either(basic_info, *mod_keys("max_hp"), default=0)) * 5
            mod["max_dmg"] = int(get_either(basic_info, *mod_keys("max_dmg"), default=0))
            mod["max_eva"] = int(get_either(basic_info, *mod_keys("max_eva"), default=0))
            mod["max_acc"] = int(get_either(basic_info, *mod_keys("max_acc"), default=0))
            mod["max_rof"] = int(get_either(basic_info, *mod_keys("max_rof"), default=0))
            mod["max_armor"] = int(get_either(basic_info, *mod_keys("max_armor"), default=0))
            mod["clip_size"] = int(get_either(basic_info, *mod_keys("clipsize"), default=0))

            mod_tile = {}

            mod_tile["shape"] = {str(i): utils.to_int(get_either(basic_info, *mod_keys(f"tile{i}")), default=-1) for i in range(1, 10)}
            mod_tile["target"] = basic_info.get("mod1_aura1") or basic_info.get("aura1")
            mod_tile["effect"] = [
                basic_info.get("mod1_aura2") or basic_info.get("aura2", ""),
                basic_info.get("mod1_aura3") or basic_info.get("aura3", "")
            ]
            mod["tile"] = mod_tile
        else:
            doll.moddable = False

        # skill section
        bytes_ = await self.bot.fetch(
            GFWIKI_API,
            params={
                "action":       "parse",
                "prop":         "wikitext",
                "page":         doll.name + "/skilldata",
                "format":       "json",
                "redirects":    1
            }
        )
        raw_skilldata = json.loads(bytes_)
        doll.skill = parser.parse(raw_skilldata["parse"]["wikitext"]["*"])[0]

        # mod 3 skill
        if doll.moddable:
            skill = []
            for path in ("/skilldata/mod1", "/skill2data"):
                bytes_ = await self.bot.fetch(
                    GFWIKI_API,
                    params={
                        "action":       "parse",
                        "prop":         "wikitext",
                        "page":         doll.name + path,
                        "format":       "json",
                        "redirects":    1
                    }
                )
                raw_skilldata = json.loads(bytes_)
                skill.append(parser.parse(raw_skilldata["parse"]["wikitext"]["*"])[0])
            mod["skill"] = skill

        # skin section
        file_list = {
            f"{doll.name}.png": (0, "default", "normal"),
            f"{doll.name} D.png": (0, "default", "damaged")
        }
        for index in range(1, 9):
            next_costume = f"costume{index}"
            costume_name = basic_info.get(next_costume)
            if costume_name:
                file_list[f"{doll.name} {next_costume}.png"] = (index, costume_name, "normal")
                file_list[f"{doll.name} {next_costume} D.png"] = (index, costume_name, "damaged")
            else:
                break

        skins = []
        mod_skins = []
        for filename, (index, costume_name, form) in file_list.items():
            skin = {
                "index": index,
                "name": costume_name,
                "form": form,
                "image_url": generate_image_url(filename)
            }
            if costume_name == "[Digimind Upgrade]":
                mod_skins.append(skin)
            else:
                skins.append(skin)

        skins.sort(key=lambda x: (-x["index"], x["form"]), reverse=True)
        doll.skins = skins
        mod["skins"] = mod_skins
        doll.mod_data = mod

        return doll

    @modding.help(brief="Search for t-dolls using given conditions", category="GFL", field="Database", paragraph=0)
    @doll.command()
    async def filter(self, ctx, *, data: modding.KeyValue(
        {
            "index": modding.Comparison(int),
            "hp": modding.Comparison(int),
            "rarity": modding.Comparison(str),
            ("dmg", "damage", "fp", "firepower"): modding.Comparison(int),
            ("eva", "evasion", "dodge"): modding.Comparison(int),
            ("acc", "accuracy"): modding.Comparison(int),
            "rof": modding.Comparison(int),
            "armor": modding.Comparison(int),
            ("clip_size", "rounds"): modding.Comparison(int),
            ("crit_rate", "crit"): modding.Comparison(int),
            ("skill_cd", "skill.cd"): modding.Comparison(int),
            ("skill_icd", "skill.icd"): modding.Comparison(int)
        }
    )=modding.EMPTY):
        '''
            `>>doll filter <criteria>`
            Find all T-dolls with criteria.
            Criteria can contain multiple lines, each with format `attribute=value`, or `attribute>value`/`attribute<value` if applicable.
            Available attributes:
            (TBA since it's long and I'm lazy, but it should be stuff like hp, fp, acc, eva, rof, artist...)
        '''
        if not data:
            raise checks.CustomError("Can't filter without any input you know.")

        query = []
        projection = {"_id": 0, "index": 1, "en_name": 1, "name": 1}

        for orig, keys in (
            ("index", ("index",)),
            ("max_hp", ("hp",)),
            ("rarity", ("rarity",)),
            ("max_dmg", ("dmg", "damage", "fp", "firepower")),
            ("max_eva", ("eva", "evasion", "dodge")),
            ("max_acc", ("acc", "accuracy")),
            ("max_rof", ("rof",)),
            ("max_armor", ("armor",)),
            ("clip_size", ("clip_size", "rounds")),
            ("crit_rate", ("crit_rate", "crit")),
            ("skill.cd", ("skill_cd",)),
            ("skill.icd", ("skill_icd",)),
            ("skill.icd", ("skill_icd",)),
            ("skill.icd", ("skill_icd",))
        ):
            item = data.geteither(*keys, default=None)
            if item is not None:
                query.append({orig: item.to_query()})
                projection[orig.partition(".")[0]] = 1

        rarity = data.get("rarity", None)
        if rarity is not None:
            rarity.number = rarity.number.upper()
            query.append({"rarity": rarity.to_query()})
            projection["rarity"] = 1

        for orig, keys in (
            ("full_name", ("name", "full_name")),
            ("origin", ("origin", "nationality")),
            ("classification", ("class", "classification")),
            ("artist", ("artist", "illustrator")),
            ("voice_actor", ("voice_actor", "va", "cv")),
            ("origin", ("nationality", "origin")),
            ("tile.target", ("tile_target",)),
            ("tile.effect", ("tile_effect", "tile_buff"))
        ):
            item = data.geteither(*keys, default=None)
            if item is not None:
                query.append({
                    orig: {
                        "$regex": ".*?".join(map(re.escape, item.split())),
                        "$options": "i"
                    }
                })
                projection[orig] = 1

        skill = data.get("skill", None)
        if skill:
            base = ".*?".join(map(re.escape, skill.split()))
            query.append({"$or": [
                {
                    "skill.name": {
                        "$regex": base,
                        "$options": "i"
                    }
                },
                {
                    "skill.effect": {
                        "$regex": base,
                        "$options": "i"
                    }
                }
            ]})
            projection["skill"] = 1

        tile = data.get("tile", None)
        if tile:
            try:
                int(tile)
            except ValueError:
                pass
            else:
                query.append({f"tile.shape.{tile[0]}": 0})
                query.extend({f"tile.shape.{t}": 1} for t in tile[1:])

        result = []
        async for data in self.doll_list.aggregate([
            {"$match": {"$and": query}},
            {"$project": projection},
            {"$sort": {"index": 1}}
        ]):
            index = data.pop("index")
            name = data.pop("name")
            name = data.pop("en_name") or name
            embed_info = []
            for key, value in data.items():
                if key == "tile":
                    embed_info.append(f"tile: {value['effect'][0]}. {value['effect'][1]}")
                elif key == "skill":
                    embed_info.append(f"skill: {value['name']} - {value['effect']}")
                else:
                    value = str(value)
                    value = value[:200] + "..." if len(value)>200 else value
                    embed_info.append(f"{key}: {value}")
            v = "\n".join(embed_info)
            result.append(f"`#{index}` **{name}**\n{v}")

        if result:
            paging = utils.Paginator(
                result, 5, separator="\n\n",
                title=f"Search result: {len(result)} results",
                description=lambda i, x: x,
                colour=discord.Colour.green()
            )
            await paging.navigate(ctx)
        else:
            await ctx.send("No result found.")

    @modding.help(brief="Display t-dolls with given craft timer", category="GFL", field="Database", paragraph=0)
    @commands.command(aliases=["t"])
    async def timer(self, ctx, time):
        '''
            `>>timer <time>`
            Display Tdolls with input timer.
            Format is either h:mm or hmm.
        '''
        m = timer_regex.match(time)
        if m:
            doll_timer = utils.to_int(m.group(1), default=0) * 3600 + int(m.group(2)) * 60
            embeds = []
            data = [d async for d in self.doll_list.find({"craft_time": doll_timer})]
            for i, d in enumerate(data):
                embed = discord.Embed(color=discord.Color.green())
                embed = discord.Embed(
                    title=f"#{d['index']} {d['en_name'] or d['name']}",
                    color=discord.Color.green(),
                    url=f"{GFWIKI_BASE}/wiki/{quote(d['name'])}"
                )
                embed.add_field(name="Classification", value=f"{self.emojis[d['classification']]}{d['classification']}")
                embed.add_field(name="Rarity", value=str(self.emojis["rank"])*utils.to_int(d["rarity"], default=0) or "**EXTRA**")
                embed.add_field(name="Production time", value=f"{d['craft_time']//3600}:{d['craft_time']%3600//60:0>2d}")
                embed.set_image(url=d["skins"][0]["image_url"])
                embed.set_footer(text=f"({i+1}/{len(data)})")
                embeds.append(embed)

            if embeds:
                paging = utils.Paginator(embeds, render=False)
                return await paging.navigate(ctx)

        await ctx.send("Invalid timer")

    @commands.group(aliases=["e"], invoke_without_command=True)
    @checks.in_certain_guild(607747682458402817)
    async def speq(self, ctx, *, name):
        '''
            `>>speq <name>`
            Display a special equipment info.
            Name is case-insensitive.
        '''
        pass

    @speq.group(name="update")
    @checks.in_certain_guild(607747682458402817)
    async def speq_update(self, ctx):
        pass

    @speq_update.command(name="everything", aliases=["all"])
    async def update_all_speq(self, ctx):
        await ctx.trigger_typing()
        params = {
            "action":       "query",
            "list":         "categorymembers",
            "cmtitle":      "Category:Exclusive Equipments",
            "cmlimit":      5000,
            "format":       "json",
            "redirects":    1
        }
        bytes_ = await self.bot.fetch(GFWIKI_API, params=params)
        data = json.loads(bytes_)
        names = []
        for cm in data["query"]["categorymembers"]:
            names.append(cm["title"])

        await self.update_equipments_with_names(ctx, names)

    @speq_update.command(name="many")
    async def update_many_speq(self, ctx, *names):
        await ctx.trigger_typing()
        logs = await self.update_equipments_with_names(ctx, names)
        if logs:
            await ctx.send(file=discord.File.from_str(json.dumps(logs, indent=4, ensure_ascii=False)))

    async def update_equipments_with_names(self, ctx, names):
        await ctx.send(f"Total: {len(names)} equipments")
        msg = await ctx.send(f"Fetching...\n{utils.progress_bar(0)}")
        passed = []
        failed = []
        logs = {}
        count = len(names)
        for i, name in enumerate(names):
            try:
                speq = await self.search_gfwiki_for_speq(name)
            except:
                logs[name] = traceback.format_exc()
                failed.append(name)
            else:
                passed.append(speq["name"])
                await self.special_equipments.update_one(
                    {"name": speq["name"]},
                    {"$set": speq},
                    upsert=True
                )
            if (i+1)%10 == 0:
                await msg.edit(content=f"Fetching...\n{utils.progress_bar((i+1)/count)}")
        await msg.edit(content=f"Done.\n{utils.progress_bar(1)}")
        txt = json.dumps({"passed": passed, "failed": failed}, indent=4)
        if len(txt) > 1900:
            await ctx.send(
                f"Passed: {len(passed)}\nFailed: {len(failed)}",
                file=discord.File.from_str(txt)
            )
        else:
            await ctx.send(f"Passed: {len(passed)}\nFailed: {len(failed)}\n```json\n{txt}\n```")
        return logs

    async def search_gfwiki_for_speq(self, name):
        bytes_ = await self.bot.fetch(
            GFWIKI_API,
            params={
                "action":       "parse",
                "prop":         "wikitext",
                "page":         name,
                "format":       "json",
                "redirects":    1
            }
        )
        raw = json.loads(bytes_)
        if "error" in raw:
            raise checks.CustomError(f"Page {name} doesn't exist.")

        raw_basic_info = raw["parse"]["wikitext"]["*"]
        ret = parser.parse(raw_basic_info)
        for r in ret:
            if "class" in r:
                basic_info = r
                break

        speq = {}
        speq["name"] = name
        speq["class"] = basic_info["class"]
        speq["slot"] = basic_info["slot"]
        speq["rarity"] = utils.to_int(basic_info["rarity"])
        speq["compatible"] = basic_info["compatibleto"]
        stats = []
        for i in range(1, 5):
            stat_name = basic_info.get(f"stat{i}")
            if stat_name:
                stat_name = stat_name.replace("(%)", "").replace(" ", "").lower()
                normalized_name = STATS_NORMALIZE[stat_name]
                base_stat = max(
                    to_float(basic_info.get(f"stat{i}max"), default=-INF),
                    to_float(basic_info.get(f"stat{i}min"), default=-INF)
                )
                growth = float(basic_info.get(f"stat{i}growth") or 1)
                cur = {
                    "name": normalized_name,
                    "value": int(base_stat * growth)
                }
                stats.append(cur)
            else:
                break
        speq["stats"] = stats
        
        filename = basic_info.get("icon") or f"Generic {basic_info['compatibleto']} {basic_info['class']}"
        filename = filename + ".png"
        speq["image_url"] = generate_image_url(filename)

        return speq

    @modding.help(brief="Display fairy info", category="GFL", field="Database", paragraph=0)
    @commands.group(aliases=["f"], invoke_without_command=True)
    async def fairy(self, ctx, *, name):
        '''
            `>>fairy <name>`
            Display a fairy info.
            Name is case-insensitive.
        '''
        fairy = await ctx.search(
            name,
            self.fairy_list,
            colour=discord.Colour.blue(),
            atts=["name", "en_name"],
            name_att="en_name",
            emoji_att="classification",
            sort={"index": 1}
        )
        if fairy:
            if fairy.image_urls:
                emojis = self.emojis
                embeds = []
                image_count = len(fairy.image_urls)
                classification = fairy.classification
                for i, image_url in enumerate(fairy.image_urls):
                    embed = discord.Embed(
                        title=fairy.en_name,
                        color=discord.Color.blue() if classification[0]=="s" else discord.Color.dark_orange(),
                        url=f"{GFWIKI_BASE}/wiki/{quote(fairy.name)}"
                    )

                    embed.add_field(
                        name="Classification",
                        value=f"{emojis[fairy.classification]} {fairy.classification.replace('_', ' ').title()}",
                        inline=False
                    )
                    
                    stat_info = []
                    st = fairy.stats
                    for key, emoji_name, title in (
                        ("dmg", "damage", "DMG"),
                        ("critdmg", "crit_dmg", "Crit DMG"),
                        ("acc", "accuracy", "ACC"),
                        ("eva", "evasion", "EVA"),
                        ("armor", "armor", "Armor")
                    ):
                        stat = st[key]
                        if stat:
                            stat_info.append(f"{emojis[emoji_name]}**{title}** +{stat}")

                    embed.add_field(
                        name="Stats",
                        value="\n".join(stat_info),
                        inline=False
                    )

                    sk = fairy.skill
                    embed.add_field(
                        name="Skill",
                        value=f"**{sk['name']}** (Cost: {sk['cost']} Fairy Command(s))\n"
                            f"{sk['effect']}",
                        inline=False
                    )

                    embed.set_footer(text=f"({i+1}/{image_count})")
                    embed.set_image(url=image_url)

                    embeds.append(embed)

                paging = utils.Paginator([])
                embed_iter = circle_iter(embeds)

                @paging.wrap_action("\U0001f5bc")
                def change_image():
                    return next(embed_iter)

                await paging.navigate(ctx)
            else:
                return await ctx.send("This fairy info is currently incompleted and thus cannot be displayed.")

    @fairy.group(name="update")
    @checks.in_certain_guild(607747682458402817)
    async def fairy_update(self, ctx):
        pass

    @fairy_update.command(name="everything", aliases=["all"])
    async def update_all_fairies(self, ctx):
        await ctx.trigger_typing()
        names = []
        for category in ("Battle Fairies", "Strategy Fairies"):
            params = {
                "action":       "query",
                "list":         "categorymembers",
                "cmtitle":      f"Category:{category}",
                "cmlimit":      5000,
                "format":       "json",
                "redirects":    1
            }
            bytes_ = await self.bot.fetch(GFWIKI_API, params=params)
            data = json.loads(bytes_)
            for cm in data["query"]["categorymembers"]:
                names.append(cm["title"])

        await self.update_fairies_with_names(ctx, names)

    @fairy_update.command(name="many")
    async def update_many_fairies(self, ctx, *names):
        await ctx.trigger_typing()
        logs = await self.update_fairies_with_names(ctx, names)
        if logs:
            await ctx.send(file=discord.File.from_str(json.dumps(logs, indent=4, ensure_ascii=False)))

    async def update_fairies_with_names(self, ctx, names):
        await ctx.send(f"Total: {len(names)} fairies")
        msg = await ctx.send(f"Fetching...\n{utils.progress_bar(0)}")
        passed = []
        failed = []
        logs = {}
        count = len(names)
        for i, name in enumerate(names):
            try:
                fairy = await self.search_gfwiki_for_fairy(name)
            except:
                logs[name] = traceback.format_exc()
                failed.append(name)
            else:
                passed.append(fairy["name"])
                await self.fairy_list.update_one(
                    {"name": fairy["name"]},
                    {"$set": fairy},
                    upsert=True
                )
            if (i+1)%10 == 0:
                await msg.edit(content=f"Fetching...\n{utils.progress_bar((i+1)/count)}")
        await msg.edit(content=f"Done.\n{utils.progress_bar(1)}")
        txt = json.dumps({"passed": passed, "failed": failed}, indent=4)
        if len(txt) > 1900:
            await ctx.send(
                f"Passed: {len(passed)}\nFailed: {len(failed)}",
                file=discord.File.from_str(txt)
            )
        else:
            await ctx.send(f"Passed: {len(passed)}\nFailed: {len(failed)}\n```json\n{txt}\n```")
        return logs

    
    async def search_gfwiki_for_fairy(self, name):
        bytes_ = await self.bot.fetch(
            GFWIKI_API,
            params={
                "action":       "parse",
                "prop":         "wikitext",
                "page":         name,
                "format":       "json",
                "redirects":    1
            }
        )
        raw = json.loads(bytes_)
        if "error" in raw:
            raise checks.CustomError(f"Page {name} doesn't exist.")

        raw_basic_info = raw["parse"]["wikitext"]["*"]
        ret = parser.parse(raw_basic_info)
        for r in ret:
            if "class" in r:
                basic_info = r
                break

        fairy = {}
        fairy["index"] = int(basic_info["index"])
        fairy["name"] = name
        fairy["en_name"] = basic_info.get("releasedon", "").strip(" ,") or name
        fairy["classification"] = basic_info["class"].lower() + "_fairy"
        fairy["craft_time"] = timer_to_seconds(basic_info.get("craft", ""))

        stats = {}
        for key in ("dmg", "critdmg", "acc", "eva", "armor"):
            stats[key] = basic_info.get(f"max_{key}")
        fairy["stats"] = stats
        
        fairy["skill"] = {
            "name": basic_info["skillname"],
            "effect": basic_info["skilldesc"],
            "cost": basic_info["skillcost"]
        }

        fairy["image_urls"] = [
            generate_image_url(f"{name}.png"),
            generate_image_url(f"{name} 2.png"),
            generate_image_url(f"{name} 3.png")
        ]

        return fairy

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(GirlsFrontline(bot))
