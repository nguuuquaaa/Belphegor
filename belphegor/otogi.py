import discord
from discord.ext import commands
import os
from urllib.parse import quote
from .utils import config, checks, request, format
import random
import json
import re
from bs4 import BeautifulSoup as BS
from fuzzywuzzy import process

#==================================================================================================================================================

class Daemon:
    def __init__(self, id, **kwargs):
        self.id = id
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def from_file(cls, filename):
        with open(f"{config.data_path}/daemon/daemon/{filename}", encoding="utf-8") as file:
            data = json.load(file)
            id = data.pop("id")
            return cls(id, **data)

    @classmethod
    def empty(cls, id):
        return cls(id, name=None, alias=None, pic_url=None, artwork_url=None, max_atk=0, max_hp=0, mlb_atk=None, mlb_hp=None,
                   rarity=0, daemon_type=None, daemon_class=None, skill=[], ability=[], bond=[], additional_data={}, faction=None)

    def embed_form(self, cog):
        data_embed = discord.Embed(colour=discord.Colour.orange())
        data_embed.add_field(name=f"{cog.emoji.get(self.daemon_type, '')} #{self.id} {self.name}",
                             value=f"{cog.emoji.get(self.daemon_class, '')} | {str(cog.emoji['star'])*self.rarity}\n"
                                   f"{cog.emoji['atk']}{self.atk}\n{cog.emoji['hp']}{self.hp}"
                                   "\n----------------------------------------------------------------------------------",
                             inline=False)
        check = len(self.skill) + len(self.ability) + len(self.bond) - 1
        for field in ("skill", "ability", "bond"):
            try:
                data = getattr(self, field)
                for stuff in data[:-1]:
                    data_embed.add_field(name=f"{cog.emoji[field]}{stuff[0]}", value=stuff[1], inline=False)
                    check -= 1
                if check > 0:
                    data_embed.add_field(name=f"{cog.emoji[field]}{data[-1][0]}", value=f"{data[-1][1]}\n----------------------------------------------------------------------------------", inline=False)
                else:
                    data_embed.add_field(name=f"{cog.emoji[field]}{data[-1][0]}", value=data[-1][1], inline=False)
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
        des = self.additional_data["description"].partition(".")
        data_embed = discord.Embed(title=self.name, url=f"http://otogi.wikia.com/wiki/{quote(base_name)}", description=f"***{des[0]}.***{des[2]}", colour=discord.Colour.orange())
        va = self.additional_data["voice_actor"]
        illu = self.additional_data["illustrator"]
        how = self.additional_data["how_to_acquire"]
        trv = self.additional_data["notes_and_trivia"]
        data_embed.add_field(name="Voice Actor", value=va if va else "--")
        data_embed.add_field(name="Illustrator", value=illu if illu else "--")
        data_embed.add_field(name="How to Acquire", value=how if how else "--", inline=False)
        data_embed.add_field(name="Notes & Trivia", value=trv if trv else "--", inline=False)
        quotes = self.additional_data["quote"]
        data_embed.add_field(name="Quotes", value=f"Main: [{quotes['main'][0]}]({quotes['main'][1]})\n"
                                                  f"Skill: [{quotes['skill'][0]}]({quotes['skill'][1]})\n"
                                                  f"Summon: [{quotes['summon'][0]}]({quotes['summon'][1]})\n"
                                                  f"Limit break: [{quotes['limit_break'][0]}]({quotes['limit_break'][1]})\n", inline=False)
        return pic_embed, data_embed

    def to_file(self):
        jsonable = self.__dict__
        with open(f"{config.data_path}/daemon/daemon/{self.id}.json", "w+", encoding="utf-8") as file:
            json.dump(jsonable, file, indent=4, ensure_ascii=False)

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
            return config.no_img

    @property
    def true_url(self):
        if self.pic_url:
            return self.pic_url
        else:
            return config.no_img

    @property
    def voice_actor(self):
        return self.additional_data["voice_actor"]

    @property
    def illustrator(self):
        return self.additional_data["illustrator"]

    @property
    def how_to_acquire(self):
        return self.additional_data["how_to_acquire"]

    @property
    def description(self):
        return self.additional_data["description"]

#==================================================================================================================================================

class MiniDaemon:
    def __init__(self, id, rarity, lb=0):
        self.id = id
        self.lb = lb
        self.rarity = rarity

    @property
    def cost(self):
        if self.rarity <= 2:
            return 0
        elif self.rarity == 3:
            return 1 * (self.lb + 1)
        elif self.rarity == 4:
            return 5 * (self.lb + 1)
        elif self.rarity == 5:
            return 25 * (self.lb + 1)

#==================================================================================================================================================

class Player:
    def __init__(self, id, mochi=0, daemons=[], exchange={}):
        self.mochi = mochi
        self.id = id
        self.daemons = daemons
        self.exchange = exchange

    @classmethod
    def from_file(cls, filename):
        with open(f"{config.data_path}/daemon/simulation/player/{filename}", encoding="utf-8") as file:
            data = json.load(file)
            daemons = []
            for d in data["daemons"]:
                daemons.append(MiniDaemon(d["id"], d["rarity"], d["lb"]))
            return cls(data["id"], data["mochi"], daemons, data["exchange"])

    def to_file(self):
        jsonable = {"id": self.id,
                    "mochi": self.mochi,
                    "daemons": [d.__dict__ for d in self.daemons],
                    "exchange": self.exchange}
        with open(f"{config.data_path}/daemon/simulation/player/{self.id}.json", "w+", encoding="utf-8") as file:
            json.dump(jsonable, file, indent=4, ensure_ascii=False)

    def sort_daemons(self):
        self.daemons.sort(key = lambda x: (x.id, -x.lb))

    def summon(self, id, rarity):
        self.daemons.append(MiniDaemon(id, rarity))
        self.to_file()

    def gimme(self, player, daemon):
        player.daemons.remove(daemon)
        self.daemons.append(daemon)
        self.to_file()
        player.to_file()

    def cmd_mochi(self, daemon):
        self.mochi += daemon.cost
        self.daemons.remove(daemon)
        self.to_file()

#==================================================================================================================================================

class OtogiBot():
    '''
    Otogi daemon info and summon simulation.
    '''

    def __init__(self, bot):
        self.bot = bot

        self.daemons = {}
        for filename in os.listdir(f"{config.data_path}/daemon/daemon"):
            if filename.endswith('.json'):
                data = Daemon.from_file(filename)
                self.daemons[data.id] = data

        with open(f"{config.data_path}/daemon/simulation/summon/jewel.json", encoding="utf-8") as file:
            raw_summon = json.load(file)
            self.summon = {3: raw_summon["3"], 4: raw_summon["4"], 5: raw_summon["5"]}

        self.players = {}
        for filename in os.listdir(f"{config.data_path}/daemon/simulation/player"):
            if filename.endswith(".json"):
                new_player = Player.from_file(filename)
                self.players[new_player.id] = new_player

        test_guild = self.bot.get_guild(config.test_guild_id)
        self.emoji = {}
        for emoji_name in ("atk", "hp", "skill", "ability", "bond", "star", "mochi", "phantasma", "anima", "divina", "ranged", "melee", "healer"):
            self.emoji[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild.emojis)

    def _search(self, name, *, no_prompt=False):
        result = []
        try:
            d_id = int(name)
            if no_prompt:
                return self.daemons[d_id]
            else:
                return [self.daemons[d_id],]
        except:
            pass
        regex = re.compile(".*?".join(name.split()), flags=re.I)
        for daemon in self.daemons.values():
            if regex.search(daemon.name):
                result.append(daemon)
            elif regex.search(daemon.alias):
                result.append(daemon)
        if no_prompt:
            for daemon in result:
                if name.lower() in (daemon.name.lower(), daemon.alias.lower()):
                    return daemon
            return result[0] if result else None
        else:
            return result

    async def filter(self, ctx, name, result, *, prompt_all=False):
        if not result:
            await ctx.send(f"Can't find {name} in database.")
            return None
        elif not prompt_all:
            if len(result) == 1:
                return result[0]
        await ctx.send("Do you mean:\n```\n{}\n<>: cancel\n```".format('\n'.join([f"{index+1}: {d.name}" for index, d in enumerate(result)])))
        msg = await self.bot.wait_for("message", check=lambda m:m.author.id==ctx.author.id)
        try:
            index = int(msg.content)-1
        except:
            return None
        if index in range(len(result)):
            return result[index]
        else:
            return None

    @commands.command(aliases=["daemon",])
    async def d(self, ctx, *, name:str):
        result = self._search(name)
        daemon = await self.filter(ctx, name, result)
        if not daemon:
            return
        pic_embed, data_embed = daemon.embed_form(self)
        await ctx.send(embed=pic_embed)
        await ctx.send(embed=data_embed)

    @commands.command(aliases=["pic",])
    async def p(self, ctx, *, name:str):
        daemon = self._search(name, no_prompt=True)
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

    def _search_att(self, attrs):
        result = []
        re_attrs = []
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
            except:
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
                else:
                    att = orig_att
                re_value = re.compile(".*?".join(value.split()), flags=re.I)
            re_attrs.append((att, re_value, orig_att))
        for daemon in self.daemons.values():
            check = True
            dattrs = ""
            for attr in re_attrs:
                value = attr[1]
                if isinstance(value, int):
                    target_value = getattr(daemon, attr[0], None)
                    if value != target_value:
                        check = False
                        break
                else:
                    target_value = getattr(daemon, attr[0], None)
                    if not value.search(target_value):
                        check = False
                        break
                    if len(target_value) > 100:
                        target_value = f"{target_value[:100]}..."
                dattrs = f"{dattrs}\n    {attr[2]}: {target_value}"
            if check:
                result.append((daemon, dattrs))
        return result

    @commands.command(aliases=["search",])
    async def ds(self, ctx, *, data):
        data = data.strip().splitlines()
        attrs = []
        for d in data:
            stuff = d.partition(" ")
            att = stuff[0].lower()
            attrs.append((att, stuff[2]))
        result = self._search_att(attrs)
        if not result:
            return await ctx.send("No result found.")
        result.sort(key=lambda x: x[0].id)
        result_pages = []
        for i, r in enumerate(result):
            if i%5 == 0:
                result_pages.append(f"#*{r[0].id}* **{r[0].name}**{r[1]}")
            else:
                result_pages[i//5] = f"{result_pages[i//5]}\n\n*#{r[0].id}* **{r[0].name}**{r[1]}"
        max_page = len(result_pages)
        current_page = 0
        embed = discord.Embed(title=f"Search result: {len(result)} results", colour=discord.Colour.orange())

        def data(page):
            embed.description = result_pages[page]
            embed.set_footer(text=f"(Page {page+1}/{max_page})")
            return embed

        await format.embed_page(ctx, max_page=max_page, embed=data)

    @commands.command(aliases=["trivia",])
    async def t(self, ctx, *, name:str):
        result = self._search(name)
        daemon = await self.filter(ctx, name, result)
        if not daemon:
            return
        pic_embed, data_embed = daemon.more_info(self)
        await ctx.send(embed=pic_embed)
        await ctx.send(embed=data_embed)

    @commands.group()
    async def update(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(title=":cd: Update database", colour=discord.Colour.orange())
            embed.add_field(name="Otogi SSA server only commands", value=
                            "`>>update create <data>` - Add an entry to database.")
            embed.add_field(name="Public commands", value=
                            "`>>update wikia <name>` - Update an entry with the information from wikia.\n")
            embed.add_field(name="Owner only commands", value=
                            "`>>update edit <data>` - Edit an entry's field.\n"
                            "`>>update delete <name>` - Delete an entry.\n"
                            "`>>update summon <name>` - Add a daemon to summon pool.\n"
                            "`>>update nosummon <name>` - Remove a daemon from summon pool.")
            await ctx.send(embed=embed)

    @update.command()
    @checks.otogi_guild_only()
    async def create(self, ctx, *, data:str):
        cur_index = 1
        while cur_index in self.daemons.keys():
            cur_index += 1
        data = data.strip().splitlines()
        try:
            new_daemon = Daemon.empty(cur_index)
            new_daemon.name = data[0]
            new_daemon.alias = data[1]
            try:
                new_daemon.max_atk = data[2]
                new_daemon.max_hp = data[3]
            except:
                pass
            for i, d in enumerate(data):
                if i > 3 and i%2 == 0:
                    if ">" in d:
                        new_daemon.bond.append((d, data[i+1]))
                    elif "(Lv" in d:
                        new_daemon.ability.append((d, data[i+1]))
                    else:
                        new_daemon.skill.append((d, data[i+1]))
            new_daemon.to_file()
            self.daemons[new_daemon.id] = new_daemon
            await ctx.send(f"Entry #{new_daemon.id} has been created.")
        except Exception as e:
            print(e)
            await ctx.send("Wrong format.")

    @update.command()
    @checks.owner_only()
    async def delete(self, ctx, *, name:str):
        result = self._search(name)
        daemon = await self.filter(ctx, name, result, prompt_all=True)
        if not daemon:
            return
        os.remove(f"{config.data_path}/daemon/daemon/{daemon.id}.json")
        name_remember = daemon.name
        self.daemons.pop(daemon.id, None)
        await ctx.send(f"The entry for {name_remember} has been deleted.")

    @update.command()
    @checks.owner_only()
    async def edit(self, ctx, *, data:str):
        data = data.strip().splitlines()
        result = self._search(data[0])
        daemon = await self.filter(ctx, data[0], result, prompt_all=True)
        if not daemon:
            return
        field = data[1]
        value = data[2]
        if field.lower() in ("id", "name", "alias","pic_url", "artwork_url", "max_atk", "max_hp",
                               "mlb_atk", "mlb_hp", "rarity", "daemon_type", "daemon_class", "faction"):
            if field in ("skill", "ability", "bond"):
                sab = []
                for ab, cd in enumerate(data):
                    if ab > 1 and ab%2 == 0:
                        sab.append((cd, data[ab+1]))
                setattr(daemon, field, sab)
            else:
                try:
                    value = int(value)
                except:
                    pass
                if field == "id":
                    if value in self.daemons.keys() and value != daemon.id:
                        return await ctx.send("This ID is already existed.")
                    else:
                        os.remove(f"{config.data_path}/daemon/daemon/{daemon.id}.json")
                        daemon = self.daemons.pop(daemon.id)
                if value:
                    setattr(daemon, field, value)
                else:
                    setattr(daemon, field, None)

            daemon.to_file()
            await ctx.send(f"The entry for {daemon.name} has been edited.")
        else:
            await ctx.send("Wrong format.")

    @update.command(name="summon")
    @checks.owner_only()
    async def _summon(self, ctx, *, name:str):
        result = self._search(name)
        daemon = await self.filter(ctx, name, result, prompt_all=True)
        if not daemon:
            return
        if daemon.rarity in (3, 4, 5):
            if daemon.id in self.summon[daemon.rarity]:
                return await ctx.send(f"The daemon {daemon.name} is already in summon pool.")
            else:
                self.summon[daemon.rarity].append(daemon.id)
        with open(f"{config.data_path}/daemon/simulation/summon/jewel.json", "w+", encoding="utf-8") as file:
            json.dump(self.summon, file, indent=4, ensure_ascii=False)
        await ctx.send(f"The daemon {daemon.name} has been added to summon pool.")

    @update.command()
    @checks.owner_only()
    async def nosummon(self, ctx, *, name:str):
        result = self._search(name)
        daemon = await self.filter(ctx, name, result, prompt_all=True)
        if not daemon:
            return
        for index, name in enumerate(self.summon[str(daemon.rarity)]):
            if name == daemon.name:
                self.summon[key].pop(index)
                with open(f"{config.data_path}/daemon/simulation/summon/jewel.json", "w+", encoding="utf-8") as file:
                    json.dump(self.summon, file, indent=4, ensure_ascii=False)
                return await ctx.send(f"The daemon {daemon.name} has been removed from summon pool.")
        await ctx.send(f"The daemon {daemon.name} is not in summon pool.")

    @update.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def wikia(self, ctx, *, name:str):
        result = self._search(name)
        daemon = await self.filter(ctx, name, result, prompt_all=True)
        if not daemon:
            return

        with ctx.typing():
            new_daemon = await self.search_wikia(daemon)
            try:
                if new_daemon:
                    self.daemons[new_daemon.id] = new_daemon
                    new_daemon.to_file()
                    await ctx.send(f"The entry for {new_daemon.name} has been updated with latest information from wikia.")
                else:
                    await ctx.send("No wikia page found.")
            except:
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
            bytes_ = await request.fetch(self.bot.session, f"http://otogi.wikia.com/api/v1/Search/List?query={quote(name)}&limit=5&batch=1&namespaces=0%2C14")
            search_query = json.loads(bytes_)
            check = False
            for item in search_query.get("items"):
                if "/" not in item["title"]:
                    base_name = item["title"]
                    check = True
                    break
            if not check:
                return None

        url = f"http://otogi.wikia.com/wiki/{quote(base_name)}"
        raw_data = await request.fetch(self.bot.session, url)

        delimiters = (' [', ']', ' ')
        regexPattern = '|'.join(map(re.escape, delimiters))
        name_pattern = '_'.join(re.split(regexPattern, name)).strip("_ ")
        pic_kind = {"pic_url": "", "artwork_url": "_Artwork"}
        for kind, trailing in pic_kind.items():
            try:
                wiki_pic_url = f"http://otogi.wikia.com/wiki/File:{quote(name_pattern)}{quote(trailing)}.png"
                pic_kind[kind] = await request.fetch(self.bot.session, wiki_pic_url)
            except:
                pic_kind[kind] = None

        new_daemon = await self.bot.loop.run_in_executor(None, self._bs_process, daemon, form, raw_data, pic_kind)
        return new_daemon

    def _bs_process(self, daemon, form, raw_data, pic_kind):
        bs_data = BS(raw_data.decode("utf-8"), "lxml")
        relevant_data = bs_data.find("div", attrs={"class": "tabbertab", "title": lambda x:x==form})
        tags = tuple(relevant_data.find_all("tr"))

        new_daemon = Daemon.empty(daemon.id)

        #name and alias
        new_daemon.name = format.unifix(tags[0].text)
        new_daemon.alias = format.unifix(daemon.alias)

        #type, class and rarity
        new_daemon.daemon_type = tags[0].find("img")["alt"].replace("icon", "").lower()
        rarity_and_class = tuple(tags[3].find_all("td"))
        new_daemon.rarity = -(-len(tuple(rarity_and_class[0].find_all("img"))) // 2)
        new_daemon.daemon_class = rarity_and_class[1].find("noscript").img["alt"].lower()

        #stats
        raw_atk = tuple(tags[4].find_all("td"))
        new_daemon.max_atk = int(raw_atk[1].text.strip().partition("/")[2])
        raw_hp = tuple(tags[5].find_all("td"))
        new_daemon.max_hp = int(raw_hp[1].text.strip().partition("/")[2])
        raw_mlb = tuple(tags[6].find_all("td"))
        try:
            stat_mlb = raw_mlb[1].text.strip().partition("/")
            new_daemon.mlb_atk = int(stat_mlb[0])
            new_daemon.mlb_hp = int(stat_mlb[2])
        except:
            pass

        #skill, ability and bond
        sub_pattern = re.compile(re.escape("(MAX/MLB)"), re.IGNORECASE)
        new_daemon.skill.append((format.unifix(tags[7].text), sub_pattern.sub("", format.unifix(tags[8].text))))
        for i in (10, 12):
            ability_value = format.unifix(str(tags[i].text))
            if len(ability_value) > 5:
                new_daemon.ability.append((format.unifix(tags[i-1].text), ability_value))
        for i in (14, 15):
            bond_data = tuple(tags[i].find_all("td"))
            bond_value = format.unifix(str(bond_data[1].text))
            if len(bond_value) > 5:
                new_daemon.bond.append((re.sub(' +', ' ', format.unifix(bond_data[0].text)), bond_value))

        #additional info
        add_keys = {16: "voice_actor", 18: "illustrator", 20: "description", 22: "how_to_acquire", 24: "notes_and_trivia"}
        for i in (16, 18, 20, 22, 24):
            new_daemon.additional_data[add_keys[i]] = format.unifix(tags[i+1].text)
        quote_keys = {27: "main", 28: "skill", 29: "summon", 30: "limit_break"}
        new_daemon.additional_data["quote"] = {}
        for i in (27, 28, 29, 30):
            quote_data = tuple(tags[i].find_all("td"))
            new_daemon.additional_data["quote"][quote_keys[i]] = (format.unifix(quote_data[1].text), quote_data[2].span.a["href"])

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
        else:
            new_daemon.faction = None

        new_daemon.to_file()
        return new_daemon

    @update.command()
    @checks.owner_only()
    async def data(self, ctx):
        self.__init__(self.bot)
        await ctx.send("Daemon database updated.")

    @commands.group(aliases=["ls"])
    @commands.cooldown(rate=1, per=1, type=commands.BucketType.user)
    async def lunchsummon(self, ctx):
        if ctx.invoked_subcommand is None:
            player = self.get_player(ctx.author.id)
            roll = random.randint(1,100)
            if 0 < roll <= 4:
                rarity = 5
            elif 4 < roll <= 22:
                rarity = 4
            else:
                rarity = 3
            daemon_id = random.choice(self.summon[rarity])
            player.summon(daemon_id, rarity)
            embed = discord.Embed(title=f"{ctx.author.display_name} summoned {self.daemons[daemon_id].name}!", colour=discord.Colour.orange())
            scale_url = self.daemons[daemon_id].true_url
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
        result = self._search(name)
        daemon = await self.filter(ctx, name, result)

        def whale_mode():
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
                did = random.choice(self.summon[rarity])
                if did == daemon.id:
                    break
            return result

        check = False
        for pool in self.summon.values():
            for daemon_id in pool:
                if daemon.id == daemon_id:
                    check = True
                    break
        if check:
            number_of_rolls = await self.bot.loop.run_in_executor(None, whale_mode)
            await ctx.send(f"It took {number_of_rolls} summons to get {daemon.name}.")
        else:
            await ctx.send(f"{daemon.name} is not in summon pool.")

    @lunchsummon.command(name="pool")
    async def summon_pool(self, ctx):
        summon_pools = {3: [], 4: [], 5: []}
        for rarity, pool in self.summon.items():
            for i, daemon_id in enumerate(pool):
                if i % 10 == 0:
                    summon_pools[rarity].append("")
                summon_pools[rarity][i//10] = f"{summon_pools[rarity][i//10]}{self.daemons[daemon_id].name}\n"
        max_pages = {3: len(summon_pools[3]), 4: len(summon_pools[4]), 5: len(summon_pools[5])}
        max_page = max([v for k, v in max_pages.items()])
        current_page = 0

        embed = discord.Embed(title="Current summon pool", colour=discord.Colour.blue())
        embed.add_field(name="3", value="3")
        embed.add_field(name="4", value="4")
        embed.add_field(name="5", value="5")
        embed.set_footer(text="Use reactions below to navigate pages.")

        def data(page):
            cur3 = min(page+1, max_pages[3])
            cur4 = min(page+1, max_pages[4])
            cur5 = min(page+1, max_pages[5])
            embed.set_field_at(0, name=str(self.emoji['star'])*3, value=f"{summon_pools[3][cur3-1]}\n(Page {cur3}/{max_pages[3]})" if summon_pools[3] else "None")
            embed.set_field_at(1, name=str(self.emoji['star'])*4, value=f"{summon_pools[4][cur4-1]}\n(Page {cur4}/{max_pages[4]})" if summon_pools[4] else "None")
            embed.set_field_at(2, name=str(self.emoji['star'])*5, value=f"{summon_pools[5][cur5-1]}\n(Page {cur5}/{max_pages[5]})" if summon_pools[5] else "None", inline=False)
            return embed

        await format.embed_page(ctx, max_page=max_page, embed=data)

    def get_player(self, id):
        player = self.players.get(id)
        if player is None:
            player = Player(id)
            self.players[player.id] = player
            player.to_file()
        return player

    @commands.command()
    async def mybox(self, ctx, *, member:discord.Member=None):
        try:
            target = member
            player = self.get_player(target.id)
        except:
            target = ctx.author
            player = self.get_player(target.id)
        player.sort_daemons()
        mybox_daemons = {3: [], 4: [], 5: []}
        rare = {3: 0, 4: 0, 5: 0}
        for daemon in player.daemons:
            r = daemon.rarity
            page = rare[r] // 10
            if rare[r] % 10 == 0:
                mybox_daemons[r].append("")
            mybox_daemons[r][page] = f"{mybox_daemons[r][page]}{self.daemons[daemon.id].name} lb{daemon.lb}\n"
            rare[r] += 1
        max_pages = {3: len(mybox_daemons[3]), 4: len(mybox_daemons[4]), 5: len(mybox_daemons[5])}
        max_page = max([v for k, v in max_pages.items()])

        embed = discord.Embed(title=f"Mochi: {player.mochi}{self.emoji['mochi']}", colour=discord.Colour.blue())
        embed.set_author(name=f"{target.display_name}'s box", icon_url=target.avatar_url)
        embed.add_field(name="3", value="3")
        embed.add_field(name="4", value="4")
        embed.add_field(name="5", value="5")
        embed.set_footer(text="Use reactions below to navigate pages.")

        def data(page):
            cur3 = min(page+1, max_pages[3])
            cur4 = min(page+1, max_pages[4])
            cur5 = min(page+1, max_pages[5])
            embed.set_field_at(0, name=str(self.emoji['star'])*3, value=f"{mybox_daemons[3][cur3-1]}\n(Page {cur3}/{max_pages[3]})" if mybox_daemons[3] else "None")
            embed.set_field_at(1, name=str(self.emoji['star'])*4, value=f"{mybox_daemons[4][cur4-1]}\n(Page {cur4}/{max_pages[4]})" if mybox_daemons[4] else "None")
            embed.set_field_at(2, name=str(self.emoji['star'])*5, value=f"{mybox_daemons[5][cur5-1]}\n(Page {cur5}/{max_pages[5]})" if mybox_daemons[5] else "None", inline=False)
            return embed

        await format.embed_page(ctx, max_page=max_page, embed=data)

    def _mini_search(self, player, name, lb):
        daemon = self._search(name, no_prompt=True)
        if daemon:
            for d in player.daemons:
                if d.id == daemon.id and d.lb == lb:
                    return d
        else:
            return None

    def _process_name(self, player, name):
        if name[-3:-1] == "lb":
            return self._mini_search(player, name[:-3], int(name[-1:]))
        elif name[:2] == "lb":
            return self._mini_search(player, name[4:], int(name[2]))
        else:
            return self._mini_search(player, name.strip(), 0)

    @commands.command()
    async def mochi(self, ctx, *, names):
        player = self.get_player(ctx.author.id)
        data = [n.strip() for n in names.split("&")]
        number_of_daemons = 0
        total_mochi = 0
        for name in data:
            mini_daemon = self._process_name(player, name)
            try:
                player.cmd_mochi(mini_daemon)
                number_of_daemons += 1
                total_mochi += mini_daemon.cost
            except AttributeError:
                pass
        await ctx.send(f"{ctx.author.display_name} sold {number_of_daemons} daemon(s) for {total_mochi}{self.emoji['mochi']}.\n{len(data)-number_of_daemons} failed.")

    @commands.command()
    async def mochibulk(self, ctx, *, names):
        player = self.get_player(ctx.author.id)
        data = [n.strip() for n in names.split("&")]
        number_of_daemons = 0
        failed = 0
        total_mochi = 0
        for name in data:
            try:
                mini_daemon = self._process_name(player, name)
                for d in player.daemons:
                    if d.id == mini_daemon.id:
                        player.cmd_mochi(mini_daemon)
                        number_of_daemons += 1
                        total_mochi += mini_daemon.cost
            except AttributeError:
                failed += 1
        await ctx.send(f"{ctx.author.display_name} sold {number_of_daemons} daemon(s) for {total_mochi}{self.emoji['mochi']}.\n{failed} failed.")

    @commands.command()
    async def mochiall(self, ctx, rarity:int):
        player = self.get_player(ctx.author.id)
        total = 0
        for mini_daemon in player.daemons[:]:
            if mini_daemon.rarity==rarity:
                total += mini_daemon.cost
                player.cmd_mochi(mini_daemon)
        await ctx.send(f"{ctx.author.display_name} sold all {rarity}* daemons for {total}{self.emoji['mochi']}.")

    @commands.command()
    async def gift(self, ctx, member:discord.Member, *, name):
        myself = self.get_player(ctx.author.id)
        player = self.get_player(member.id)
        mini_daemon = self._process_name(myself, name)
        if mini_daemon:
            player.gimme(myself, mini_daemon)
            await ctx.send(f"{ctx.author.display_name} gave {member.display_name} {self.daemons[mini_daemon.id].name} lb{mini_daemon.lb}.")

    @commands.command()
    async def gimme(self, ctx, member:discord.Member, price:int, *, name):
        myself = self.get_player(ctx.author.id)
        player = self.get_player(member.id)
        mini_daemon = self._process_name(player, name)
        if mini_daemon:
            if myself.mochi >= price:
                await ctx.send(f"Would {member.mention} trade {self.daemons[mini_daemon.id].name} lb{mini_daemon.lb} for {price}{self.emoji['mochi']}? Y/N")
                msg = await self.bot.wait_for("message", check=lambda m:m.author==member)
                if msg.content.lower() == "y":
                    myself.gimme(player, mini_daemon)
                    player.mochi += price
                    myself.mochi -= price
                    await ctx.send("Trade succeed.")
                else:
                    await ctx.send("Trade failed.")
            else:
                await ctx.send(f"{ctx.author.display_name}, you don't have that many {self.emoji['mochi']}.")
        else:
            await ctx.send(f"{member.display_name} doesn't have {name}.")

    def lb_that(self, player, mini_id):
        all_them = [d for d in player.daemons if d.id==mini_id]
        all_them.sort(key=lambda x: -x.lb)
        first = 0
        last = len(all_them) - 1
        while first < last:
            if all_them[first].lb + all_them[last].lb <= 3:
                all_them[first].lb += all_them[last].lb + 1
                player.daemons.remove(all_them[last])
                all_them.pop(last)
                last -= 1
            else:
                first += 1

    @commands.command()
    async def limitbreak(self, ctx, *, name=None):
        player = self.get_player(ctx.author.id)
        if name:
            try:
                mini_daemon = self._process_name(player, name)
                self.lb_that(player, mini_daemon.id)
            except:
                return await ctx.send(f"You don't have {name} in your box.")
        else:
            all_ids = []
            for d in player.daemons:
                if d.id not in all_ids:
                    all_ids.append(d.id)
            for mid in all_ids:
                self.lb_that(player, mid)
        player.to_file()
        await ctx.send("Limit breaking succeed.")

    @commands.group()
    async def exchange(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @exchange.command(name="get")
    async def exchange_get(self, ctx, *, name):
        pass

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(OtogiBot(bot))
