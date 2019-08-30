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

#==================================================================================================================================================

GFWIKI_API = "https://en.gfwiki.com/api.php"

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
    while True:
        if with_index:
            for i, item in enumerate(iterable):
                yield i, item
        else:
            for item in iterable:
                yield item

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

#==================================================================================================================================================

parser = wiki.WikitextParser()

@parser.set_box_handler("PlayableUnit")
def handle_playable_unit(box, **kwargs):
    return kwargs

@parser.set_box_handler("voice actor name")
@parser.set_box_handler("artist name")
def handle_creator(box, name):
    return name

@parser.set_box_handler("doll_server_alias")
def handle_alias(box, *, server, alias):
    if server == "EN":
        return alias
    else:
        return ""

@parser.set_box_handler("doll name")
def handle_doll_name(box, name, *args):
    return name

@parser.set_box_handler("HG aura")
@parser.set_box_handler("HG_aura")
def handle_hg_aura(box, value):
    return value + "%"

@parser.set_box_handler("enemy name")
def handle_enemy_name(box, name, subtype="enemy"):
    return name

@parser.set_box_handler("cite ab1")
def handle_cite_ab1(box, value):
    return ""

@parser.set_box_handler("equip name")
def handle_equip_name(box, name, type, rarity):
    return name

@parser.set_reference_handler
def handle_reference(box, *args, **kwargs):
    return box

@parser.set_html_handler("ref")
def handle_ref_tag(tag, text, **kwargs):
    return ""

@parser.set_html_handler("div")
def handle_div_tag(tag, text, **kwargs):
    if kwargs.get("class") == "spoiler":
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

class Doll(data_type.BaseObject):
    @property
    def qual_name(self):
        return self.en_name or self.name

    def _base_info(self, cog):
        emojis = cog.emojis
        embeds = []
        for skill_effect in utils.split_page(self.skill["effect"], 900, check=lambda s:s=="\n"):
            embed = discord.Embed(
                title=f"#{self.index} {self.en_name or self.name}",
                color=discord.Color.green(),
                url=f"https://en.gfwiki.com/wiki/{quote(self.name)}"
            )
            embed.add_field(name="Classification", value=f"{emojis[self.classification]}{self.classification}")
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
                    f"{emojis['accuracy']}**ACC:** {self.max_acc}\n"
                    f"{emojis['rof']}**ROF:** {self.max_rof}\n"
                    f"{emojis['evasion']}**EVA:** {self.max_eva}\n"
                    f"{emojis['crit_rate']}**Crit rate:** {self.crit_rate}%"
                    +
                    (f"{emojis['armor']}**Armor:**  {self.max_armor}\n" if self.max_armor > 0 else "")
                    +
                    (f"{emojis['clip_size']}**Clip size:** {self.clip_size}\n" if self.clip_size > 0 else "")
            )
            embed.add_field(
                name="Equipment slots",
                value=
                    "\n".join(f"**Lv{20+i*30}**:\n\u200b    {''.join(str(emojis[e]) for e in self.equipment_slots[i])}" for i in range(3))
            )

            tile = {
                k: emojis["green_square"] if v==1 else emojis["white_square"] if v==0 else emojis["black_square"]
                for k, v in self.tile["shape"].items()
            }

            embed.add_field(
                name="Tile",
                value=
                    f"\u200b {tile['7']}{tile['8']}{tile['9']}\u2001{self.tile['target']}\n"
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

    def _other_info(self, cog):
        embeds = []
        for trivia in utils.split_page(self.trivia, 1000, check=lambda s:s=="\n"):
            embed = discord.Embed(
                title=f"#{self.index} {self.en_name or self.name}",
                color=discord.Color.green(),
                url=f"https://en.gfwiki.com/wiki/{quote(self.name)}"
            )
            embed.add_field(name="Full name", value=self.full_name)
            embed.add_field(name="Origin", value=self.origin)
            embed.add_field(name="Illustrator", value=self.artist)
            embed.add_field(name="Voice Actor", value=self.voice_actor or "None")
            embed.add_field(name="Trivia", value=trivia or "None", inline=False)
            embeds.append(embed)

        return embeds

    def _mod_info(self, cog):
        emojis = cog.emojis
        embeds = []
        mod = self.mod_data

        for skill_index in range(2):
            for skill_effect in utils.split_page(mod["skill"][skill_index]["effect"], 900, check=lambda s:s=="\n"):
                embed = discord.Embed(
                    title=f"#{self.index} {self.en_name or self.name}",
                    color=discord.Color.green(),
                    url=f"https://en.gfwiki.com/wiki/{quote(self.name)}"
                )
                embed.add_field(name="Classification", value=f"{emojis[self.classification]}{self.classification}")
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
                        f"{emojis['accuracy']}**ACC:** {mod['max_acc']}\n"
                        f"{emojis['rof']}**ROF:** {mod['max_rof']}\n"
                        f"{emojis['evasion']}**EVA:** {mod['max_eva']}\n"
                        f"{emojis['crit_rate']}**Crit rate:** {self.crit_rate}%"
                        +
                        (f"{emojis['armor']}**Armor:**  {mod['max_armor']}\n" if mod["max_armor"] > 0 else "")
                        +
                        (f"{emojis['clip_size']}**Clip size:** {mod['clip_size']}\n" if mod["clip_size"] > 0 else "")
                )
                embed.add_field(
                    name="Equipment slots",
                    value=
                        "\n".join(f"**Lv{20+i*30}**:\n\u200b    {''.join(str(emojis[e]) for e in self.equipment_slots[i])}" for i in range(3))
                )

                tile = {
                    k: emojis["green_square"] if v==1 else emojis["white_square"] if v==0 else emojis["black_square"]
                    for k, v in mod["tile"]["shape"].items()
                }

                embed.add_field(
                    name="Tile",
                    value=
                        f"\u200b {tile['7']}{tile['8']}{tile['9']}\u2001{mod['tile']['target']}\n"
                        f"\u200b {tile['4']}{tile['5']}{tile['6']}\u2001{mod['tile']['effect'][0]}\n"
                        f"\u200b {tile['1']}{tile['2']}{tile['3']}\u2001{mod['tile']['effect'][1]}",
                    inline=False
                )

                skill = mod["skill"][skill_index]
                icd = f"Initial CD: {skill['icd']}s" if skill["icd"] else None
                cd = f"CD: {skill['cd']}s" if skill["cd"] else None
                if cd or icd:
                    add = " (" + "/".join(filter(None, (icd, cd))) + ")"
                else:
                    add = ""

                embed.add_field(
                    name=f"Skill {skill_index+1}",
                    value=
                        f"**{skill['name']}**{add}\n"
                        f"{skill_effect}",
                    inline=False
                )
                embeds.append(embed)

        return embeds

    async def display_info(self, ctx):
        paging = utils.Paginator([])
        base_info = self._base_info(ctx.cog)
        other_info = self._other_info(ctx.cog)
        skin = self.skins

        saved = {
            "info": None,
            "info_iter": None,
            "skin": None,
            "skin_iter": None,
            "current_skin": None
        }

        def add_image():
            index, skin = saved["current_skin"]
            saved["embed"].set_footer(text=f"Skin: {skin['name']} ({skin['form']}) - ({index+1}/{len(saved['skin'])})")
            saved["embed"].set_image(url=skin["image_url"])

        def change_info_to(info, skin):
            if saved["info"] is not info:
                saved["info"] = info
                saved["info_iter"] = circle_iter(info)
            if saved["skin"] is not skin:
                saved["skin"] = skin
                saved["skin_iter"] = circle_iter(skin, with_index=True)
                saved["current_skin"] = next(saved["skin_iter"])
            saved["embed"] = next(saved["info_iter"])
            add_image()

        @paging.wrap_action("\U0001f1ee")
        def change_base_info():
            change_info_to(base_info, skin)
            return saved["embed"]

        @paging.wrap_action("\U0001f1f9")
        def change_other_info():
            change_info_to(other_info, skin)
            return saved["embed"]

        if self.moddable:
            mod_info = self._mod_info(ctx.cog)
            mod_skin = self.mod_data["skins"]

            @paging.wrap_action("\U0001f1f2")
            def change_mod3_info():
                change_info_to(mod_info, mod_skin)
                return saved["embed"]

        @paging.wrap_action("\U0001f5bc")
        def change_image():
            saved["current_skin"] = next(saved["skin_iter"])
            add_image()
            return saved["embed"]

        await paging.navigate(ctx)

#==================================================================================================================================================

class GirlsFrontline(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.doll_list = bot.db.doll_list

        test_guild_2 = bot.get_guild(config.TEST_GUILD_2_ID)
        self.emojis = {"white_square": "\u2b1c", "black_square": "\u2b1b"}
        for emoji_name in (
            "green_square",
            "hp", "damage", "accuracy", "rof", "evasion", "armor",
            "crit_rate", "crit_dmg", "armor_penetration", "clip_size", "mobility",
            "telescopic_sight", "red_dot_sight", "holographic_sight",
            "night_equipment", "silencer",
            "hp_ammo", "hv_ammo", "ap_ammo", "shotgun_ammo",
            "armor_plate", "camo_cape", "ammo_box", "exoskeleton", "chip",
            "ammo", "ration"
        ):
            self.emojis[emoji_name] = discord.utils.find(lambda e: e.name==emoji_name, test_guild_2.emojis)

        creampie_guild = self.bot.get_guild(config.CREAMPIE_GUILD_ID)
        for emoji_name in ("HG", "RF", "AR", "SMG", "MG", "SG", "rank"):
            self.emojis[emoji_name] = discord.utils.find(lambda e: e.name==emoji_name, creampie_guild.emojis)

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

    @doll.group()
    @checks.owner_only()
    async def update(self, ctx):
        pass

    @update.command(aliases=["all"])
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

    @update.command()
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
        params = {
            "action":       "parse",
            "prop":         "wikitext",
            "page":         name,
            "format":       "json",
            "redirects":    1
        }
        bytes_ = await self.bot.fetch(GFWIKI_API, params=params)
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
        doll.full_name = basic_info["fullname"]
        doll.en_name = basic_info.get("releasedon", "").strip(" ,")
        doll.aliases = doll.name
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

        doll.mobility = int(basic_info.get("mov", MOBILITY[dtype]))
        doll.craft_time = timer_to_seconds(basic_info.get("craft", ""))
        doll.crit_rate = utils.to_int(basic_info.get("crit", "").rstrip("%"), default=CRIT_RATE[dtype])
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
        print(basic_info.get("use_armor-piercing_pmmo", False))

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
        params = {
            "action":       "parse",
            "prop":         "wikitext",
            "page":         doll.name + "/skilldata",
            "format":       "json",
            "redirects":    1
        }
        bytes_ = await self.bot.fetch(GFWIKI_API, params=params)
        raw_skilldata = json.loads(bytes_)
        doll.skill = parser.parse(raw_skilldata["parse"]["wikitext"]["*"])[0]

        # mod 3 skill
        if doll.moddable:
            skill = []
            for path in ("/skilldata/mod1", "/skill2data"):
                params = {
                    "action":       "parse",
                    "prop":         "wikitext",
                    "page":         doll.name + path,
                    "format":       "json",
                    "redirects":    1
                }
                bytes_ = await self.bot.fetch(GFWIKI_API, params=params)
                raw_skilldata = json.loads(bytes_)
                skill.append(parser.parse(raw_skilldata["parse"]["wikitext"]["*"])[0])
            mod["skill"] = skill

        # skin section
        file_list = {
            f"File:{doll.name}.png": (0, "default", "normal"),
            f"File:{doll.name} D.png": (0, "default", "damaged")
        }
        number = 0
        while True:
            number += 1
            next_costume = f"costume{number}"
            costume_name = basic_info.get(next_costume)
            if costume_name:
                file_list[f"File:{doll.name}_{next_costume}.png"] = (number, costume_name, "normal")
                file_list[f"File:{doll.name}_{next_costume}_D.png"] = (number, costume_name, "damaged")
            else:
                break

        file_params = {
            "action":       "query",
            "prop":         "imageinfo",
            "iiprop":       "url",
            "titles":       "|".join(file_list.keys()),
            "format":       "json",
            "redirects":    1
        }
        file_bytes_ = await self.bot.fetch(GFWIKI_API, params=file_params)
        file_data = json.loads(file_bytes_)

        for n in file_data["query"].get("normalized", []):
            file_list[n["to"]] = file_list[n["from"]]

        skins = []
        mod_skins = []
        for file_info in file_data["query"]["pages"].values():
            if "imageinfo" in file_info:
                url = file_info["imageinfo"][0]["url"]
                info = file_list[file_info["title"]]
                skin = {
                    "index": info[0],
                    "name": info[1],
                    "form": info[2],
                    "image_url": url
                }
                if info[1] == "[Digimind Upgrade]":
                    mod_skins.append(skin)
                else:
                    skins.append(skin)

        skins.sort(key=lambda x: (-x["index"], x["form"]), reverse=True)
        doll.skins = skins
        mod["skins"] = mod_skins
        doll.mod_data = mod

        return doll

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
        },
        multiline=True
    )=modding.EMPTY):
        '''
            `>>doll filter <criteria>`
            Find all T-dolls with criteria.
            Criteria can contain multiple lines, each with format `attribute=value`, or `attribute>value`/`attribute<value` if applicable.
            Available attributes:
            (TBA since it's long and I'm lazy, but it should be stuff like hp, fp, acc, eva, rof, artist...)
        '''
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
                embed.add_field(name="Name", value=d["name"])
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

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(GirlsFrontline(bot))
