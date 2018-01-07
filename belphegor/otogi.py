import discord
from discord.ext import commands
from urllib.parse import quote
from . import utils
from .utils import config, checks, token, data_type
import random
import re
import traceback
from bs4 import BeautifulSoup as BS
from apiclient.discovery import build
import asyncio
from pymongo import ReturnDocument, UpdateOne
import json

#==================================================================================================================================================

class Daemon(data_type.BaseObject):
    @classmethod
    def empty(cls, id):
        return cls({
            "id": id, "name": None, "alias": None, "pic_url": None, "artwork_url": None, "max_atk": 0, "max_hp": 0,
            "mlb_atk": None, "mlb_hp": None, "rarity": 0, "daemon_type": None, "daemon_class": None, "skills": [], "abilities": [], "bonds": [],
            "faction": None, "voice_actor": None, "illustrator": None, "description": None, "how_to_acquire": None, "notes_and_trivia": None,
            "quotes": {"main": {}, "skill": {}, "summon": {}, "limit_break": {}}
        })

    def embed_form(self, cog):
        emojis = cog.emojis
        data_embed = discord.Embed(colour=discord.Colour.orange())
        data_embed.add_field(
            name=f"{emojis.get(self.daemon_type, '')} #{self.id} {self.name}",
            value=
                f"{emojis.get(self.daemon_class, '')} | {str(emojis['star'])*self.rarity}\n"
                f"{emojis['atk']}{self.atk}\n{emojis['hp']}{self.hp}"
                "\n----------------------------------------------------------------------------------",
            inline=False
        )
        check = len(self.skills) + len(self.abilities) + len(self.bonds) - 1
        field_list = ("skills", "abilities", "bonds")
        for index, key in enumerate(("skill", "ability", "bond")):
            field = field_list[index]
            try:
                data = getattr(self, field)
                for stuff in data[:-1]:
                    data_embed.add_field(name=f"{emojis[key]}{stuff['name']}", value=stuff['effect'], inline=False)
                    check -= 1
                if check > 0:
                    data_embed.add_field(name=f"{emojis[key]}{data[-1]['name']}", value=f"{data[-1]['effect']}\n----------------------------------------------------------------------------------", inline=False)
                else:
                    data_embed.add_field(name=f"{emojis[key]}{data[-1]['name']}", value=data[-1]['effect'], inline=False)
                check -= 1
            except:
                pass
        pic_embed = discord.Embed(colour=discord.Colour.orange())
        pic_embed.set_image(url=self.true_url)
        return pic_embed, data_embed

    def more_info(self, cog):
        pic_embed = discord.Embed(colour=discord.Colour.orange())
        pic_embed.set_image(url=self.true_artwork)
        try:
            bracket_index = self.name.index("[")
            base_name = self.name[:bracket_index-1]
        except:
            base_name = self.name
        description = self.description or "--"
        des = description.partition(".")
        data_embed = discord.Embed(title=self.name, url=f"http://otogi.wikia.com/wiki/{quote(base_name)}", description=f"***{des[0]}.***{des[2]}", colour=discord.Colour.orange())
        data_embed.add_field(name="Voice Actor", value=self.voice_actor or "--")
        data_embed.add_field(name="Illustrator", value=self.illustrator or "--")
        data_embed.add_field(name="How to Acquire", value=self.how_to_acquire or "--", inline=False)
        data_embed.add_field(name="Notes & Trivia", value=self.notes_and_trivia or "--", inline=False)
        quotes = self.quotes
        data_embed.add_field(
            name="Quotes",
            value=
                f"Main: [{quotes['main'].get('value')}]({quotes['main'].get('url')})\n"
                f"Skill: [{quotes['skill'].get('value')}]({quotes['skill'].get('url')})\n"
                f"Summon: [{quotes['summon'].get('value')}]({quotes['summon'].get('url')})\n"
                f"Limit break: [{quotes['limit_break'].get('value')}]({quotes['limit_break'].get('url')})\n",
            inline=False
        )
        return pic_embed, data_embed

    @property
    def atk(self):
        if self.mlb_atk:
            return f"{self.max_atk}/{self.mlb_atk}"
        else:
            return self.max_atk

    @property
    def hp(self):
        if self.mlb_hp:
            return f"{self.max_hp}/{self.mlb_hp}"
        else:
            return self.max_hp

    @property
    def true_artwork(self):
        if self.artwork_url:
            return self.artwork_url
        else:
            return config.NO_IMG

    @property
    def true_url(self):
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
        for emoji_name in ("atk", "hp", "skill", "ability", "bond", "star", "mochi", "phantasma", "anima", "divina", "ranged", "melee", "healer"):
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, creampie_guild.emojis)

        self.lock = asyncio.Lock()

    async def _search(self, ctx, name, *, prompt=None):
        return await ctx.search(
            name, self.daemon_collection,
            cls=Daemon, colour=discord.Colour.orange(), atts=["id", "name", "alias"], name_att="name", emoji_att="daemon_class", prompt=prompt, sort={"id": 1}
        )

    @commands.command(name="daemon", aliases=["d"])
    async def cmd_daemon(self, ctx, *, name: str):
        daemon = await self._search(ctx, name)
        if not daemon:
            return
        pic_embed, data_embed = daemon.embed_form(self)
        await ctx.send(embed=pic_embed)
        await ctx.send(embed=data_embed)

    @commands.command(name="pic", aliases=["p"])
    async def cmd_pic(self, ctx, *, name: str):
        daemon = await self._search(ctx, name, prompt=False)
        if daemon:
            pic_embed = discord.Embed(colour=discord.Colour.orange())
            pic_embed.set_image(url=daemon.true_url)
            await ctx.send(embed=pic_embed)
            if daemon.artwork_url:
                artwork_embed = discord.Embed(colour=discord.Colour.orange())
                artwork_embed.set_image(url=daemon.artwork_url)
                await ctx.send(embed=artwork_embed)
        else:
            await ctx.send(f"Can't find {name} in database.")

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

    @commands.command(name="daemonsearch", aliases=["ds"])
    async def cmd_ds(self, ctx, *, data):
        data = data.strip().splitlines()
        attrs = []
        for d in data:
            stuff = d.partition(" ")
            attrs.append((stuff[0].lower(), stuff[2].lower()))
        result = await self._search_att(attrs)
        if not result:
            return await ctx.send("No result found.")
        embeds = utils.page_format(
            result, 5, separator="\n\n",
            title=f"Search result: {len(result)} results",
            description=lambda i, x: f"`#{x['id']}` **{x['name']}**{x['value']}",
            colour=discord.Colour.orange()
        )
        await ctx.embed_page(embeds)

    @commands.command(name="trivia", aliases=["t"])
    async def cmd_t(self, ctx, *, name:str):
        daemon = await self._search(ctx, name)
        if not daemon:
            return
        pic_embed, data_embed = daemon.more_info(self)
        await ctx.send(embed=pic_embed)
        await ctx.send(embed=data_embed)

    @commands.group()
    async def update(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(title="\U0001f4bf Update database", colour=discord.Colour.orange())
            embed.add_field(
                name="Otogi SSA server only command",
                value="`>>update create <data>` - Add an entry to database."
            )
            embed.add_field(
                name="Public command",
                value="`>>update wikia <name>` - Update an entry with the information from wikia.\n"
            )
            await ctx.send(embed=embed)

    @update.command()
    @checks.otogi_guild_only()
    async def create(self, ctx, *, data:str):
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

    @update.command()
    @checks.owner_only()
    async def delete(self, ctx, *, name):
        daemon = await self._search(ctx, name, prompt=True)
        if not daemon:
            return
        await self.daemon_collection.find_one_and_delete({"id": daemon.id})
        await ctx.send(f"The entry for {daemon.name} has been deleted.")

    @update.command()
    @checks.owner_only()
    async def edit(self, ctx, *, data):
        data = data.strip().splitlines()
        daemon = await self._search(ctx, data[0], prompt=True)
        if not daemon:
            return
        field = data[1]
        value = data[2]
        if field.lower() in (
            "name", "alias","pic_url", "artwork_url", "max_atk", "max_hp", "mlb_atk", "mlb_hp", "rarity",
            "daemon_type", "daemon_class", "skill", "ability1", "ability2", "bond1", "bond2", "faction"
        ):
            try:
                if field.lower() in ("skill", "ability1", "ability2", "bond1", "bond2"):
                    value = {"name": data[2], "effect": data[3]}
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

    @update.command(name="summon")
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

    @update.command()
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

    @update.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def wikia(self, ctx, *, name):
        daemon = await self._search(ctx, name, prompt=True)
        if not daemon:
            return
        async with ctx.typing():
            try:
                new_daemon = await self.search_wikia(daemon)
                if new_daemon:
                    await self.daemon_collection.replace_one({"id": daemon.id}, new_daemon.__dict__)
                    await ctx.send(f"The entry for {new_daemon.name} has been updated with latest information from wikia.")
                else:
                    await ctx.send("No wikia page found.")
            except:
                print(traceback.format_exc())
                await ctx.send("Something went wrong.")

    async def search_wikia(self, daemon):
        name = daemon.name
        alias = daemon.alias
        try:
            bracket_index = name.index("[")
            base_name = name[:bracket_index-1]
            form = f"{name[bracket_index+1:-1]} Form"
        except:
            base_name = name
            form = "Original Form"

        #wikia search
        if base_name == "Commander Yashichi":
            base_name = "Yashichi"
            form = "Commander Form"
        elif base_name in ("Tsukuyomi", "Tsukiyomi"):
            base_name = "Tsukuyomi"
            form = "Original Form"
        else:
            bytes_ = await utils.fetch(self.bot.session, f"http://otogi.wikia.com/api/v1/Search/List?query={quote(name)}&limit=5&batch=1&namespaces=0%2C14")
            search_query = json.loads(bytes_)
            for item in search_query.get("items"):
                if "/" not in item["title"]:
                    base_name = item["title"]
                    break
            else:
                return None

        url = f"http://otogi.wikia.com/wiki/{quote(base_name)}"
        raw_data = await utils.fetch(self.bot.session, url)

        delimiters = (' [', ']', ' ')
        regexPattern = '|'.join(map(re.escape, delimiters))
        name_pattern = '_'.join(re.split(regexPattern, name)).strip("_ ")
        pic_kind = {"pic_url": "", "artwork_url": "_Artwork"}
        for kind, trailing in pic_kind.items():
            try:
                wiki_pic_url = f"http://otogi.wikia.com/wiki/File:{quote(name_pattern)}{quote(trailing)}.png"
                pic_kind[kind] = await utils.fetch(self.bot.session, wiki_pic_url)
            except:
                pic_kind[kind] = None

        new_daemon = await self.bot.loop.run_in_executor(None, self._bs_process, daemon, form, raw_data, pic_kind)
        return new_daemon

    def _bs_process(self, daemon, form, raw_data, pic_kind):
        bs_data = BS(raw_data.decode("utf-8"), "lxml")
        relevant_data = bs_data.find("div", attrs={"class": "tabbertab", "title": lambda x:x==form})
        tags = relevant_data.find_all("tr")

        new_daemon = Daemon.empty(daemon.id)

        #name and alias
        new_daemon.name = utils.unifix(tags[0].text)
        new_daemon.alias = utils.unifix(daemon.alias)

        #type, class and rarity
        rarity_and_class = tags[3].find_all("td")
        new_daemon.rarity = len(rarity_and_class[0].find_all("img", recursive=False))
        new_daemon.daemon_type = tags[0].find("img")["alt"].replace("icon", "").lower()
        new_daemon.daemon_class = rarity_and_class[1].find("img")["alt"].lower()

        #stats
        raw_atk = tags[4].find_all("td")
        new_daemon.max_atk = int(raw_atk[1].text.strip().partition("/")[2])
        raw_hp = tags[5].find_all("td")
        new_daemon.max_hp = int(raw_hp[1].text.strip().partition("/")[2])
        raw_mlb = tags[6].find_all("td")
        try:
            stat_mlb = raw_mlb[1].text.strip().partition("/")
            new_daemon.mlb_atk = int(stat_mlb[0])
            new_daemon.mlb_hp = int(stat_mlb[2])
        except:
            pass

        #skills, abilities and bonds
        sub_pattern = re.compile(re.escape("(MAX/MLB)"), re.IGNORECASE)
        new_daemon.skills.append({"name": utils.unifix(tags[7].text), "effect": sub_pattern.sub("", utils.unifix(tags[8].text))})
        for i in (10, 12):
            ability_value = utils.unifix(str(tags[i].text))
            if len(ability_value) > 5:
                new_daemon.abilities.append({"name": utils.unifix(tags[i-1].text), "effect": ability_value})
        for i in (14, 15, 16):
            bond_data = tags[i].find_all("td")
            bond_value = utils.unifix(str(bond_data[1].text))
            if len(bond_value) > 5:
                new_daemon.bonds.append({"name": re.sub(' +', ' ', utils.unifix(bond_data[0].text)), "effect": bond_value})

        #additional info
        add_keys = {17: "voice_actor", 19: "illustrator", 21: "description", 23: "how_to_acquire", 25: "notes_and_trivia"}
        for i, add_type in add_keys.items():
            setattr(new_daemon, add_type, utils.unifix(tags[i+1].text))
        quote_keys = {28: "main", 29: "skill", 30: "summon", 31: "limit_break"}
        for i, quote_type in quote_keys.items():
            quote_data = tags[i].find_all("td")
            new_daemon.quotes[quote_type] = {
                "value": utils.unifix(quote_data[1].text),
                "url": quote_data[2].span.a["href"]
            }

        #pic links
        for kind, raw_pic_data in pic_kind.items():
            try:
                bs_pic_data = BS(raw_pic_data.decode("utf-8"), "lxml")
                pic_url = bs_pic_data.find("a", attrs={"class": "internal"})
                setattr(new_daemon, kind, pic_url["href"])
            except:
                pass

        #faction
        if daemon.faction:
            new_daemon.faction = daemon.faction

        return new_daemon

    @update.command(name="everything", aliases=["all"])
    @checks.owner_only()
    async def update_everything(self, ctx, start_from: int=0):
        async for daemon_data in self.daemon_collection.find({"id": {"$gte": start_from}}):
            try:
                daemon = Daemon(daemon_data)
                new_daemon = await self.search_wikia(daemon)
                await self.daemon_collection.replace_one({"id": daemon.id}, new_daemon.__dict__)
            except:
                return print(traceback.format_exc())
            else:
                print(f"Done #{new_daemon.id} {new_daemon.name}")

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
        if ctx.invoked_subcommand is None:
            id = ctx.author.id
            player = await self.get_player(id)
            roll = random.randint(1,100)
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
            scale_url = daemon.true_url
            data = scale_url.split("?cb=")
            try:
                code = data[2].partition("&")
                scale_url = f"{data[0]}/scale-to-width-down/250?cb={code[0]}"
            except:
                pass
            embed.set_image(url=scale_url)
            await ctx.send(embed=embed)

    @lunchsummon.command()
    async def till(self, ctx, *, name):
        daemon = await self._search(ctx, name)
        if not daemon:
            return
        pool_data = await self.summon_pool.find_one({"rarity": daemon.rarity})
        pool = pool_data["pool"]
        for daemon_id in pool:
            if daemon.id == daemon_id:
                break
        else:
            return await ctx.send(f"{daemon.name} is not in summon pool.")
        result = 0
        while True:
            result += 1
            roll = random.randint(1,100)
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
        summon_pool = {p["rarity"]: p["pool"] async for p in self.summon_pool.find({})}
        embeds = []
        for rarity, pool in summon_pool.items():
            max_page = (len(pool)-1)//10+1
            embed_pool = []
            daemons = [d async for d in self.daemon_collection.find({"id": {"$in": pool}}, projection={"_id": False, "id": True, "name": True})]
            daemons.sort(key=lambda x: x["id"])
            for index in range(0, len(daemons), 10):
                desc = "\n".join((daemon['name'] for daemon in daemons[index:index+10]))
                embed = discord.Embed(
                    title="Current summon pool:",
                    description=f"{str(self.emojis['star'])*rarity}\n{desc}\n\n(Page {index//10+1}/{max_page} - Book {rarity-2}/3)",
                    colour=discord.Colour.orange()
                )
                embed_pool.append(embed)
            embeds.append(embed_pool)
        await ctx.embed_page(embeds)

    @commands.command()
    async def mybox(self, ctx, *, member: discord.Member=None):
        target = member or ctx.author
        player = await self.get_player(target.id)
        lbs = {d["id"]: d["lb"] for d in player["daemons"]}
        embeds = []
        async for pool in self.daemon_collection.aggregate([
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
        ]):
            daemons = pool["daemons"]
            max_page = (len(daemons)-1)//10+1
            embed_pool = []
            for index in range(0, len(daemons), 10):
                desc = "\n".join((f"{daemon['name']} lb{lbs[daemon['id']]}" for daemon in daemons[index:index+10]))
                embed = discord.Embed(
                    title=f"Mochi: {player['mochi']}{self.emojis['mochi']}",
                    description=f"{str(self.emojis['star'])*pool['_id']}\n{desc}\n\n(Page {index//10+1}/{max_page}",
                    colour=discord.Colour.orange()
                )
                embed.set_author(name=f"{target.display_name}'s box", icon_url=target.avatar_url)
                embed_pool.append(embed)
            embeds.append(embed_pool)
        if embeds:
            max_vertical = len(embeds)
            for i, embed_pool in enumerate(embeds):
                for embed in embed_pool:
                    embed.description = f"{embed.description} - Book {i+1}/{max_vertical})"
            await ctx.embed_page(embeds)
        else:
            embed = discord.Embed(f"Mochi: {player['mochi']}{self.emojis['mochi']}", description="Empty", colour=discord.Colour.orange())
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
        player = await self.get_player(ctx.author.id)
        names = [n.strip() for n in names.split(";")]
        number_of_daemons = 0
        total_mochi = 0
        for raw_name in names:
            name, lb = self._process_name(raw_name)
            daemon = await self._search(ctx, name, prompt=False)
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
        player = await self.get_player(ctx.author.id)
        names = [n.strip() for n in names.split(";")]
        total_mochi = 0
        for raw_name in names:
            name, lb = self._process_name(raw_name)
            daemon = await self._search(ctx, name, prompt=False)
            i = 0
            while i < len(player["daemons"]):
                d = player["daemons"][i]
                if d["id"] == daemon.id:
                    target = player["daemons"].pop(i)
                    total_mochi += self.mochi_cost(daemon) * (target["lb"] + 1)
                else:
                    i += 1
        await self.player_list.update_one({"id": ctx.author.id}, {"$inc": {"mochi": total_mochi}, "$set": {"daemons": player["daemons"]}})
        await ctx.send(f"{ctx.author.display_name} sold {number_of_daemons} daemon(s) for {total_mochi}{self.emojis['mochi']}.")

    @mochi.command()
    async def all(self, ctx, rarity: int):
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
        name, lb = self._process_name(name)
        daemon = await self._search(ctx, name, prompt=False)
        if not daemon:
            return await ctx.send(f"Can't find {name} in database.")
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
        data = data.rsplit("for", 1)
        price = int(data[1].replace("mochi", "").replace("mc", "").strip(" s"))
        name = data[0].strip()
        name, lb = self._process_name(name)
        daemon = await self._search(ctx, name, prompt=False)
        if not daemon:
            return await ctx.send(f"Can't find {name} in database.")
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
        player = await self.get_player(ctx.author.id)
        if name:
            name, lb = self._process_name(player, name)
            daemon = await self._search(ctx, name, prompt=False)
            self.lb_that(player, daemon.id)
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

    @update.command(name="sheet")
    @checks.owner_only()
    async def update_sheet(self, ctx):
        result = await self.bot.loop.run_in_executor(None, self.get_sheet, "1oJnQ5TYL5d9LJ04HMmsuXBvJSAxqhYqcggDZKOctK2k", "Sheet1!$A$1:$YY")
        await self.stat_sheet.find_one_and_replace({}, result)
        await ctx.message.add_reaction("\u2705")

    @commands.command(aliases=["nuker"])
    async def nukers(self, ctx):
        data = await self.stat_sheet.find_one({})
        sheet = data["values"]
        filter_sheet = [s for s in sheet if s[64]=="Damage"]
        filter_sheet.sort(key=lambda x: -int(x[59].replace(",", "")))
        embeds = []
        max_page = (len(filter_sheet) - 1) // 5 + 1
        for index in range(0, len(filter_sheet), 5):
            desc = "\n\n".join((
                f"{index+i+1}. **{field[1]}**\n   MLB Effective Skill DMG: {field[59]}\n   MLB Auto ATK DMG: {field[57]}"
                for i, field in enumerate(filter_sheet[index:index+5])
            ))
            embed = discord.Embed(
                title="Nuker rank",
                description = f"{desc}\n\n(Page {index//5+1}/{max_page})",
                colour=discord.Colour.orange()
            )
            embeds.append(embed)
        await ctx.embed_page(embeds)

    @commands.command(aliases=["auto"])
    async def autoattack(self, ctx):
        data = await self.stat_sheet.find_one({})
        sheet = data["values"][1:]
        filter_sheet = [s for s in sheet if s[19]!="Healer"]
        filter_sheet.sort(key=lambda x: -int(x[57].replace(",", "")))
        embeds = []
        max_page = (len(filter_sheet) - 1) // 5 + 1
        for index in range(0, len(filter_sheet), 5):
            desc = "\n\n".join((
                f"{index+i+1}. **{field[1]}**\n   Class: {field[19]}\n   MLB Auto ATK DMG: {field[57]}"
                for i, field in enumerate(filter_sheet[index:index+5])
            ))
            embed = discord.Embed(
                title="Auto attack rank",
                description = f"{desc}\n\n(Page {index//5+1}/{max_page})",
                colour=discord.Colour.orange()
            )
            embeds.append(embed)
        await ctx.embed_page(embeds)

    def list_get(self, iterable, index, default=None):
        try:
            return iterable[index]
        except:
            return default

    def int_get(self, any_obj):
        try:
            return int(any_obj)
        except:
            return 0

    @commands.command(aliases=["debuffer"])
    async def debuffers(self, ctx):
        data = await self.stat_sheet.find_one({})
        sheet = data["values"]
        filter_sheet = [s for s in sheet if self.list_get(s, 74)=="Increases DMG Rec'd" or s[64]=="Debuff"]
        filter_sheet.sort(key=lambda x: x[0])
        embeds = []
        max_page = (len(filter_sheet) - 1) // 5 + 1
        for index in range(0, len(filter_sheet), 5):
            desc = "\n\n".join((
                f"{index+i+1}. **{field[1]}**\n   MLB Debuff Value: {self.list_get(field, 76) or 'N/A'}\n"
                f"   MLB Effective Skill DMG: {field[59]}\n   Skill Effect: {self.list_get(field, 74) or 'N/A'}"
                for i, field in enumerate(filter_sheet[index:index+5])
            ))
            embed = discord.Embed(
                title="Debuffer list",
                description = f"{desc}\n\n(Page {index//5+1}/{max_page})",
                colour=discord.Colour.orange()
            )
            embeds.append(embed)
        await ctx.embed_page(embeds)

    @commands.command(aliases=["buffer"])
    async def buffers(self, ctx):
        data = await self.stat_sheet.find_one({})
        sheet = data["values"]
        filter_sheet = [s for s in sheet if s[64]=="Buff"]
        filter_sheet.sort(key=lambda x: x[0])
        embeds = []
        max_page = (len(filter_sheet) - 1) // 5 + 1
        for index in range(0, len(filter_sheet), 5):
            desc = "\n\n".join((
                f"{index+i+1}. **{field[1]}**\n   MLB Buff Value: {self.list_get(field, 76) or 'N/A'}\n   Skill Effect: {self.list_get(field, 74) or 'N/A'}"
                for i, field in enumerate(filter_sheet[index:index+5])
            ))
            embed = discord.Embed(
                title="Buffer list",
                description = f"{desc}\n\n(Page {index//5+1}/{max_page})",
                colour=discord.Colour.orange()
            )
            embeds.append(embed)
        await ctx.embed_page(embeds)

    @commands.command()
    async def gcqstr(self, ctx):
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
        embeds = []
        max_page = (len(daemons) - 1) // 5 + 1
        for index in range(0, len(daemons), 5):
            desc = "\n\n".join((
                f"{index+i+1}. **{daemon['name']}**\n   Max ATK: {daemon['atk']}\n   Max HP: {daemon['hp']}\n   GCQ STR: {daemon['total_stat']}"
                for i, daemon in enumerate(daemons[index:index+5])
            ))
            embed = discord.Embed(
                title="GCQ STR rank",
                description = f"{desc}\n\n(Page {index//5+1}/{max_page})",
                colour=discord.Colour.orange()
            )
            embeds.append(embed)
        await ctx.embed_page(embeds)

    @commands.command()
    @checks.owner_only()
    async def datadump(self, ctx):
        async for daemon in self.daemon_collection.find({}):
            daemon.pop("_id")
            with open(f"data/otogi/daemon/{daemon['id']}.json", "w", encoding="utf-8") as file:
                json.dump(daemon, file, indent=4, ensure_ascii=False)
        sum = {sp["rarity"]: sp["pool"] async for sp in self.summon_pool.find({})}
        with open(f"data/otogi/jewel_summon.json", "w", encoding="utf-8") as file:
            json.dump(sum, file, indent=4, ensure_ascii=False)
        await ctx.confirm()

    @commands.group()
    async def exchange(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @exchange.command(name="get")
    async def exchange_get(self, ctx, *, name):
        pass

    @commands.group(aliases=["leaks"])
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

    @leak.command(name="edit")
    @commands.check(lambda ctx: ctx.channel.id==303247718514556928)
    async def leak_edit(self, ctx, *, content):
        await self.belphegor_config.update_one({"category": "leak"}, {"$set": {"content": content, "last_update": utils.now_time().strftime("%Y-%m-%d")}})
        await ctx.confirm()

    @leak.command(name="append")
    @commands.check(lambda ctx: ctx.channel.id==303247718514556928)
    async def leak_append(self, ctx, *, content):
        cur = await self.belphegor_config.find_one({"category": "leak"}, projection={"_id": False, "content": True})
        await self.belphegor_config.update_one({"category": "leak"}, {"$set": {"content": f"{cur['content']}\n{content}", "last_update": utils.now_time().strftime("%Y-%m-%d")}})
        await ctx.confirm()

    @leak.command(name="policy")
    @commands.check(lambda ctx: ctx.channel.id==303247718514556928)
    async def leak_policy(self, ctx, *, content):
        await self.belphegor_config.update_one({"category": "leak"}, {"$set": {"policy": content, "last_update": utils.now_time().strftime("%Y-%m-%d")}})
        await ctx.confirm()

    @leak.command(name="test")
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

    @leak.command(name="log")
    @commands.check(lambda ctx: ctx.channel.id==303247718514556928)
    async def leak_log(self, ctx):
        data = await self.belphegor_config.find_one({"category": "leak"}, projection={"_id": False, "access_log": True})
        log_data = data["access_log"][::-1]
        embeds = []
        number_of_results = min(len(log_data), 100)
        max_page = (number_of_results - 1) // 5 + 1
        for index in range(0, number_of_results, 5):
            desc = "\n\n".join((
                f"`{utils.format_time(l['timestamp'])}`\nUsername: {self.bot.get_user(l['user_id'])}\nUser ID: {l['user_id']}"
                for i, l in enumerate(log_data[index:index+5])
            ))
            embed = discord.Embed(
                title=f"Leak access log (last {number_of_results} command uses)",
                description=f"{desc}\n\n(Page {index//5+1}/{max_page})"
            )
            embed.set_footer(text=utils.format_time(utils.now_time()))
            embeds.append(embed)
        await ctx.embed_page(embeds)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Otogi(bot))
