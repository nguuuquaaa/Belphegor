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

#==================================================================================================================================================

class Chip:
    def __init__(self, data):
        data.pop("_id", None)
        for key, value in data.items():
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
        data.pop("_id", None)
        for key, value in data.items():
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
            usable_classes = ''.join([str(emojis[cl]) for cl in CLASS_DICT.values()])
        else:
            usable_classes = ''.join([str(emojis[cl]) for cl in self.classes])
        embed.description = f"{description}\n{usable_classes}"
        if self.pic_url:
            embed.set_thumbnail(url=self.pic_url)
        embed.add_field(name="Requirement", value=self.requirement)
        max_atk = self.atk['max']
        embed.add_field(name="ATK", value="\n".join([f"{emojis[e]}{max_atk[e]}" for e in ATK_EMOJI]))
        for prp in self.properties:
            embed.add_field(name=f"{emojis[prp['type']]}{prp['name']}", value=prp['description'], inline=False)
        return embed

#==================================================================================================================================================

class EsBot():
    '''
    PSO2es chip info.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.pool = {
            "chip": (Chip, bot.db.chip_library),
            "weapon": (Weapon, bot.db.weapon_list)
        }
        test_guild = self.bot.get_guild(config.TEST_GUILD_ID)
        self.emojis = {}
        for emoji_name in (
            "fire", "ice", "lightning", "wind", "light", "dark",
            "hu", "fi", "ra", "gu", "fo", "te", "br", "bo", "su", "hr",
            "satk", "ratk", "tatk", "ability", "potential", "set_effect",
            "pa", "saf", "star_0", "star_1", "star_2", "star_3", "star_4"
        ):
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild.emojis)
        for emoji_name in CATEGORY_DICT:
            self.emojis[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild.emojis)

    async def _search(self, name, pool_name, *, no_prompt=False):
        name = name.lower()
        pool_list = self.pool[pool_name]
        pool = pool_list[1]
        cls = pool_list[0]
        regex = ".*?".join(map(re.escape, name.split()))
        cursor = pool.find({
            "$or": [
                {
                    "en_name": {
                        "$regex": regex,
                        "$options": "i"
                    }
                },
                {
                    "jp_name": {
                        "$regex": regex,
                        "$options": "i"
                    }
                }
            ]
        })
        if no_prompt:
            async for item in cursor:
                if name in (item["en_name"].lower(), item["jp_name"].lower()):
                    return cls(item)
            item = cursor.next_object()
            if item:
                return cls(item)
            else:
                return None
        else:
            return [cls(item) async for item in cursor]

    async def filter(self, ctx, name, result, *, prompt_all=False):
        if not result:
            await ctx.send(f"Can't find {name} in database.")
            return None
        elif not prompt_all:
            if len(result) == 1:
                return result[0]
        await ctx.send("Do you mean:\n```\n{}\n<>: cancel\n```".format('\n'.join([f"{index+1}: {item.en_name}" for index, item in enumerate(result)])))
        msg = await self.bot.wait_for("message", check=lambda m:m.author.id==ctx.author.id)
        try:
            index = int(msg.content)-1
        except:
            return None
        if index in range(len(result)):
            return result[index]
        else:
            return None

    @commands.command(aliases=["c",])
    async def chip(self, ctx, *, name):
        result = await self._search(name, "chip")
        chip = await self.filter(ctx, name, result)
        if not chip:
            return
        await ctx.send(embed=chip.embed_form(self))

    @commands.command(aliases=["cjp",])
    async def chipjp(self, ctx, *, name):
        result = await self._search(name, "chip")
        chip = await self.filter(ctx, name, result)
        if not chip:
            return
        await ctx.send(embed=chip.embed_form(self, "jp"))

    @commands.command(aliases=["w",])
    async def weapon(self, ctx, *, name):
        result = await self._search(name, "weapon")
        weapon = await self.filter(ctx, name, result)
        if not weapon:
            return
        await ctx.send(embed=weapon.embed_form(self))

    @commands.command()
    @checks.owner_only()
    async def wupdate(self, ctx, *args):
        msg = await ctx.send("Fetching...")
        weapon_list = self.pool["weapon"][1]
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
        await weapon_list.delete_many({"category": {"$in": tuple(urls.keys())}})
        await weapon_list.insert_many(weapons)
        print("Done everything.")
        await msg.edit(content = "Done.")

    def bs_parse(self, category, bytes_):
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
                weapon["pic_url"] = f"https://pso2.arks-visiphone.com{relevant[1].find('img')['src'].replace('64px-', '240px-')}"
            except:
                weapon["pic_url"] = None
            weapon["requirement"] = utils.unifix(relevant[3].get_text())
            weapon["atk"] = {
                "base": {ATK_EMOJI[i]: int(l.strip()) for i, l in enumerate(relevant[5].find_all(text=True))},
                "max":  {ATK_EMOJI[i]: int(l.strip()) for i, l in enumerate(relevant[6].find_all(text=True))}
            }
            weapon["properties"] = []
            for child in relevant[7].find_all(True, recursive=False):
                if child.name == "img":
                    cur = {"type": ICON_DICT[child["alt"]]}
                elif child.name == "span":
                    cur["name"] = utils.unifix(child.get_text())
                    cur["description"] = utils.unifix(html.unescape(child["data-simple-tooltip"]).replace("<br>", "\n"))
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

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(EsBot(bot))