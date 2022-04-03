import discord
from discord.ext import commands
from . import utils
from .utils import data_type, checks, config, modding, token, wiki
import json
import traceback
from urllib.parse import quote
import re

#==================================================================================================================================================

ISWIKI_BASE = "https://ironsaga.fandom.com"
ISWIKI_API = f"{ISWIKI_BASE}/api.php"

COPILOT_SLOTS = {
    "attack": "Attack",
    "tech": "Tech",
    "defense": "Defense",
    "support": "Support",
    "control": "Control",
    "special": "Special"
}

#==================================================================================================================================================

parser = wiki.WikitextParser()

@parser.set_box_handler("PilotInfo")
@parser.set_box_handler("PilotInfo1")
def handle_base_box(box, **kwargs):
    return {"pilot_info": kwargs}

@parser.set_html_handler
def handle_html(tag, text, **kwargs):
    if tag == "tabber":
        return {"tabber": text}
    elif tag == "gallery":
        return {"skin_gallery": text.strip().splitlines()}
    else:
        return text

@parser.set_reference_handler
def handle_reference(box, *args, **kwargs):
    if box.startswith("File:"):
        return {"file": box[5:]}
    else:
        return box

#==================================================================================================================================================

class Pilot(data_type.BaseObject):
    @property
    def name(self):
        return self.en_name or self.jp_name or self.page_name

    def _base_info(self, ctx):
        embed = discord.Embed(
            title=self.name,
            color=discord.Color.red(),
            url=f"{ISWIKI_BASE}/wiki/{quote(self.page_name)}"
        )
        stats = self.stats
        embed.add_field(
            name="Stats",
            value=f"Melee: {stats['melee']}\n"
                f"Ranged: {stats['ranged']}\n"
                f"Defense: {stats['defense']}\n"
                f"Reaction: {stats['reaction']}"
        )
        embed.add_field(name="Personality", value=self.personality)
        embed.add_field(name="Copilot slots", value=" | ".join(k for k, v in self.copilot_slots.items() if v), inline=False)
        for sk, dot in zip(self.skills, ["\u25CF", "\u00B7", "\u00B7", "\u00B7"]):
            copilot = sk["copilot"]
            if copilot:
                copilot = f" [{copilot}]"
            else:
                copilot = ""
            embed.add_field(
                name=f"{dot} {sk['name']}{copilot}",
                value=sk["effect"],
                inline=False
            )
        return embed

    def _other_info(self, ctx):
        embed = discord.Embed(
            title=self.name,
            description=self.description,
            color=discord.Color.red(),
            url=f"{ISWIKI_BASE}/wiki/{quote(self.page_name)}"
        )
        embed.add_field(name="Faction", value=self.faction, inline=False)
        embed.add_field(name="Artist", value=self.artist or "N/A")
        embed.add_field(name="Voice actor", value=self.voice_actor or "N/A")
        return embed

    async def display_info(self, ctx):
        emojis = ctx.cog.emojis
        paging = utils.Paginator([])
        base_info = self._base_info(ctx)
        other_info = self._other_info(ctx)
        skins = self.skins
        skin_iter = data_type.circle_iter(skins, with_index=True)

        saved = {
            "embed": base_info,
            "skin": next(skin_iter)
        }

        def add_image():
            embed = saved["embed"]
            i, skin = saved["skin"]
            embed.set_image(url=skin["url"])
            embed.set_footer(text=f"Skin: {skin['name']} ({i+1}/{len(skins)})")

        @paging.wrap_action(emojis["exp_capsule"])
        def display_base_info():
            saved["embed"] = base_info
            add_image()
            return saved["embed"]

        @paging.wrap_action("\U0001f5d2")
        def display_other_info():
            saved["embed"] = other_info
            add_image()
            return saved["embed"]

        @paging.wrap_action("\U0001f5bc")
        def change_image():
            saved["skin"] = next(skin_iter)
            add_image()
            return saved["embed"]

        await paging.navigate(ctx)

#==================================================================================================================================================

color_mapping = {
    "S": discord.Color.purple(),
    "A": discord.Color.blue(),
    "B": discord.Color.green(),
    "C": discord.Color.light_grey()
}

class Part(data_type.BaseObject):
    def embed_form(self, ctx):
        embed = discord.Embed(
            title=f"[{self.classification.capitalize()}] {self.name}",
            description=self.effect,
            color=color_mapping[self.rank]
        )
        embed.set_thumbnail(url=self.thumbnail)
        return embed

#==================================================================================================================================================

class Pet(data_type.BaseObject):
    def embed_form(self, ctx):
        embed = discord.Embed(
            title=self.name,
            description=self.effect,
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=self.thumbnail)
        return embed

#==================================================================================================================================================

class Mech(data_type.BaseObject):
    pass

#==================================================================================================================================================

class IronSaga(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pilot_index = bot.db.pilot_index
        self.part_index = bot.db.part_index
        self.pet_index = bot.db.pet_index
        self.mech_index = bot.db.mech_index
        self.emojis = {
            "SSS": "[SSS] ", "SS": "[SS] ", "S": "[S] ", "A": "[A] ", "B": "[B] ", "C": "[C] "
        }

        test_guild_3 = bot.get_guild(config.TEST_GUILD_3_ID)
        for emoji_name in (
            "exp_capsule", "blinking",
            "normal", "fire", "ice", "em",  "beam", "explosive", "acid",
            "main_arm", "secondary_arm", "missile", "melee", "mega_weapon"
        ):
            self.emojis[emoji_name] = discord.utils.find(lambda e: e.name==emoji_name, test_guild_3.emojis)

    @commands.group(invoke_without_command=True)
    async def pilot(self, ctx, *, name):
        '''
            `>>pilot <name>`
            Display a pilot info.
            Name is case-insensitive.
        '''
        p = await ctx.search(
            name,
            self.pilot_index,
            cls=Pilot,
            atts=["en_name", "jp_name", "page_name"],
            aliases_att="aliases",
            name_att="name",
            sort={"en_name": 1, "jp_name": 1, "page_name": 1}
        )
        if p:
            await p.display_info(ctx)

    @pilot.command(name="skill", aliases=["s"])
    async def pilot_skill(self, ctx, *, name):
        '''
            `>>pilot skill <name>`
            Filter pilots with given name or effect.
        '''
        escaped_name = r".*?".join(map(re.escape, name.split()))
        pilots = []
        async for doc in self.pilot_index.find(
            {
                "skills": {
                    "$elemMatch": {
                        "$or": [
                            {
                                "name": {
                                    "$regex": escaped_name,
                                    "$options": "i"
                                }
                            },
                            {
                                "effect": {
                                    "$regex": escaped_name,
                                    "$options": "i"
                                }
                            }
                        ]
                    }
                }
            },
            projection={
                "_id": 0,
                "en_name": 1,
                "skills.$": 1
            }
        ):
            pilots.append({"name": doc["en_name"], "skill": doc["skills"][0]})

        if pilots:
            paging = utils.Paginator(
                pilots, 10,
                title=f"Result: {len(pilots)} matches",
                colour=discord.Colour.red(),
                fields=lambda i, x: (
                    x["name"],
                    f"**{x['skill']['name']} {'[' + x['skill']['copilot'] + ']' if x['skill']['copilot'] else ''}**\n{x['skill']['effect']}",
                    False
                )
            )
            await paging.navigate(ctx)
        else:
            return await ctx.send("Found nothing.")

    @pilot.group(name="update")
    @checks.owner_only()
    async def pilot_update(self, ctx):
        pass

    @pilot_update.command(aliases=["all"])
    async def everything(self, ctx):
        await ctx.trigger_typing()
        params = {
            "action":       "parse",
            "prop":         "wikitext",
            "page":         "Pilot_List",
            "format":       "json",
            "redirects":    1
        }
        bytes_ = await self.bot.fetch(ISWIKI_API, params=params)
        raw = json.loads(bytes_)
        parser = wiki.WikitextParser()
        data = parser.parse(raw["parse"]["wikitext"]["*"])
        names = []
        for row in data[0]:
            if len(row) > 1:
                names.append(row[1].rpartition("<br>")[2].strip("[]"))

        await self.update_pilots_with_names(ctx, names)

    @pilot_update.command()
    async def many(self, ctx, *names):
        await ctx.trigger_typing()
        logs = await self.update_pilots_with_names(ctx, names)
        if logs:
            await ctx.send_json(logs, filename="log.json")

    async def update_pilots_with_names(self, ctx, names):
        logs = {}
        async def do_query():
            passed = []
            failed = []
            count = len(names)
            for i, name in enumerate(names):
                try:
                    pilot = await self.search_iswiki_for_pilot(name)
                except:
                    logs[name] = traceback.format_exc()
                    failed.append(name)
                else:
                    passed.append(pilot.en_name)
                    updated = pilot.__dict__.copy()
                    index = updated.pop("index")
                    await self.pilot_index.update_one(
                        {"index": index},
                        {"$set": updated, "$setOnInsert": {"aliases": []}},
                        upsert=True
                    )
                    yield (i + 1) / count

            txt = json.dumps({"passed": passed, "failed": failed}, indent=4, ensure_ascii=False)
            await ctx.send(
                f"Passed: {len(passed)}\nFailed: {len(failed)}",
                file=discord.File.from_str(txt, "result.json")
            )

        await ctx.progress_bar(
            do_query(),
            {
                "initial": f"Total: {len(names)} pilots\nFetching...\n",
                "done": f"Total: {len(names)} pilots\nDone.\n"
            }
        )
        return logs

    async def search_iswiki_for_pilot(self, name):
        bytes_ = await self.bot.fetch(
            ISWIKI_API,
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

        page_id = raw["parse"]["pageid"]
        raw_basic_info = raw["parse"]["wikitext"]["*"]
        ret = parser.parse(raw_basic_info)
        skins = []
        for item in ret:
            if isinstance(item, dict):
                if "pilot_info" in item:
                    basic_info = item["pilot_info"]
                    elem = basic_info["image"][0]
                    try:
                        tabber = elem["tabber"]
                    except KeyError:
                        filename = elem["file"]
                        skins.append({"name": "Default", "url": f"{ISWIKI_BASE}/{wiki.generate_image_path(filename)}"})
                    else:
                        for tab in tabber:
                            if isinstance(tab, str) and tab.endswith("="):
                                name = tab.rstrip("=").lstrip("|-")
                            elif isinstance(tab, dict):
                                filename = tab["file"]
                                skins.append({"name": name, "url": f"{ISWIKI_BASE}/{wiki.generate_image_path(filename)}"})
                    

                elif "skin_gallery" in item:
                    for s in item["skin_gallery"]:
                        filename, _, name = s.partition("|")
                        skins.append({"name": name, "url": f"{ISWIKI_BASE}/{wiki.generate_image_path(filename)}"})

        pilot = Pilot({})
        pilot.index = page_id
        pilot.en_name = basic_info["name (english/romaji)"]
        pilot.jp_name = basic_info["name (original)"]
        pilot.page_name = raw["parse"]["title"]
        pilot.description = basic_info.get("background")
        pilot.personality = basic_info["personality"]
        pilot.faction = basic_info["affiliation"]
        pilot.artist = basic_info.get("artist")
        pilot.voice_actor = basic_info.get("seiyuu")
        pilot.stats = {
            "melee": basic_info["meleemax"],
            "ranged": basic_info["shootingmax"],
            "defense": basic_info["defensemax"],
            "reaction": basic_info["reactionmax"]
        }
        pilot.skills = [
            {
                "name": basic_info["activeskillname"],
                "effect": basic_info["activeskilleffect"],
                "copilot": COPILOT_SLOTS.get(basic_info.get("activeskilltype", "").lower())
            },
            {
                "name": basic_info["passiveskill1name"],
                "effect": basic_info["passiveskill1effect"],
                "copilot": COPILOT_SLOTS.get(basic_info.get("passiveskill1type", "").lower())
            },
            {
                "name": basic_info["passiveskill2name"],
                "effect": basic_info["passiveskill2effect"],
                "copilot": COPILOT_SLOTS.get(basic_info.get("passiveskill2type", "").lower())
            },
            {
                "name": basic_info["passiveskill3name"],
                "effect": basic_info["passiveskill3effect"],
                "copilot": COPILOT_SLOTS.get(basic_info.get("passiveskill3type", "").lower())
            }
        ]
        pilot.copilot_slots = {
            "Attack": bool(basic_info.get("copilotattack")),
            "Tech": bool(basic_info.get("copilottech")),
            "Defense": bool(basic_info.get("copilotdefense")),
            "Support": bool(basic_info.get("copilotsupport")),
            "Control": bool(basic_info.get("copilotcontrol")),
            "Special": bool(basic_info.get("copilotspecial"))
        }
        pilot.skins = skins

        return pilot

    @pilot_update.command(name="alias")
    @checks.owner_only()
    async def update_alias(self, ctx, *, data=modding.KeyValue()):
        try:
            name = data.getone("")
            alias = data.getone("alias")
        except KeyError:
            return await ctx.send("Need name and alias.")

        p = await ctx.search(
            name,
            self.pilot_index,
            cls=Pilot,
            atts=["en_name", "jp_name", "page_name"],
            aliases_att="aliases",
            name_att="name",
            sort={"en_name": 1, "jp_name": 1, "page_name": 1},
            prompt=True
        )
        if p:
            await self.pilot_index.update_one({"index": p.index}, {"$addToSet": {"aliases": alias}})
            await ctx.send(f"Added {alias} to {p.en_name}'s list of aliases.")

    @commands.group(invoke_without_command=True)
    async def part(self, ctx, *, name):
        '''
            `>>part <name>`
            Display a part info.
            Name is case-insensitive.
        '''
        p = await ctx.search(
            name,
            self.part_index,
            cls=Part,
            colour=discord.Colour.red(),
            atts=["name", "classification"],
            aliases_att="aliases",
            emoji_att="rank",
            name_att="name",
            sort={"rank": ["S", "A", "B", "C"], "name": 1}
        )
        if p:
            await ctx.send(embed=p.embed_form(ctx))

    @part.command(name="update")
    async def part_update(self, ctx):
        try:
            attachment = ctx.message.attachments[0]
        except IndexError:
            return await ctx.send("Need json file.")

        col = self.part_index
        await col.delete_many({})
        bytes_ = await attachment.read()
        data = json.loads(bytes_)
        for index, doc in enumerate(data):
            await col.insert_one({"id": index+1, **doc})
        await ctx.send("Done.")

    @commands.group(invoke_without_command=True)
    async def pet(self, ctx, *, name):
        '''
            `>>pet <name>`
            Display a pet info.
            Name is case-insensitive.
        '''
        p = await ctx.search(
            name,
            self.pet_index,
            cls=Pet,
            colour=discord.Colour.red(),
            atts=["name"],
            aliases_att="aliases",
            name_att="name",
            sort={"name": 1}
        )
        if p:
            await ctx.send(embed=p.embed_form(ctx))

    @pet.command(name="update")
    async def pet_update(self, ctx):
        try:
            attachment = ctx.message.attachments[0]
        except IndexError:
            return await ctx.send("Need json file.")

        col = self.pet_index
        await col.delete_many({})
        bytes_ = await attachment.read()
        data = json.loads(bytes_)
        for index, doc in enumerate(data):
            await col.insert_one({"id": index+1, **doc})
        await ctx.send("Done.")

    @commands.group(invoke_without_command=True, aliases=["mecha"])
    @checks.owner_only()
    async def mech(self, ctx, *, name):
        p = await ctx.search(
            name,
            self.mech_index,
            cls=Mech,
            colour=discord.Colour.red(),
            atts=["en_name"],
            emoji_att="rarity",
            name_att="en_name",
            sort={"rarity": ["SSS", "SS", "S", "A", "B", "C"], "en_name": 1}
        )
        if p:
            await ctx.send(embed=p.embed_form(ctx))

    @mech.group(name="update")
    @checks.owner_only()
    async def mech_update(self, ctx):
        pass

    @mech_update.command(name="basic")
    @checks.owner_only()
    async def mech_update_basic(self, ctx, *, data: modding.KeyValue()):
        try:
            en_name = data.getone("en_name")
        except KeyError:
            return await ctx.send("Invalid mech name")

        classification = data.geteither("classification", "class")
        if classification in ("mecha", "mech"):
            classification = "mecha"
            abilities = []
            # for raw_ab in data.getall("action")

        mech = {
            "en_name": en_name,
            "jp_name": data.get("jp_name") or None,
            "rarity": data.getone("rarity"),
            "faction": data.get("faction", "Unknown"),
            "description": data.geteither("description", "desc"),
            "image_url": data.geteither("image", "image_url"),
            "hp": data.get("hp", "?")
        }

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(IronSaga(bot))