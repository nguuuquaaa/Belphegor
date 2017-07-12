import discord
from discord.ext import commands
import os
import codecs
from urllib.parse import quote
import urllib.request as rq
from .utils import config, checks, request
import random
import json
import re
from bs4 import BeautifulSoup as BS

#======================================================================================================

class Daemon:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def from_file(cls, filename):
        try:
            with codecs.open(config.data_path+"daemon/daemon/"+filename+".json", encoding="utf-8") as file:
                data = json.load(file)
                try:
                    alias = data["alias"]
                except:
                    alias = filename
                return cls(name=data["name"], alias=alias, pic_url=data["pic_url"], atk=data["atk"],
                           hp=data["hp"], skill=data["skill"], ability=data["ability"], bond=data["bond"])
        except:
            return None

    def embed_form(self, cog):
        data_embed = discord.Embed(colour=discord.Colour.orange())
        data_embed.add_field(name=self.name, value="{}{}\n{}{}\n----------------------------------------------------------------------------------".format(cog.emoji["atk"], self.atk, cog.emoji["hp"], self.hp), inline=False)
        check = len(self.skill) + len(self.ability) + len(self.bond) - 1
        for field in ("skill", "ability", "bond"):
            try:
                data = getattr(self, field)
                for stuff in data[:-1]:
                    data_embed.add_field(name="{}{}".format(cog.emoji[field], stuff["name"]), value=stuff["value"], inline=False)
                    check -= 1
                if check > 0:
                    data_embed.add_field(name="{}{}".format(cog.emoji[field], data[-1]["name"]), value=data[-1]["value"]+"\n----------------------------------------------------------------------------------", inline=False)
                else:
                    data_embed.add_field(name="{}{}".format(cog.emoji[field], data[-1]["name"]), value=data[-1]["value"], inline=False)
                check -= 1
            except:
                pass
        pic_embed = discord.Embed(colour=discord.Colour.orange())
        pic_embed.set_image(url=self.true_url)
        return pic_embed, data_embed

    def to_file(self):
        jsonable = self.__dict__
        with codecs.open(config.data_path+"daemon/daemon/"+self.alias+".json", "w+", encoding="utf-8") as file:
            json.dump(jsonable, file, ensure_ascii=False)

    @property
    def true_url(self):
        if self.pic_url:
            return self.pic_url
        else:
            return config.no_img

#======================================================================================================

class MiniDaemon:
    def __init__(self, name, rarity, lb=0):
        self.name = name
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

#======================================================================================================

class Player:
    def __init__(self, member_id, mochi=0, daemons=[], exchange=[]):
        self.mochi = mochi
        self.member_id = member_id
        self.daemons = daemons
        self.exchange = exchange

    @classmethod
    def from_file(cls, member_id):
        try:
            with codecs.open(config.data_path + "daemon/simulation/player/" + str(member_id) + ".json", encoding="utf-8") as file:
                data = json.load(file)
                daemons = []
                for d in data["daemons"]:
                    daemons.append(MiniDaemon(d["name"], d["rarity"], d["lb"]))
                try:
                    return cls(data["member_id"], data["mochi"], daemons, data["exchange"])
                except:
                    return cls(data["member_id"], data["mochi"], daemons)
        except Exception as e:
            print(e)
            new_player = cls(member_id)
            new_player.to_file()
            return new_player

    def to_file(self):
        jsonable = {"member_id": self.member_id,
                    "mochi": self.mochi,
                    "daemons": [d.__dict__ for d in self.daemons],
                    "exchange": self.exchange}
        with codecs.open(config.data_path + "daemon/simulation/player/" + str(self.member_id) + ".json", "w+", encoding="utf-8") as file:
            json.dump(jsonable, file, ensure_ascii=False)

    def sort_daemons(self):
        self.daemons.sort(key = lambda x: (x.name, -x.lb))

    def summon(self, name, rarity):
        self.daemons.append(MiniDaemon(name, rarity))
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

#======================================================================================================

class OtogiBot():
    def __init__(self, bot):
        self.bot = bot

        self.daemons = {}
        for filename in os.listdir(config.data_path+"daemon/daemon"):
            if filename.endswith('.json'):
                data = Daemon.from_file(filename[:-5])
                self.daemons[data.name] = data

        with codecs.open(config.data_path + "daemon/group/tags.json", encoding="utf-8") as file:
            self.tags = json.load(file)
        with codecs.open(config.data_path + "daemon/group/groups.json", encoding="utf-8") as file:
            self.groups = json.load(file)

        with codecs.open(config.data_path + "daemon/simulation/summon/jewel.json", encoding="utf-8") as file:
            self.summon = json.load(file)

        test_server = self.bot.get_guild(config.test_server_id)
        self.emoji = {}
        for emoji_name in ("atk", "hp", "skill", "ability", "bond", "star", "mochi"):
            self.emoji[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_server.emojis)

    def _search(self, name):
        result = []
        for daemon_alias, daemon in self.daemons.items():
            check = True
            for word in name.lower().split():
                if word not in daemon.name.lower():
                    check = False
                    break
            if check:
                result.append(daemon)
            elif daemon.name != daemon.alias:
                check = True
                for word in name.split():
                    if word.lower() not in daemon.alias.lower():
                        check = False
                        break
                if check:
                    result.append(daemon)
        return result

    @commands.command(aliases=["daemon",])
    async def d(self, ctx, *, name:str):
        result = self._search(name)
        if not result:
            await ctx.send("Can't find {} in database.".format(name))
            return
        elif len(result) > 1:
            await ctx.send("Do you mean:\n```\n{}\n<>: cancel\n```".format('\n'.join([str(index+1)+": "+d.name for index, d in enumerate(result)])))
            msg = await self.bot.wait_for("message", check=lambda m:m.author==ctx.message.author)
            try:
                index = int(msg.content)-1
                if index in range(len(result)):
                    daemon = result[index]
                else:
                    return
            except:
                return
        else:
            daemon = result[0]
        pic_embed, data_embed = daemon.embed_form(self)
        await ctx.send(embed=pic_embed)
        await ctx.send(embed=data_embed)

    def _search_group(self, name):
        result = []
        for tag, group in self.tags.items():
            check = True
            for word in name.lower().split():
                if word not in tag:
                    check = False
                    break
            if check:
                result.append(group)
        return result

    @commands.command(aliases=["group"])
    async def g(self, ctx, *, name:str):
        result = self._search_group(name)
        if not result:
            await ctx.send("Can't find {} in database.".format(name))
            return
        elif len(result) > 1:
            await ctx.send("Do you mean:\n```\n{}\n<>: cancel\n```".format('\n'.join([str(index+1)+": "+d for index, d in enumerate(result)])))
            msg = await self.bot.wait_for("message", check=lambda m:m.author==ctx.message.author)
            try:
                index = int(msg.content)-1
                if index in range(len(result)):
                    group = result[index]
                else:
                    return
            except:
                return
        else:
            group = result[0]
        embed = discord.Embed(colour=discord.Colour.orange())
        embed.add_field(name="Current members of "+group, value="\n".join([str(i+1)+". "+g for i, g in enumerate(self.groups[group])]))
        await ctx.send(embed=embed)

    def _find_player(self, member_id):
        return Player.from_file(member_id)

    @commands.command(aliases=["ls"])
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def lunchsummon(self, ctx):
        player = self._find_player(ctx.message.author.id)
        roll = random.randint(1,100)
        if 0 < roll <= 4:
            rarity = "5"
        elif 4 < roll <= 22:
            rarity = "4"
        else:
            rarity = "3"
        daemon = random.choice(self.summon[rarity])
        player.summon(daemon, int(rarity))
        embed = discord.Embed(title=ctx.message.author.display_name+" summoned " + daemon + "!", colour=discord.Colour.orange())
        data = self.daemons[daemon].true_url.split("?cb=")
        try:
            code = data[1].split("&")
            scale_url = data[0] + "/scale-to-width-down/250?cb=" + code[0]
        except:
            scale_url = self.daemons[daemon].true_url
        embed.set_image(url=scale_url)
        await ctx.send(embed=embed)

    @commands.group()
    async def update(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(title=":cd: Update database", colour=discord.Colour.orange())
            embed.add_field(name="Otogi SSA server only commands", value=
                            "`>>update create <data>` - Add a card to database.\n"
                            "`>>update edit <data>` - Edit a card's field.\n"
                            "`>>update delete <name>` - Delete a card.\n"
                            "`>>update group <data>` - Add a daemon to a group.\n"
                            "`>>update tag <data>` - Add a tag to search for group.\n"
                            "`>>update summon <rarity> <name>` - Add a daemon to summon pool.\n"
                            "`>>update nosummon <name>` - Remove a daemon from summon pool.\n\n"
                            "Note: Please don't use commands when you are not sure of <data> format.")
            embed.add_field(name="Public commands", value=
                            "`>>update wikia <name>` - Update a daemon with the information from wikia.\n")
            await ctx.send(embed=embed)

    @update.command()
    @checks.otogi_server_only()
    async def create(self, ctx, *, data:str):
        data = [d for d in data.splitlines() if d]
        new_daemon = {}
        try:
            new_daemon["name"] = data[0]
            new_daemon["alias"] = data[1]
            new_daemon["pic_url"] = None
            try:
                new_daemon["atk"] = data[2]
                new_daemon["hp"] = data[3]
            except:
                new_daemon["atk"] = 0
                new_daemon["hp"] = 0
            new_daemon["skill"] = []
            new_daemon["ability"] = []
            new_daemon["bond"] = []
            for i, d in enumerate(data):
                if i > 3 and i%2 == 0:
                    if ">" in d:
                        new_daemon["bond"].append({"name": d, "value": data[i+1]})
                    elif "(Lv" in d:
                        new_daemon["ability"].append({"name": d, "value": data[i+1]})
                    else:
                        new_daemon["skill"].append({"name": d, "value": data[i+1]})
            with codecs.open(config.data_path+"daemon/daemon/"+data[1]+".json", "w+", encoding="utf-8") as file:
                json.dump(new_daemon, file, ensure_ascii=False)
            self.daemons[new_daemon["name"]] = Daemon.from_file(data[1])
            await ctx.send("Added.")
        except:
            await ctx.send("Wrong format.")

    @update.command()
    @checks.otogi_server_only()
    async def delete(self, ctx, *, name:str):
        result = self._search(name)
        if not result:
            await ctx.send("Can't find {} in database.".format(name))
            return
        else:
            await ctx.send("Do you mean:\n```\n{}\n<>: cancel\n```".format('\n'.join([str(index+1)+": "+d.name for index, d in enumerate(result)])))
            msg = await self.bot.wait_for("message", check=lambda m:m.author==ctx.message.author)
            try:
                index = int(msg.content)-1
                if index in range(len(result)):
                    daemon = result[index]
                else:
                    return
            except:
                return
        os.remove(config.data_path+"daemon/daemon/"+daemon.alias+".json")
        del self.daemons[daemon.name]
        await ctx.send("Deleted.")

    @update.command()
    @checks.otogi_server_only()
    async def edit(self, ctx, *, data:str):
        data = [d for d in data.splitlines() if d]
        name = data[0]
        result = self._search(name)
        if not result:
            await ctx.send("Can't find {} in database.".format(name))
            return
        else:
            await ctx.send("Do you mean:\n```\n{}\n<>: cancel\n```".format('\n'.join([str(index+1)+": "+d.name for index, d in enumerate(result)])))
            msg = await self.bot.wait_for("message", check=lambda m:m.author==ctx.message.author)
            try:
                index = int(msg.content)-1
                if index in range(len(result)):
                    daemon = result[index]
                else:
                    return
            except:
                return
        with codecs.open(config.data_path+"daemon/daemon/"+daemon.alias+".json", encoding="utf-8") as file:
            d = json.load(file)
        if data[1] in daemon.__dict__:
            if data[1] in ("skill", "ability", "bond"):
                sab = []
                for ab, cd in enumerate(data):
                    if ab > 1 and ab%2 == 0:
                        sab.append({"name": cd, "value": data[ab+1]})
                setattr(daemon, data[1], sab)
            else:
                setattr(daemon, data[1], data[2])
            os.remove(config.data_path+"daemon/daemon/"+daemon.alias+".json")
            daemon.to_file()
            await ctx.send("Edited.")
        else:
            await ctx.send("Wrong format.")

    @update.command(name="summon")
    @checks.otogi_server_only()
    async def _summon(self, ctx, rarity:int, *, name:str):
        result = self._search(name)
        if not result:
            await ctx.send("Can't find {} in database.".format(name))
            return
        else:
            await ctx.send("Do you mean:\n```\n{}\n<>: cancel\n```".format('\n'.join([str(index+1)+": "+d.name for index, d in enumerate(result)])))
            msg = await self.bot.wait_for("message", check=lambda m:m.author==ctx.message.author)
            try:
                index = int(msg.content)-1
                if index in range(len(result)):
                    daemon = result[index]
                else:
                    return
            except:
                return
        with codecs.open(config.data_path + "daemon/simulation/summon/jewel.json", encoding="utf-8") as file:
            summon = json.load(file)
        if rarity in (3, 4, 5):
            summon[str(rarity)].append(daemon.name)
        with codecs.open(config.data_path + "daemon/simulation/summon/jewel.json", "w+", encoding="utf-8") as file:
            json.dump(summon, file, ensure_ascii=False)
        self.summon = summon
        await ctx.send("Summon added.")

    @update.command()
    @checks.otogi_server_only()
    async def nosummon(self, ctx, *, name:str):
        result = self._search(name)
        if not result:
            await ctx.send("Can't find {} in database.".format(name))
            return
        else:
            await ctx.send("Do you mean:\n```\n{}\n<>: cancel\n```".format('\n'.join([str(index+1)+": "+d.name for index, d in enumerate(result)])))
            msg = await self.bot.wait_for("message", check=lambda m:m.author==ctx.message.author)
            try:
                index = int(msg.content)-1
                if index in range(len(result)):
                    daemon = result[index]
                else:
                    return
            except:
                return
        summon = dict(self.summon)
        for key, value in summon.items():
            for index, name in enumerate(value):
                if name == daemon.name:
                    self.summon[key].pop(index)
                    break
        with codecs.open(config.data_path + "daemon/simulation/summon/jewel.json", "w+", encoding="utf-8") as file:
            json.dump(summon, file, ensure_ascii=False)
        await ctx.send("Summon removed.")

    @update.command(name="group")
    @checks.otogi_server_only()
    async def group_update(self, ctx, *, data:str):
        data = [d for d in data.splitlines() if d]
        try:
            group = self._search_group(data[1])[-1]
        except IndexError:
            await ctx.send("No group found. Create a new group {}? Y/N".format(data[1]))
            msg = await self.bot.wait_for("message", check=lambda m:m.author==ctx.message.author)
            if msg.content.lower() == "y":
                group = data[1]
            else:
                return
        result = self._search(data[0])
        if not result:
            await ctx.send("Can't find {} in database.".format(name))
            return
        else:
            await ctx.send("Do you mean:\n```\n{}\n<>: cancel\n```".format('\n'.join([str(i+1)+": "+d.name for i, d in enumerate(result)])))
            msg = await self.bot.wait_for("message", check=lambda m:m.author==ctx.message.author)
            try:
                index = int(msg.content)-1
                if index in range(len(result)):
                    daemon = result[index]
                else:
                    return
            except:
                return
        try:
            self.groups[group].append(daemon.name)
        except:
            self.groups[group] = [daemon.name,]
            self.tags[group] = group
        with codecs.open(config.data_path + "daemon/group/groups.json", "w+", encoding="utf-8") as file:
            json.dump(self.groups, file, ensure_ascii=False)
        with codecs.open(config.data_path + "daemon/group/tags.json", "w+", encoding="utf-8") as file:
            json.dump(self.tags, file, ensure_ascii=False)
        await ctx.send("Group updated.")

    @update.command(name="tag")
    @checks.otogi_server_only()
    async def group_tag(self, ctx, *, data:str):
        data = [d for d in data.splitlines() if d]
        try:
            group = self._search_group(data[1])[-1]
        except IndexError:
            await ctx.send("No group found. Create a new group {}? Y/N".format(data[1]))
            msg = await self.bot.wait_for("message", check=lambda m:m.author==ctx.message.author)
            if msg.content.lower() == "y":
                group = data[1]
                self.groups[group] = []
            else:
                return
        self.tags[data[0]] = group
        with codecs.open(config.data_path + "daemon/group/groups.json", "w+", encoding="utf-8") as file:
            json.dump(self.groups, file, ensure_ascii=False)
        with codecs.open(config.data_path + "daemon/group/tags.json", "w+", encoding="utf-8") as file:
            json.dump(self.tags, file, ensure_ascii=False)
        await ctx.send("Tag updated.")

    @update.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def wikia(self, ctx, *, name:str):
        result = self._search(name)
        if not result:
            await ctx.send("Can't find {} in database.".format(name))
            return
        else:
            await ctx.send("Do you mean:\n```\n{}\n<>: cancel\n```".format('\n'.join([str(index+1)+": "+d.name for index, d in enumerate(result)])))
            msg = await self.bot.wait_for("message", check=lambda m:m.author==ctx.message.author)
            try:
                index = int(msg.content)-1
                if index in range(len(result)):
                    daemon = result[index]
                else:
                    return
            except:
                return
        new_daemon = await self.bot.loop.run_in_executor(None, self._search_wikia, daemon)
        self.daemons[new_daemon.name] = new_daemon
        new_daemon.to_file()
        await ctx.send("Updated.")

    def _search_wikia(self, daemon):
        try:
            base_name = daemon.name[:daemon.name.index("[")-1]
            form = f"{daemon.name[daemon.name.index('[')+1:-1]} Form"
        except:
            base_name = daemon.name
            form = "Original Form"

        url = f"http://otogi.wikia.com/wiki/{quote(base_name)}"
        with rq.urlopen(url) as request:
            raw_data = request.read().decode("utf-8")

        bs_data = BS(raw_data, "html.parser")

        for script in bs_data(["script", "style"]):
            script.extract()
        text = bs_data.get_text().replace(u'\xa0', u' ')
        text = re.sub(r'\n\s*\n', r'\n', text.strip(), flags=re.M)
        unprocess_data = text.split("Comments")[1]
        data = unprocess_data[unprocess_data.find(daemon.name):]
        data = data[:data.find("Voice Actor")]
        data = data.replace("(MAX/MLB)", "").replace("(MAX)", "")
        data = [l.strip() for l in data.splitlines()]
        data.remove("Special Bonds")
        for d in data[8:]:
            if "N/A" in d or d.startswith("(Lv.") or "--" in d:
                data.remove(d)

        new_daemon = Daemon(name=data[0], alias=daemon.name, pic_url=None, atk="",
                            hp="", skill=[], ability=[], bond=[])
        new_daemon.name = data[0]
        new_daemon.alias = daemon.alias
        atk = data[3].split("/")[1]
        hp = data[5].split("/")[1]
        mlb_stat = data[7].split("/")
        try:
            new_daemon.atk = f"{atk}/{mlb_stat[0]}"
            new_daemon.hp = f"{hp}/{mlb_stat[1]}"
        except:
            new_daemon.atk = atk
            new_daemon.hp = hp
        for i, d in enumerate(data):
            if i > 7 and i%2 == 0:
                if ">" in d:
                    new_daemon.bond.append({"name": d, "value": data[i+1]})
                elif "(Lv" in d:
                    new_daemon.ability.append({"name": d, "value": data[i+1]})
                else:
                    new_daemon.skill.append({"name": d, "value": data[i+1]})
        delimiters = (' [', ']', ' ')
        regexPattern = '|'.join(map(re.escape, delimiters))
        name_pattern = "_".join(' '.join(re.split(regexPattern, daemon.name)).strip().split())
        wiki_url = f"http://otogi.wikia.com/wiki/File:{quote(name_pattern)}.png"
        try:
            with rq.urlopen(wiki_url) as request:
                html = request.read().decode("utf-8").split("Full resolution</a> (<a href=\"")
                process_html = html[1].split("\"")
                new_daemon.pic_url = process_html[0]
        except:
            pass
        return new_daemon

    @update.command()
    @checks.owner_only()
    async def data(self, ctx):
        self.__init__(self.bot)
        await ctx.send("Daemon database updated.")

    @commands.command()
    async def mybox(self, ctx, *, member:discord.Member=None):
        try:
            target = member
            player = self._find_player(target.id)
        except:
            target = ctx.message.author
            player = self._find_player(target.id)
        player.sort_daemons()
        embed = discord.Embed(title="Mochi: {}{}".format(player.mochi, self.emoji["mochi"]), colour=discord.Colour.blue())
        embed.set_author(name=target.display_name+"'s box", icon_url=target.avatar_url)

        def data(i):
            des = ""
            for daemon in player.daemons:
                if daemon.rarity == i:
                    des += daemon.name + " lb" + str(daemon.lb) + "\n"
            if des:
                if len(des)>800:
                    return des[:800] + "...>>"
                else:
                    return des
            else:
                return "None"
        embed.add_field(name="{0}{0}{0}".format(self.emoji["star"]), value=data(3))
        embed.add_field(name="{0}{0}{0}{0}".format(self.emoji["star"]), value=data(4))
        embed.add_field(name="{0}{0}{0}{0}{0}".format(self.emoji["star"]), value=data(5), inline=False)
        embed.set_footer(text="If you see \"...>>\" it means your daemon list is too long. Consider using [>>mochiall].")
        await ctx.send(embed=embed)

    def _mini_search(self, player, name, lb):
        result = self._search(name)
        try:
            daemon = result[-1]
        except:
            return None
        for r in result:
            if name.lower() == r.name.lower():
                daemon = r
                break
        for d in player.daemons:
            if d.name == daemon.name and d.lb == lb:
                return d
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
        player = self._find_player(ctx.message.author.id)
        data = [n.rstrip() for n in names.split("&")]
        number_of_daemons = 0
        total_mochi = 0
        for name in data:
            daemon = self._process_name(player, name)
            try:
                player.cmd_mochi(daemon)
                number_of_daemons += 1
                total_mochi += daemon.cost
            except AttributeError:
                pass
        await ctx.send("{} sold {} daemon(s) for {}{}.\n{} failed.".format(ctx.message.author.display_name, number_of_daemons, total_mochi, self.emoji["mochi"], len(data)-number_of_daemons))

    @commands.command()
    async def mochibulk(self, ctx, *, names):
        player = self._find_player(ctx.message.author.id)
        data = [n.rstrip() for n in names.split("&")]
        number_of_daemons = 0
        failed = 0
        total_mochi = 0
        for name in data:
            try:
                daemon_name = self._process_name(player, name).name
                for daemon in player.daemons:
                    if daemon.name == daemon_name:
                        player.cmd_mochi(daemon)
                        number_of_daemons += 1
                        total_mochi += daemon.cost
            except AttributeError:
                failed += 1
        await ctx.send("{} sold {} daemon(s) for {}{}.\n{} failed.".format(ctx.message.author.display_name, number_of_daemons, total_mochi, self.emoji["mochi"], failed))

    @commands.command()
    async def mochiall(self, ctx, rarity:int):
        player = self._find_player(ctx.message.author.id)
        total = 0
        for daemon in player.daemons[:]:
            if daemon.rarity==rarity:
                total += daemon.cost
                player.cmd_mochi(daemon)
        await ctx.send("{} sold all {}* daemons for {}{}.".format(ctx.message.author.display_name, rarity, total, self.emoji["mochi"]))

    @commands.command()
    async def gift(self, ctx, member:discord.Member, *, name):
        myself = self._find_player(ctx.message.author.id)
        player = self._find_player(member.id)
        daemon = self._process_name(myself, name)
        if daemon:
            player.gimme(myself, daemon)
            await ctx.send("{} gave {} {} lb{}.".format(ctx.message.author.display_name, member.display_name, daemon.name, daemon.lb))

    @commands.command()
    async def gimme(self, ctx, member:discord.Member, price:int, *, name):
        myself = self._find_player(ctx.message.author.id)
        player = self._find_player(member.id)
        daemon = self._process_name(player, name)
        if daemon:
            if myself.mochi >= price:
                await ctx.send("Would {} trade {} lb{} for {}{}? Y/N".format(member.mention, daemon.name, daemon.lb, price, self.emoji["mochi"]))
                msg = await self.bot.wait_for("message", check=lambda m:m.author==member)
                if msg.content.lower() == "y":
                    myself.gimme(player, daemon)
                    player.mochi += price
                    myself.mochi -= price
                    await ctx.send("Trade succeed.")
                else:
                    await ctx.send("Trade failed.")
            else:
                await ctx.send("{}, you don't have that many {}.".format(ctx.message.author.display_name, self.emoji["mochi"]))
        else:
            await ctx.send("{} doesn't have {}.".format(member.display_name, name))

    def lb_that(self, player, name):
        all_them = [d for d in player.daemons if d.name==name]
        all_them.sort(key = lambda x: -x.lb)
        first = 0
        last = len(all_them) - 1
        while first < last:
            if all_them[first].lb + all_them[last].lb <= 3:
                all_them[first].lb += all_them[last].lb + 1
                for i, d in enumerate(player.daemons):
                    if d.name==all_them[last].name and d.lb==all_them[last].lb:
                        player.daemons.pop(i)
                        break
                all_them.pop(last)
                last -= 1
            else:
                first += 1

    @commands.command()
    async def limitbreak(self, ctx, *, name=None):
        player = self._find_player(ctx.message.author.id)
        if name:
            good_name = self._process_name(player, name)
            self.lb_that(player, good_name)
        else:
            all_names = []
            for d in player.daemons:
                if d.name not in all_names:
                    all_names.append(d.name)
            for n in all_names:
                self.lb_that(player, n)
        player.to_file()
        await ctx.send("Limit breaking succeed.")

    @commands.group()
    async def exchange(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @exchange.command(name="get")
    async def exchange_get(self, ctx, *, name):
        pass

#======================================================================================================

def setup(bot):
    bot.add_cog(OtogiBot(bot))
