import discord
from discord.ext import commands
from urllib.parse import quote
from . import utils
from .utils import config, checks, token, data_type, modding
import random
import re
import traceback
from bs4 import BeautifulSoup as BS
from apiclient.discovery import build
import asyncio
from pymongo import ReturnDocument, UpdateOne, ASCENDING
import json
import math

#==================================================================================================================================================
SPECIAL = {
    "Commander Yashichi": ("Yashichi", "Commander"),
    "Earth Defense Force: Helium": ("Helium Elf", "Earth Defense Force")
}

#==================================================================================================================================================

class Daemon(data_type.BaseObject):
    @classmethod
    def empty(cls, id):
        return cls({
            "id": id, "name": None, "alias": None, "form": None, "url": None, "pic_url": None, "artwork_url": None, "max_atk": 0, "max_hp": 0,
            "mlb_atk": None, "mlb_hp": None, "rarity": 0, "daemon_type": None, "daemon_class": None, "skills": [], "abilities": [], "bonds": [],
            "faction": None, "voice_actor": None, "illustrator": None, "description": None, "how_to_acquire": None, "notes_and_trivia": None,
            "quotes": {"main": {}, "skill": {}, "summon": {}, "limit_break": {}}
        })

    @classmethod
    def from_infobox(cls, *args, **kwargs):
        #basic info
        daemon = cls.empty(None)
        daemon.form = kwargs.get("version")
        daemon.max_atk = utils.to_int(kwargs.get("final atk"), default=0)
        daemon.max_hp = utils.to_int(kwargs.get("final hp"), default=0)
        daemon.rarity = utils.to_int(kwargs.get("rarity"), default=0)
        daemon.mlb_atk = utils.to_int(kwargs.get("lb atk"), default=mlb_stat(max=daemon.max_atk, rarity=daemon.rarity))
        daemon.mlb_hp = utils.to_int(kwargs.get("lb hp"), default=mlb_stat(max=daemon.max_hp, rarity=daemon.rarity))
        daemon.daemon_type = kwargs.get("type").lower()
        daemon.daemon_class = kwargs.get("class").lower()

        #skill, abilities and special bonds
        daemon.skills.append({
            "name": kwargs.get("skill"),
            "effect": kwargs.get("skill info")
        })
        order = ("", 2)
        for o in order:
            abi_name = kwargs.get(f"ability{o}")
            abi_effect = kwargs.get(f"ability info{o}")
            if abi_name and abi_effect:
                unlock = kwargs.get(f"unlock level{o}", "?")
                daemon.abilities.append({
                    "name": f"{abi_name} (Lv. {unlock})",
                    "effect": abi_effect
                })
            bond_name = kwargs.get(f"bond{o}")
            if bond_name:
                daemon.bonds.append({
                    "name": strip_ref(bond_name),
                    "effect": kwargs.get(f"bond info{o}")
                })

        #additional info
        daemon.voice_actor = kwargs.get("va") or None
        daemon.illustrator = kwargs.get("illustrator") or None
        daemon.description = strip_ref(strip_html(kwargs.get("description", ""))) or None
        daemon.how_to_acquire = strip_ref(strip_html(kwargs.get("acquire", "")).strip(";")) or None
        daemon.notes_and_trivia = strip_ref(strip_html(kwargs.get("info", ""))) or None
        daemon.quotes["main"]["text"] = kwargs.get("caption")
        daemon.quotes["skill"]["text"] = kwargs.get("skill quote")
        daemon.quotes["summon"]["text"] = kwargs.get("summon quote")
        daemon.quotes["limit_break"]["text"] = kwargs.get("lb quote")

        return daemon

    def embed_form(self, cog):
        emojis = cog.emojis
        data_embed = discord.Embed(
            title=f"{emojis.get(self.daemon_type, '')} #{self.id} {self.name}",
            description=
                f"{emojis.get(self.daemon_class, '')} | {str(emojis['star'])*self.rarity}\n"
                f"{emojis['atk']}{self.atk}\n{emojis['hp']}{self.hp}"
                "\n----------------------------------------------------------------------------------",
            colour=discord.Colour.orange()
        )
        check = len(self.skills) + len(self.abilities) + len(self.bonds) - 1
        field_list = ("skills", "abilities", "bonds")
        for index, key in enumerate(("skill", "ability", "bond")):
            field = field_list[index]
            try:
                data = getattr(self, field)
                for stuff in data[:-1]:
                    data_embed.add_field(name=f"{emojis[key]}{stuff['name']}", value=stuff["effect"], inline=False)
                    check -= 1
                if check > 0:
                    data_embed.add_field(name=f"{emojis[key]}{data[-1]['name']}", value=f"{data[-1]['effect']}\n----------------------------------------------------------------------------------", inline=False)
                else:
                    data_embed.add_field(name=f"{emojis[key]}{data[-1]['name']}", value=data[-1]["effect"], inline=False)
                check -= 1
            except:
                pass
        return data_embed

    def more_info(self, cog):
        description = self.description or "--"
        des = description.partition(".")
        data_embed = discord.Embed(
            title=f"Wikia: {self.name}",
            description=f"***{des[0]}.***{des[2]}",
            url=getattr(self, "url", None) or discord.Embed.Empty,
            colour=discord.Colour.orange()
        )
        data_embed.add_field(name="Voice Actor", value=self.voice_actor or "--")
        data_embed.add_field(name="Illustrator", value=self.illustrator or "--")
        data_embed.add_field(name="How to Acquire", value=self.how_to_acquire or "--", inline=False)
        data_embed.add_field(name="Notes & Trivia", value=self.notes_and_trivia or "--", inline=False)
        quotes = self.quotes
        data_embed.add_field(
            name="Quotes",
            value=
                f"Main: [\"{quotes['main'].get('text')}\"]({quotes['main'].get('url')})\n"
                f"Skill: [\"{quotes['skill'].get('text')}\"]({quotes['skill'].get('url')})\n"
                f"Summon: [\"{quotes['summon'].get('text')}\"]({quotes['summon'].get('url')})\n"
                f"Limit break: [\"{quotes['limit_break'].get('text')}\"]({quotes['limit_break'].get('url')})\n",
            inline=False
        )
        return data_embed

    @property
    def atk(self):
        if self.mlb_atk:
            return f"{self.max_atk}/{self.mlb_atk}"
        else:
            return self.max_atk or "?"

    @property
    def hp(self):
        if self.mlb_hp:
            return f"{self.max_hp}/{self.mlb_hp}"
        else:
            return self.max_hp or "?"

    @property
    def true_artwork_url(self):
        if self.artwork_url:
            return self.artwork_url
        else:
            return config.NO_IMG

    @property
    def true_image_url(self):
        if self.pic_url:
            return self.pic_url
        else:
            return config.NO_IMG

    @property
    def skill(self):
        if self.skills:
            return ": ".join(self.skills[0].values())
        else:
            return ""

    @skill.setter
    def skill(self, value):
        if self.skills:
            self.skills[0] = value
        else:
            self.skills.append(value)

    @property
    def ability1(self):
        if self.abilities:
            return ": ".join(self.abilities[0].values())
        else:
            return ""

    @ability1.setter
    def ability1(self, value):
        if self.abilities:
            self.abilities[0] = value
        else:
            self.abilities.append(value)

    @property
    def ability2(self):
        if len(self.abilities) > 1:
            return ": ".join(self.abilities[1].values())
        else:
            return ""

    @ability2.setter
    def ability2(self, value):
        number_of_abilities = len(self.abilities)
        if number_of_abilities > 1:
            self.abilities[1] = value
        elif number_of_abilities == 0:
            self.abilities.append(value)
        else:
            raise Exception("You can't set ability 2 when there's no ability 1.")

    @property
    def bond1(self):
        if self.bonds:
            return ": ".join(self.bonds[0].values())
        else:
            return ""

    @bond1.setter
    def bond1(self, value):
        if self.bonds:
            self.bonds[0] = value
        else:
            self.bonds.append(value)

    @property
    def bond2(self):
        if self.bonds:
            return ": ".join(self.bonds[0].values())
        else:
            return ""

    @bond2.setter
    def bond2(self, value):
        number_of_bonds = len(self.bonds)
        if number_of_bonds > 1:
            self.bonds[1] = value
        elif number_of_bonds == 0:
            self.bonds.append(value)
        else:
            raise Exception("You can't set bond 2 when there's no bond 1.")

#==================================================================================================================================================

ref_regex = re.compile(r"\[\[(.+?\]?)\]\]")
def left_most(m):
    sp = m.group(1).rpartition("|")
    return sp[2]

def strip_ref(text):
    return ref_regex.sub(left_most, text).strip()

no_multi_linebreak = re.compile(r"\n\n+")
def strip_html(text):
    soup = BS(text, "lxml")
    return no_multi_linebreak.sub("\n", soup.get_text().strip("; \n\t\r")).replace("\n:", "\n\u2022")

def to_str(func):
    def new_func(*args, **kwargs):
        return str(func(*args, **kwargs))
    return new_func

def nothing(*args, **kwargs):
    return None

def min_stat(max):
    value = int(max)
    r = value % 3
    if r == 0:
        return value // 3
    elif r == 1:
        return int(round(value/3, -1))
    else:
        return int(round(value/3, -1)) - 5

def mlb_stat(*, max, rarity, level_inc=0):
    value = int(max)
    rarity = int(rarity)
    min_value = min_stat(value)
    return int(round(value+(20+level_inc)*(value-min_value)/(19+10*rarity)))

def mlb_skill(*, skill, rarity, level_inc=0):
    rarity = int(rarity)
    if skill.endswith("%"):
        value = int(skill[:-1])
        return str(value+int(round((20+level_inc)*(value-int(value/3))/(19+10*rarity)))) + "%" #inaccurate, but this will do for now
    else:
        value = int(skill)
        return value + (20 + level_inc) * int(round(value*2/3/(19+10*rarity)))

def parse_curly(text_generator):
    try:
        next_char = next(text_generator)
    except StopIteration:
        return "{"
    if next_char != "{":
        return "{" + next_char
    else:
        args = []
        kwargs = {}
        value = []
        key = None
        ref = 0
        while True:
            next_char = next(text_generator)
            if next_char == "{":
                value.append(parse_curly(text_generator))
            elif next_char == "=":
                if key is None:
                    key = "".join(value).strip().lower()
                    value.clear()
                else:
                    value.append(next_char)
            elif next_char == "|":
                if ref >= 2:
                    value.append(next_char)
                else:
                    if key is None:
                        args.append("".join(value).strip())
                    else:
                        kwargs[key] = "".join(value).strip()
                    value.clear()
                    key = None
            elif next_char == "}":
                next_char = next(text_generator)
                if next_char != "}":
                    value.append("}"+next_char)
                else:
                    if value:
                        if key is None:
                            args.append("".join(value).strip())
                        else:
                            kwargs[key] = "".join(value).strip()
                    name = args.pop(0)
                    return INFOBOX_FUNCS.get(name.lower(), nothing)(*args, **kwargs)
            elif next_char == "[":
                value.append(next_char)
                ref = ref + 1
            elif next_char == "]":
                value.append(next_char)
                ref = ref - 1
            else:
                value.append(next_char)

def return_kwargs(*args, **kwargs):
    return (Daemon.from_infobox(*args, **kwargs), kwargs)

INFOBOX_FUNCS = {
    "infobox daemon": return_kwargs,
    "mlb": to_str(mlb_stat),
    "min": to_str(min_stat),
    "ashla": to_str(mlb_skill),
    "trim": lambda x: x,
    "namer": lambda x, y: x
}

#==================================================================================================================================================

class Otogi:
    '''
    Otogi daemon info and summon simulation.
    '''

    def __init__(self, bot):
        self.bot = bot

        db = bot.db
        self.daemon_collection = db.daemon_collection
        self.summon_pool = db.daemon_summon_pool
        self.player_list = db.otogi_simulation_player_list
        self.google_sheets = build("sheets", "v4", developerKey=token.GOOGLE_CLIENT_API_KEY)
        self.stat_sheet = db.otogi_effective_stats_sheet
        self.belphegor_config = db.belphegor_config

        creampie_guild = self.bot.get_guild(config.CREAMPIE_GUILD_ID)
        self.emojis = {}
        for emoji_name in (
            "atk", "hp", "skill", "ability", "bond", "star", "mochi", "phantasma",
            "anima", "divina", "ranged", "melee", "healer", "assist"
        ):
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, creampie_guild.emojis)

        self.lock = asyncio.Lock()

    async def _search(self, ctx, name, *, prompt=None):
        return await ctx.search(
            name, self.daemon_collection,
            cls=Daemon, colour=discord.Colour.orange(), atts=["id", "name", "alias", "form"], name_att="name", emoji_att="daemon_class", prompt=prompt, sort={"id": 1}
        )

    @modding.help(brief="Check a daemon info", category="Otogi", field="Database", paragraph=0)
    @commands.group(name="daemon", aliases=["d"], invoke_without_command=True)
    async def cmd_daemon(self, ctx, *, name: str):
        '''
            `>>daemon <name>`
            Display a daemon info.
        '''
        daemon = await self._search(ctx, name)
        if not daemon:
            return

        paging = utils.Paginator([])

        info_embed = daemon.embed_form(self)
        paging.set_action("\U0001f1e9", lambda: info_embed)
        trivia_embed = daemon.more_info(self)
        paging.set_action("\U0001f1f9", lambda: trivia_embed)
        if daemon.artwork_url:
            artwork = discord.Embed(colour=discord.Colour.orange())
            artwork.set_image(url=daemon.artwork_url)
            paging.set_action("\U0001f5bc", lambda: artwork)

        empty_embed = discord.Embed(colour=discord.Colour.orange())
        paging.set_action("\U0001f53c", lambda: empty_embed)

        image = discord.Embed(colour=discord.Colour.orange())
        image.set_image(url=daemon.true_image_url)
        await ctx.send(embed=image)
        await paging.navigate(ctx)

    async def _search_att(self, attrs):
        result = []
        query = {}
        projection = {"_id": False, "id": True, "name": True}
        for attr in attrs:
            orig_att = attr[0]
            value = attr[1]
            try:
                re_value = int(value)
                if orig_att == "atk":
                    att = "max_atk"
                elif orig_att == "hp":
                    att = "max_hp"
                else:
                    att = orig_att
                q = {att: re_value}
                p = {att: True}
            except:
                re_value = ".*?".join(map(re.escape, value.split()))
                p = None
                if orig_att in ("va", "seiyuu"):
                    att = "voice_actor"
                elif orig_att in ("illu", "artist"):
                    att = "illustrator"
                elif orig_att in ("how", "acquire", "get"):
                    att = "how_to_acquire"
                elif orig_att in ("trivia", "note", "notes"):
                    att = "notes_and_trivia"
                elif orig_att == "desc":
                    att = "description"
                elif orig_att == "class":
                    att = "daemon_class"
                elif orig_att == "type":
                    att = "daemon_type"
                elif orig_att == "skill":
                    att = "skills"
                    p = {"skills.$": True}
                elif orig_att in ("abi", "ability"):
                    att = "abilities"
                    p = {"abilities.$": True}
                elif orig_att == "bond":
                    att = "bonds"
                    p = {"bonds.$": True}
                else:
                    att = orig_att
                if p:
                    q = {
                        att: {
                            "$elemMatch": {
                                "$or": [
                                    {
                                        "name": {
                                            "$regex": re_value,
                                            "$options": "i"
                                        }
                                    },
                                    {
                                        "effect": {
                                            "$regex": re_value,
                                            "$options": "i"
                                        }
                                    }
                                ]
                            }
                        }
                    }
                else:
                    q = {att: {"$regex": re_value, "$options": "i"}}
                    p = {att: True}
            query.update(q)
            projection.update(p)

        async for daemon in self.daemon_collection.find(query, projection=projection, sort=[("id", 1)]):
            new_daemon = {}
            new_daemon["id"] = daemon.pop("id")
            new_daemon["name"] = daemon.pop("name")
            r = ""
            for key, value in daemon.items():
                while value:
                    if isinstance(value, list):
                        value = value[0]
                    else:
                        break
                if isinstance(value, dict):
                    value = f"{value['name']}: {value['effect']}"
                try:
                    if len(value) > 200:
                        value = f"{value[:200]}..."
                except:
                    pass
                r = f"{r}\n   {key}: {value}"
            new_daemon["value"] = r
            result.append(new_daemon)
        return result

    @modding.help(brief="Find daemons with given conditions", category="Otogi", field="Database", paragraph=0)
    @cmd_daemon.command(name="filter")
    async def cmd_daemon_filter(self, ctx, *, data):
        '''
            `>>daemon filter <criteria>`
            Find all daemons with <criteria>.
            Criteria can contain multiple lines, each with format `<attribute> <value>`
            Available attributes:
            - name
            - alias
            - rarity
            - type
            - class
            - max_atk
            - max_hp
            - mlb_atk
            - mlb_hp
            - skill
            - ability
            - bond
            - faction
            - voice_actor
            - illustrator
            - how_to_acquire
            - notes_and_trivia
            - description
        '''
        data = data.strip().splitlines()
        attrs = []
        for d in data:
            stuff = d.partition(" ")
            attrs.append((stuff[0].lower(), stuff[2].lower()))
        result = await self._search_att(attrs)
        if result:
            paging = utils.Paginator(
                result, 5, separator="\n\n",
                title=f"Search result: {len(result)} results",
                description=lambda i, x: f"`#{x['id']}` **{x['name']}**{x['value']}",
                colour=discord.Colour.orange()
            )
            await paging.navigate(ctx)
        else:
            await ctx.send("No result found.")

    @commands.group()
    async def update(self, ctx):
        '''
            `>>update`
            Base command. Does nothing significant.
        '''
        if ctx.invoked_subcommand is None:
            pass

    @update.command()
    @checks.owner_only()
    async def create(self, ctx, *, data:str):
        '''
            `>>update create <data>`
            Create a daemon with the input data.
            Data can contains multiple lines, each with format `<attribute> <value>`
            Normally it's advised to create a daemon with name and maybe alias, then update via wikia later.
        '''
        cur_index = 1
        all_values = await self.daemon_collection.distinct("id", {})
        while cur_index in all_values:
            cur_index += 1
        data = [d.strip() for d in data.splitlines() if d]
        try:
            new_daemon = Daemon.empty(cur_index)
            new_daemon.name = data[0]
            if len(data) == 1:
                new_daemon.alias = new_daemon.name
            else:
                new_daemon.alias = data[1]
            try:
                new_daemon.max_atk = data[2]
                new_daemon.max_hp = data[3]
            except:
                pass
            for i, d in enumerate(data):
                if i > 3 and i%2 == 0:
                    if ">" in d:
                        new_daemon.bonds.append((d, data[i+1]))
                    elif "(Lv" in d:
                        new_daemon.abilities.append((d, data[i+1]))
                    else:
                        new_daemon.skills.append((d, data[i+1]))
            await self.daemon_collection.insert_one(new_daemon.__dict__)
            await ctx.send(f"Entry #{new_daemon.id} has been created.")
        except Exception as e:
            print(e)
            await ctx.send("Wrong format.")

    @update.command(hidden=True)
    @checks.owner_only()
    async def delete(self, ctx, *, name):
        daemon = await self._search(ctx, name, prompt=True)
        if not daemon:
            return
        await self.daemon_collection.find_one_and_delete({"id": daemon.id})
        await ctx.send(f"The entry for {daemon.name} has been deleted.")

    @update.command(hidden=True)
    @checks.owner_only()
    async def edit(self, ctx, *, data):
        data = data.strip().partition("\n")
        daemon = await self._search(ctx, data[0], prompt=True)
        if not daemon:
            return
        field, sep, value = data[2].partition(" ")
        if field.lower() in (
            "name", "alias", "pic_url", "artwork_url", "max_atk", "max_hp", "mlb_atk", "mlb_hp", "rarity",
            "daemon_type", "daemon_class", "skill", "ability1", "ability2", "bond1", "bond2", "faction"
        ):
            try:
                if field.lower() in ("skill", "ability1", "ability2", "bond1", "bond2"):
                    value = value.partition("\n")
                    value = {"name": value[0], "effect": value[2]}
            except:
                return await ctx.send("Provided data is lacking.")
            try:
                value = int(value)
            except:
                pass
            try:
                if value:
                    setattr(daemon, field, value)
                else:
                    setattr(daemon, field, None)
            except Exception as e:
                return await ctx.send(e)
            await self.daemon_collection.replace_one({"id": daemon.id}, daemon.__dict__)
            await ctx.send(f"The entry for {daemon.name} has been edited.")
        else:
            await ctx.send(f"No field {field} found.")

    @update.command(hidden=True, name="summon")
    @checks.owner_only()
    async def _summon(self, ctx, *, name):
        daemon = await self._search(ctx, name, prompt=True)
        if not daemon:
            return
        if daemon.rarity in (3, 4, 5):
            update_result = await self.summon_pool.update_one({"rarity": daemon.rarity}, {"$addToSet": {"pool": daemon.id}})
            if update_result.modified_count > 0:
                await ctx.send(f"The daemon {daemon.name} has been added to summon pool.")
            else:
                await ctx.send(f"The daemon {daemon.name} is already in summon pool.")
        else:
            await ctx.send(f"You can't add {daemon.rarity}* daemon to pool.")

    @update.command(hidden=True)
    @checks.owner_only()
    async def nosummon(self, ctx, *, name):
        daemon = await self._search(ctx, name, prompt=True)
        if not daemon:
            return
        update_result = await self.summon_pool.update_one({"rarity": daemon.rarity}, {"$pull": {"pool": daemon.id}})
        if update_result.modified_count > 0:
            await ctx.send(f"The daemon {daemon.name} has been removed from summon pool.")
        else:
            await ctx.send(f"The daemon {daemon.name} is not in summon pool.")

    @update.command(aliases=["wiki"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def wikia(self, ctx, *, name):
        '''
            `>>update wikia <name>`
            Update daemon info with the infomation from wikia.
        '''
        daemon = await self._search(ctx, name, prompt=True)
        if not daemon:
            return
        await ctx.trigger_typing()
        new_daemon = await self.search_wikia(daemon)
        if new_daemon:
            await self.daemon_collection.replace_one({"id": daemon.id}, new_daemon.__dict__)
            await ctx.send(f"The entry for {new_daemon.name} has been updated with latest information from wikia.")
        else:
            await ctx.send("No wikia page found.")

    async def search_wikia(self, daemon):
        name = daemon.name
        alias = daemon.alias
        try:
            bracket_index = name.index("[")
        except ValueError:
            base_name = name
            form = "original"
        else:
            base_name = name[:bracket_index-1]
            form = name[bracket_index+1:-1]

        #wikia search
        base_name, form = SPECIAL.get(base_name, (base_name, form))
        params = {
            "action":       "parse",
            "prop":         "wikitext",
            "page":         quote(base_name),
            "format":       "json",
            "redirects":    1
        }
        bytes_ = await self.bot.fetch("https://otogi.wikia.com/api.php", params=params)
        data = json.loads(bytes_)
        text_generator = iter(data["parse"]["wikitext"]["*"])
        new_daemon = None
        while True:
            try:
                current_char = next(text_generator)
            except StopIteration:
                raise checks.CustomError("No info found.")
            else:
                if current_char == "{":
                    ret = parse_curly(text_generator)
                    if isinstance(ret, tuple):
                        new_daemon, kwargs = ret
                        if isinstance(new_daemon, Daemon) and new_daemon.form == form:
                            break

        new_daemon.id = daemon.id
        new_daemon.name = daemon.name
        new_daemon.alias = daemon.alias
        new_daemon.faction = daemon.faction
        new_daemon.url = f"https://otogi.wikia.com/wiki/{quote(base_name)}"

        filename_base = kwargs.get("image name") or name.replace("[", "").replace("]", "").replace(":", "")
        files = {
            "pic":                  f"File:{filename_base}.png",
            "artwork":              f"File:{filename_base} Artwork.png",
            "main_quote":           f"File:{filename_base} Main.ogg",
            "skill_quote":          f"File:{filename_base} Skill.ogg",
            "summon_quote":         f"File:{filename_base} Summon.ogg",
            "limit_break_quote":    f"File:{filename_base} Limit Break.ogg"
        }
        rev = {v: k for k, v in files.items()}
        file_params = {
            "action":   "query",
            "prop":     "imageinfo",
            "iiprop":   "url",
            "titles":   "|".join(files.values()),
            "format":   "json"
        }
        file_bytes_ = await self.bot.fetch("https://otogi.wikia.com/api.php", params=file_params)
        file_data = json.loads(file_bytes_)
        file_urls = {}
        for n in file_data["query"].get("normalized", []):
            files[rev[n["from"]]] = n["to"]

        rev = {v: k for k, v in files.items()}
        for d in file_data["query"]["pages"].values():
            if d["title"] in rev:
                try:
                    file_urls[rev[d["title"]]] = d["imageinfo"][0]["url"]
                except (IndexError, KeyError):
                    pass

        new_daemon.pic_url = file_urls.get("pic")
        new_daemon.artwork_url = file_urls.get("artwork")
        new_daemon.quotes["main"]["url"] = file_urls.get("main_quote")
        new_daemon.quotes["skill"]["url"] = file_urls.get("skill_quote")
        new_daemon.quotes["summon"]["url"] = file_urls.get("summon_quote")
        new_daemon.quotes["limit_break"]["url"] = file_urls.get("limit_break_quote")

        return new_daemon

    @update.command(hidden=True, name="from", aliases=["all"])
    @checks.owner_only()
    async def update_everything(self, ctx, start_from: int=0):
        done = []
        undone = []

        msg = await ctx.send(f"Fetching...\n{utils.progress_bar(0)}")
        cursor = self.daemon_collection.find({"id": {"$gte": start_from}})
        daemons = await cursor.to_list(None)
        if daemons:
            count = len(daemons)
            i = 0
            for daemon_data in daemons:
                try:
                    daemon = Daemon(daemon_data)
                    new_daemon = await self.search_wikia(daemon)
                    await self.daemon_collection.replace_one({"id": daemon.id}, new_daemon.__dict__)
                except:
                    undone.append(f"#{daemon.id: 4d} {daemon.name}")
                else:
                    done.append(f"#{new_daemon.id: 4d} {new_daemon.name}")
                i += 1
                if i%10 == 0:
                    await msg.edit(content=f"Fetching...\n{utils.progress_bar(i/count)}")

            await msg.edit(content=f"Done.\n{utils.progress_bar(i/count)}")
            txt = json.dumps({"done": done, "undone": undone}, indent=4, ensure_ascii=False)
            if len(txt) > 1900:
                await ctx.send(f"Done: {len(done)}\nUndone: {len(undone)}", file=discord.File(txt.encode("utf-8"), filename="result.json"))
            else:
                await ctx.send(f"Done: {len(done)}\nUndone: {len(undone)}\n```json\n{txt}\n```")
        else:
            await ctx.send("There's nothing to update.")

    @update.command(hidden=True, name="one")
    @checks.owner_only()
    async def update_one(self, ctx, *, name):
        cmd_create = self.bot.get_command("update create")
        cmd_wikia = self.bot.get_command("update wikia")
        await ctx.invoke(cmd_create, data=name)
        d = await self.daemon_collection.find_one({"name": name}, projection={"id": True})
        await ctx.invoke(cmd_wikia, name=str(d["id"]))

    async def get_player(self, id):
        async with self.lock:
            return await self.player_list.find_one_and_update(
                {"id": id},
                {"$setOnInsert": {"id": id, "mochi": 0, "daemons": []}},
                return_document=ReturnDocument.AFTER,
                upsert=True
            )

    async def batch_search(self, id_list):
        return {daemon["id"]: daemon async for daemon in self.daemon_collection.find({"id": {"$in": id_list}}, projection={"_id": False, "id": True, "name": True, "rarity": True})}

    @commands.group(aliases=["ls"])
    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    async def lunchsummon(self, ctx):
        '''
            `>>lunchsummon`
            Lunch summon simulation.
            The result is collected in mybox feature.
        '''
        if ctx.invoked_subcommand is None:
            id = ctx.author.id
            player = await self.get_player(id)
            roll = random.randint(1, 100)
            if 0 < roll <= 4:
                rarity = 5
            elif 4 < roll <= 22:
                rarity = 4
            else:
                rarity = 3
            pool = await self.summon_pool.find_one({"rarity": rarity})
            daemon_id = random.choice(pool["pool"])
            await self.player_list.find_one_and_update({"id": id}, {"$push": {"daemons": {"$each": [{"id": daemon_id, "lb": 0}], "$sort": {"id": 1, "lb": -1}}}})
            daemon = await ctx.search(daemon_id, self.daemon_collection, cls=Daemon, atts=["id"], name_att="name", prompt=False)
            embed = discord.Embed(title=f"{ctx.author.display_name} summoned {daemon.name}!", colour=discord.Colour.orange())
            scale_url = daemon.true_image_url
            data = scale_url.split("?cb=")
            try:
                code = data[2].partition("&")
                scale_url = f"{data[0]}/scale-to-width-down/250?cb={code[0]}"
            except IndexError:
                pass
            embed.set_image(url=scale_url)
            await ctx.send(embed=embed)

    @lunchsummon.command()
    async def till(self, ctx, *, name):
        '''
            `>>ls till <name>`
            Estimate how much ~~salt~~ summons to get a certain daemon.
            Does not count into mybox feature.
        '''
        daemon = await self._search(ctx, name)
        if not daemon:
            return
        pool_data = await self.summon_pool.find_one({"rarity": daemon.rarity})
        if pool_data:
            pool = pool_data["pool"]
        else:
            return await ctx.send(f"Daemon {daemon.name} not in summon pool.")
        for daemon_id in pool:
            if daemon.id == daemon_id:
                break
        else:
            return await ctx.send(f"{daemon.name} is not in summon pool.")
        result = 0
        while True:
            result += 1
            roll = random.randint(1, 100)
            if 0 < roll <= 4:
                rarity = 5
            elif 4 < roll <= 22:
                rarity = 4
            else:
                rarity = 3
            if rarity == daemon.rarity:
                did = random.choice(pool)
                if did == daemon.id:
                    break
        await ctx.send(f"It took {result} summons to get {daemon.name}.")

    @lunchsummon.command(name="pool")
    async def show_summon_pool(self, ctx):
        '''
            `>>lunchsummon pool`
            Show lunch summon pool.
        '''
        summon_pool = [p["pool"] async for p in self.summon_pool.find().sort("rarity")]
        daemons = []
        for pool in summon_pool:
            dp = [d async for d in self.daemon_collection.find({"id": {"$in": pool}}, projection={"_id": False, "id": True, "name": True})]
            daemons.append(dp)
        paging = utils.Paginator(
            daemons, 10, book=True,
            title="Current summon pool:",
            prefix=lambda i, n: str(self.emojis["star"])*(n+3),
            description=lambda i, x, n: x["name"],
            colour=discord.Colour.orange()
        )
        await paging.navigate(ctx)

    @commands.command()
    async def mybox(self, ctx, *, member: discord.Member=None):
        '''
            `>>mybox <optional: member>`
            Show <member>'s box. If no member is provided, show your box instead.
        '''
        target = member or ctx.author
        player = await self.get_player(target.id)
        lbs = {d["id"]: d["lb"] for d in player["daemons"]}
        cur = self.daemon_collection.aggregate([
            {
                "$match": {
                    "id": {
                        "$in": list(lbs.keys())
                    }
                }
            },
            {
                "$bucket": {
                    "groupBy": "$rarity",
                    "boundaries": [3, 4, 5, 6],
                    "output": {
                        "daemons": {
                            "$push": {
                                "name": "$name",
                                "id": "$id"
                            }
                        }
                    }
                }
            }
        ])
        daemons = [pool["daemons"] async for pool in cur]
        if daemons:
            paging = utils.Paginator(
                daemons, 10, book=True,
                author=f"{target.display_name}'s box:",
                author_icon=target.avatar_url,
                title=f"Mochi: {player['mochi']}{self.emojis['mochi']}",
                prefix=lambda i, n: str(self.emojis["star"])*(n+3),
                description=lambda i, x, n: f"{x['name']} lb{lbs[x['id']]}",
                colour=discord.Colour.orange()
            )
            await paging.navigate(ctx)
        else:
            embed = discord.Embed(title=f"Mochi: {player['mochi']}{self.emojis['mochi']}", description="Empty", colour=discord.Colour.orange())
            embed.set_author(name=f"{target.display_name}'s box", icon_url=target.avatar_url)
            await ctx.send(embed=embed)

    def _process_name(self, name):
        if name[-3:] in ("lb0", "lb1", "lb2", "lb3", "lb4"):
            lb = int(name[-1:])
            name = name[:-4]
        else:
            lb = 0
        return (name, lb)

    def mochi_cost(self, daemon):
        r = getattr(daemon, "rarity", None)
        if r is None:
            r = daemon.get("rarity", 0)
        if r == 3:
            return 1
        elif r == 4:
            return 5
        elif r == 5:
            return 25
        else:
            return 0

    @commands.group(invoke_without_command=True)
    async def mochi(self, ctx, *, names):
        '''
            `>>mochi <list of names>`
            Sell daemon(s).
            Names are separated by `;`
            You can attach `lb?` to the end of a name to choose a daemon with certain limit break level.
        '''
        player = await self.get_player(ctx.author.id)
        names = [n.strip() for n in names.split(";")]
        number_of_daemons = 0
        total_mochi = 0
        for raw_name in names:
            name, lb = self._process_name(raw_name)
            daemon = await self._search(ctx, name, prompt=False)
            if not daemon:
                continue
            for i, d in enumerate(player["daemons"]):
                if d["id"] == daemon.id and d["lb"] == lb:
                    index = i
                    break
            else:
                continue
            player["daemons"].pop(index)
            number_of_daemons += 1
            total_mochi += self.mochi_cost(daemon) * (lb + 1)
        await self.player_list.update_one({"id": ctx.author.id}, {"$inc": {"mochi": total_mochi}, "$set": {"daemons": player["daemons"]}})
        await ctx.send(f"{ctx.author.display_name} sold {number_of_daemons} daemon(s) for {total_mochi}{self.emojis['mochi']}.\n{len(names)-number_of_daemons} failed.")

    @mochi.command()
    async def bulk(self, ctx, *, names):
        '''
            `>>mochi bunk <list of names>`
            Sell all daemons with <names>.
            Names are separated by `;`
        '''
        player = await self.get_player(ctx.author.id)
        names = [n.strip() for n in names.split(";")]
        number_of_daemons = 0
        total_mochi = 0
        for raw_name in names:
            name, lb = self._process_name(raw_name)
            daemon = await self._search(ctx, name, prompt=False)
            if not daemon:
                continue
            i = 0
            while i < len(player["daemons"]):
                d = player["daemons"][i]
                if d["id"] == daemon.id:
                    target = player["daemons"].pop(i)
                    number_of_daemons += 1
                    total_mochi += self.mochi_cost(daemon) * (target["lb"] + 1)
                else:
                    i += 1
        await self.player_list.update_one({"id": ctx.author.id}, {"$inc": {"mochi": total_mochi}, "$set": {"daemons": player["daemons"]}})
        await ctx.send(f"{ctx.author.display_name} sold {number_of_daemons} daemon(s) for {total_mochi}{self.emojis['mochi']}.")

    @mochi.command()
    async def all(self, ctx, rarity: int):
        '''
            `>>mochi all <rarity>`
            Sell all daemons with <rarity>.
        '''
        player = await self.get_player(ctx.author.id)
        daemons = await self.batch_search([d["id"] for d in player["daemons"]])
        total_mochi = 0
        i = 0
        while i < len(player["daemons"]):
            d = player["daemons"][i]
            dm = daemons[d["id"]]
            if dm["rarity"] == rarity:
                target = player["daemons"].pop(i)
                total_mochi += self.mochi_cost(dm) * (d["lb"] + 1)
            else:
                i += 1
        await self.player_list.update_one({"id": ctx.author.id}, {"$inc": {"mochi": total_mochi}, "$set": {"daemons": player["daemons"]}})
        await ctx.send(f"{ctx.author.display_name} sold all {rarity}* daemons for {total_mochi}{self.emojis['mochi']}.")

    @commands.command()
    async def gift(self, ctx, member: discord.Member, *, name):
        '''
            `>>gift <member> <name>`
            Gift <member> a daemon with <name>.
            You can attach `lb?` to the end of <name> to choose a daemon with certain limit break level.
        '''
        name, lb = self._process_name(name)
        daemon = await self._search(ctx, name, prompt=False)
        if not daemon:
            return
        myself = await self.get_player(ctx.author.id)
        target = await self.get_player(member.id)
        i = 0
        while i < len(myself["daemons"]):
            d = myself["daemons"][i]
            if d["id"] == daemon.id and d["lb"] == lb:
                dm = myself["daemons"].pop(i)
                target["daemons"].append(dm)
                target["daemons"].sort(key=lambda x: (x["id"], -x["lb"]))
                break
            else:
                i += 1
        else:
            return await ctx.send(f"You don't even have {daemon.name} lb{lb}.")
        await self.player_list.bulk_write([
            UpdateOne({"id": myself["id"]}, {"$set": {"daemons": myself["daemons"]}}),
            UpdateOne({"id": target["id"]}, {"$set": {"daemons": target["daemons"]}})
        ])
        await ctx.send(f"{ctx.author.display_name} gave {member.display_name} {daemon.name} lb{dm['lb']}.")

    @commands.command()
    async def gimme(self, ctx, member: discord.Member, *, data):
        '''
            `>>gimme <member> <name> for <number of mochi>`
            Ask <member> to trade a daemon with <name> for a price.
            You can attach `lb?` to the end of <name> to choose a daemon with certain limit break level.
        '''
        data = data.rpartition(" for ")
        price = int(data[2].replace("mochi", "").replace("mc", "").strip(" s"))
        name = data[0].strip()
        name, lb = self._process_name(name)
        daemon = await self._search(ctx, name, prompt=False)
        if not daemon:
            return
        myself = await self.get_player(ctx.author.id)
        target = await self.get_player(member.id)
        i = 0
        if myself["mochi"] < price:
            return await ctx.send("You don't have that many mochis.")
        else:
            while i < len(target["daemons"]):
                d = target["daemons"][i]
                if d["id"] == daemon.id and d["lb"] == lb:
                    sentences = {
                        "initial":  f"Would {member.mention} trade {daemon.name} lb{lb} for {price}{self.emojis['mochi']}?",
                        "yes":      "Trade succeed.",
                        "no":       "Trade failed.",
                        "timeout":  "Timeout, cancelled trading."
                    }
                    check = await ctx.yes_no_prompt(sentences, target=member)
                    if check:
                        dm = target["daemons"].pop(i)
                        myself["daemons"].append(dm)
                        myself["daemons"].sort(key=lambda x: (x["id"], -x["lb"]))
                        break
                    else:
                        return
                else:
                    i += 1
            else:
                return await ctx.send(f"{member.display_name} doesn't have {daemon.name} lb{lb}.")
        await self.player_list.bulk_write([
            UpdateOne({"id": myself["id"]}, {"$set": {"daemons": myself["daemons"]}}),
            UpdateOne({"id": target["id"]}, {"$set": {"daemons": target["daemons"]}})
        ])
        await ctx.send(f"{ctx.author.display_name} gave {member.display_name} {daemon.name} lb{dm['lb']}.")

    def lb_that(self, player, mini_id):
        all_them = [d for d in player["daemons"] if d["id"]==mini_id]
        first = 0
        last = len(all_them) - 1
        while first < last:
            if all_them[first]["lb"] + all_them[last]["lb"] <= 3:
                all_them[first]["lb"] += all_them[last]["lb"] + 1
                player["daemons"].remove(all_them[last])
                all_them.pop(last)
                last -= 1
            else:
                first += 1

    @commands.command(aliases=["lb"])
    async def limitbreak(self, ctx, *, name=None):
        '''
            `>>limitbreak <optional: name>`
            Auto limit break all daemons with <name>.
            If no name is provide, limit break everything.
        '''
        player = await self.get_player(ctx.author.id)
        if name:
            name, lb = self._process_name(name)
            daemon = await self._search(ctx, name, prompt=False)
            if daemon:
                self.lb_that(player, daemon.id)
            else:
                return await ctx.send("Can't find daemon with that name.")
        else:
            all_ids = set([])
            for d in player["daemons"]:
                all_ids.add(d["id"])
            for mid in all_ids:
                self.lb_that(player, mid)
        await self.player_list.update_one({"id": player["id"]}, {"$set": {"daemons": player["daemons"]}})
        await ctx.send("Limit breaking succeed.")

    def get_sheet(self, sheet_id, sheet_range):
        result = self.google_sheets.spreadsheets().values().get(spreadsheetId=sheet_id, range=sheet_range).execute()
        return result

    @update.command(hidden=True, name="sheet")
    @checks.owner_only()
    async def update_sheet(self, ctx):
        result = await self.bot.loop.run_in_executor(None, self.get_sheet, "1oJnQ5TYL5d9LJ04HMmsuXBvJSAxqhYqcggDZKOctK2k", "Sheet1!$A$1:$YY")
        await self.stat_sheet.find_one_and_replace({}, result)
        await ctx.message.add_reaction("\u2705")

    @commands.command(aliases=["nuker"])
    async def nukers(self, ctx):
        '''
            `>>nukers`
            Show nuker (skill damage) ranking.
        '''
        data = await self.stat_sheet.find_one()
        sheet = data["values"]

        headers = sheet[0]
        name_index = headers.index("Name")
        skill_type_index = headers.index("Skill Type")
        skill_dmg_index = headers.index("MLB Effective Skill DMG With Bonds")
        auto_dmg_index = headers.index("MLB True Auto ATK DMG")

        filter_sheet = [s for s in sheet if s[skill_type_index]=="Damage"]
        filter_sheet.sort(key=lambda x: -int(x[skill_dmg_index].replace(",", "")))
        paging = utils.Paginator(
            filter_sheet, 5, separator="\n\n",
            title="Nuker rank",
            description=lambda i, x: f"{i+1}. **{x[name_index]}**\n   MLB Effective Skill DMG: {x[skill_dmg_index]}\n   MLB Auto ATK DMG: {x[auto_dmg_index]}",
            colour=discord.Colour.orange()
        )
        await paging.navigate(ctx)

    @commands.command(aliases=["auto"])
    async def autoattack(self, ctx):
        '''
            `>>autoattack`
            Show auto attack ranking.
        '''
        data = await self.stat_sheet.find_one()
        sheet = data["values"][1:]

        headers = data["values"][0]
        name_index = headers.index("Name")
        class_index = headers.index("Class")
        auto_dmg_index = headers.index("MLB True Auto ATK DMG")

        filter_sheet = [s for s in sheet if s[class_index]!="Healer"]
        filter_sheet.sort(key=lambda x: -int(x[auto_dmg_index].replace(",", "")))
        paging = utils.Paginator(
            filter_sheet, 5, separator="\n\n",
            title="Auto attack rank",
            description=lambda i, x: f"{i+1}. **{x[name_index]}**\n   Class: {x[class_index]}\n   MLB Auto ATK DMG: {x[auto_dmg_index]}",
            colour=discord.Colour.orange()
        )
        await paging.navigate(ctx)

    @commands.command(aliases=["debuffer"])
    async def debuffers(self, ctx):
        '''
            `>>debuffers`
            Show debuffer list.
        '''
        data = await self.stat_sheet.find_one()
        sheet = data["values"]

        headers = sheet[0]
        name_index = headers.index("Name")
        skill_type_index = headers.index("Skill Type")
        skill_effect_index = headers.index("Skill Effect")
        skill_dmg_index = headers.index("MLB Effective Skill DMG With Bonds")
        debuff_value_index = len(headers) - 1 - headers[::-1].index("MLB Value")

        filter_sheet = [s for s in sheet if utils.get_element(s, skill_effect_index)=="Increases DMG Rec'd" or s[skill_type_index]=="Debuff"]
        filter_sheet.sort(key=lambda x: x[0])
        paging = utils.Paginator(
            filter_sheet, 5, separator="\n\n",
            title="Debuffer list",
            description=
                lambda i, x:
                    f"{i+1}. **{x[name_index]}**\n   MLB Debuff Value: {utils.get_element(x, debuff_value_index) or 'N/A'}\n"
                    f"   MLB Effective Skill DMG: {x[skill_dmg_index]}\n   Skill Effect: {utils.get_element(x, skill_effect_index) or 'N/A'}",
            colour=discord.Colour.orange()
        )
        await paging.navigate(ctx)

    @commands.command(aliases=["buffer"])
    async def buffers(self, ctx):
        '''
            `>>buffers`
            Show buffer list.
        '''
        data = await self.stat_sheet.find_one()
        sheet = data["values"]

        headers = sheet[0]
        name_index = headers.index("Name")
        skill_type_index = headers.index("Skill Type")
        skill_effect_index = headers.index("Skill Effect")
        buff_value_index = len(headers) - 1 - headers[::-1].index("MLB Value")

        filter_sheet = [s for s in sheet if s[skill_type_index]=="Buff"]
        filter_sheet.sort(key=lambda x: x[0])
        paging = utils.Paginator(
            filter_sheet, 5, separator="\n\n",
            title="Buffer list",
            description=
                lambda i, x:
                    f"{i+1}. **{x[name_index]}**\n   MLB Buff Value: {utils.get_element(x, buff_value_index) or 'N/A'}\n"
                    f"   Skill Effect: {utils.get_element(x, skill_effect_index) or 'N/A'}",
            colour=discord.Colour.orange()
        )
        await paging.navigate(ctx)

    @commands.command()
    async def gcqstr(self, ctx):
        '''
            `>>gcqstr`
            Show Guild Conquest STR ranking.
        '''
        cur = self.daemon_collection.aggregate([
            {
                "$project": {
                    "_id": 0,
                    "name": "$name",
                    "atk": "$max_atk",
                    "hp": "$max_hp",
                    "total_stat": {
                        "$add": [
                            {
                                "$divide": ["$max_atk", 10]
                            },
                            "$max_hp"
                        ]
                    }
                }
            },
            {
                "$sort": {
                    "total_stat": -1
                }
            }
        ])
        daemons = [d async for d in cur]
        paging = utils.Paginator(
            daemons, 5, separator="\n\n",
            title="GCQ STR rank",
            description=lambda i, x: f"{i+1}. **{x['name']}**\n   Max ATK: {x['atk']}\n   Max HP: {x['hp']}\n   GCQ STR: {x['total_stat']}",
            colour=discord.Colour.orange()
        )
        await paging.navigate(ctx)

    @commands.command(hidden=True)
    @checks.owner_only()
    async def lastindex(self, ctx):
        cur_index = 1
        all_values = await self.daemon_collection.distinct("id", {})
        while cur_index in all_values:
            cur_index += 1
        await ctx.send(cur_index-1)

    @commands.group(hidden=True, aliases=["leaks"])
    async def leak(self, ctx):
        if ctx.invoked_subcommand is None:
            if ctx.guild:
                return
            data = await self.belphegor_config.find_one_and_update(
                {"category": "leak"},
                {"$push": {"access_log": {"user_id": ctx.author.id, "timestamp": utils.now_time()}}},
                projection={"_id": False, "content": True, "policy": True, "last_update": True}
            )
            content = \
                f"{data['content']}\n" \
                "====================================================================================\n" \
                f"{data['policy']}\n" \
                "====================================================================================\n" \
                f"Last update: {data['last_update']}".splitlines()
            lines = []
            total_length = 0
            for l in content:
                if total_length + len(l) + 1 > 1900:
                    await ctx.send("\n".join(lines).strip())
                    lines = []
                    total_length = 0
                else:
                    lines.append(l)
                    total_length = total_length + len(l) + 1
            if lines:
                await ctx.send("\n".join(lines).strip())

    @leak.command(hidden=True, name="edit")
    @commands.check(lambda ctx: ctx.channel.id==303247718514556928)
    async def leak_edit(self, ctx, *, content):
        await self.belphegor_config.update_one({"category": "leak"}, {"$set": {"content": content, "last_update": utils.now_time().strftime("%Y-%m-%d")}})
        await ctx.confirm()

    @leak.command(hidden=True, name="append")
    @commands.check(lambda ctx: ctx.channel.id==303247718514556928)
    async def leak_append(self, ctx, *, content):
        cur = await self.belphegor_config.find_one({"category": "leak"}, projection={"_id": False, "content": True})
        await self.belphegor_config.update_one({"category": "leak"}, {"$set": {"content": f"{cur['content']}\n{content}", "last_update": utils.now_time().strftime("%Y-%m-%d")}})
        await ctx.confirm()

    @leak.command(hidden=True, name="policy")
    @commands.check(lambda ctx: ctx.channel.id==303247718514556928)
    async def leak_policy(self, ctx, *, content):
        await self.belphegor_config.update_one({"category": "leak"}, {"$set": {"policy": content, "last_update": utils.now_time().strftime("%Y-%m-%d")}})
        await ctx.confirm()

    @leak.command(hidden=True, name="test")
    @commands.check(lambda ctx: ctx.channel.id==303247718514556928)
    async def leak_test(self, ctx, *, content):
        data = await self.belphegor_config.find_one(
            {"category": "leak"},
            projection={"_id": False, "content": True, "policy": True, "last_update": True}
        )
        content = \
            f"{data['content']}\n" \
            "====================================================================================\n" \
            f"{data['policy']}\n" \
            "====================================================================================\n" \
            f"Last update: {data['last_update']}".splitlines()
        lines = []
        total_length = 0
        for l in content:
            if total_length + len(l) + 1 > 1900:
                await ctx.send("\n".join(lines).strip())
                lines = []
                total_length = 0
            else:
                lines.append(l)
                total_length = total_length + len(l) + 1
        if lines:
            await ctx.send("\n".join(lines).strip())

    @leak.command(hidden=True, name="log")
    @commands.check(lambda ctx: ctx.channel.id==303247718514556928)
    async def leak_log(self, ctx):
        data = await self.belphegor_config.find_one({"category": "leak"}, projection={"_id": False, "access_log": True})
        log_data = data["access_log"].reverse()
        embeds = []
        number_of_results = min(len(log_data), 100)
        paging = utils.Paginator(
            log_data[:number_of_results], 5, separator="\n\n",
            title=f"Leak access log (last {number_of_results} command uses)",
            description=lambda i, x: f"`{utils.format_time(x['timestamp'])}`\nUsername: {self.bot.get_user(x['user_id'])}\nUser ID: {x['user_id']}",
            footer=utils.format_time(utils.now_time())
        )
        await paging.navigate(ctx)

    @commands.command()
    async def stat(self, ctx, max_stat: int, rarity: int, level: int):
        '''
            `>>stat <max> <rarity> <level>`
            Calculate stat of daemon with given max stat and rarity, at certain level.
        '''
        if max_stat <= 0 or rarity <= 0 or rarity > 5 or level <= 0:
            return await ctx.send("What is this input.")
        else:
            result = mlb_stat(max=max_stat, rarity=rarity, level_inc=level-(40+10*rarity))
            await ctx.send(result)

    @commands.command()
    async def skill(self, ctx, max_skill, rarity: int, level: int):
        '''
            `>>skill <max> <rarity> <level>`
            Calculate skill damage/percentage of daemon with given max skill damage/percentage and rarity, at certain level.
            Percentage calculation is not accurate, just an estimation since the formula is not found yet.
        '''
        if rarity <= 0 or rarity > 5 or level <= 0:
            return await ctx.send("What is this input.")
        else:
            try:
                result = mlb_skill(skill=max_skill, rarity=rarity, level_inc=level-(40+10*rarity))
            except:
                await ctx.send("What is this input.")
            else:
                await ctx.send(result)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Otogi(bot))
