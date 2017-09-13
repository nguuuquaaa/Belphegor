import discord
from discord.ext import commands
import os
from PIL import Image
from io import BytesIO
from .utils import config, request
import aiohttp
import asyncio

#==================================================================================================================================================

class Chip:
    def __init__(self, ctype="Chip", nameEN=None, nameJP=None, url_thumbnail=None, url_swiki=None, url_weapon=None, active=None, class_bonus=[],
                 rarity=None, HP=None, CP=None, element=None, element_value=None, cost=None, frame=None, description=None, released_ability=None):
        self.nameEN = nameEN
        self.nameJP = nameJP
        self.ctype = ctype
        self.active = active
        self.class_bonus = class_bonus
        self.rarity = rarity
        self.cost = cost
        self.element = element
        self.element_value = element_value
        self.HP = HP
        self.CP = CP
        self.frame = frame
        self.description = description
        self.url_swiki = url_swiki
        self.url_weapon = url_weapon
        self._url_thumbnail = url_thumbnail
        self.released_ability = released_ability

    @property
    def url_thumbnail(self):
        if "://" in self._url_thumbnail:
            return self._url_thumbnail
        else:
            return "http://i.imgur.com/0dD1lVh.png"

    def embed_form(self, emoji):
        embed = discord.Embed(title=self.nameEN, url=self.url_weapon, colour=discord.Colour.blue())
        embed.set_thumbnail(url=self.url_thumbnail)
        try:
            if "Add" in self.released_ability and "element" in self.released_ability:
                stuff = self.released_ability.split()
                another_element = emoji[stuff[2]]
                if another_element:
                    element = "{}{}{}{}".format(emoji[self.element], self.element_value, another_element, stuff[1])
                else:
                    another_element = emoji[stuff[1]]
                    element = "{}{}{}".format(emoji[self.element], another_element, self.element_value)
            else:
                element = "{}{}".format(emoji[self.element], self.element_value)
        except:
            element = "{}{}".format(emoji[self.element], self.element_value)
        embed.add_field(name="**{}**".format(self.ctype), value="**Rarity** {}\*\n**Class bonus** {}{}\n**HP/CP** {}/{}".format(self.rarity, emoji[self.class_bonus[0]], emoji[self.class_bonus[1]], self.HP, self.CP))
        embed.add_field(name="**{}**".format(self.active), value="**Cost** {}\n**Element** {}\n**Multiplication** {}".format(self.cost, element, self.frame))
        embed.add_field(name="Description", value=self.description, inline=False)
        embed.set_author(name=self.nameJP, url=self.url_swiki)
        if self.released_ability:
            embed.add_field(name="Released ability", value=self.released_ability, inline=False)
        return embed

    @classmethod
    def from_file(cls, name, file):
        data = [d.strip() for d in file.readlines()]
        try:
            new_chip = cls(data[0], name, data[1], data[2], data[3],
                           data[4], data[5], data[6].split(), int(data[7]), int(data[8]), int(data[9]),
                           data[10], int(data[11]), int(data[12]), data[13], data[14], data[15])
        except IndexError:
            new_chip = cls(data[0], name, data[1], data[2], data[3],
                       data[4], data[5], data[6].split(), int(data[7]), int(data[8]), int(data[9]),
                       data[10], int(data[11]), int(data[12]), data[13], data[14])
        return new_chip

#==================================================================================================================================================

class EsBot():
    '''
    PSO2es chip info.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.chip_library = []
        for chip_type in ("weaponoid", "character", "pa_tech", "collab"):
            for i in os.listdir(f"{config.data_path}/chip/{chip_type}"):
                with open(f"{config.data_path}/chip/{chip_type}/{i}", encoding='utf-8') as file:
                    new_chip = Chip.from_file(i[:-4], file)
                    self.chip_library.append(new_chip)
        test_guild = self.bot.get_guild(config.test_guild_id)
        self.emoji = {}
        for emoji_name in ("fire", "ice", "lightning", "wind", "light", "dark",
                           "hu", "fi", "ra", "gu", "fo", "te", "br", "bo"):
            self.emoji[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild.emojis)

    def _search(self, name):
        result = []
        for chip in self.chip_library:
            check = True
            for word in name.split():
                if word.lower() not in chip.nameEN.lower():
                    check = False
                    break
            if check:
                result.append(chip)
        if not result:
            for chip in self.chip_library:
                check = True
                for word in name:
                    if word not in chip.nameJP:
                        check = False
                        break
                if check:
                    result.append(chip)
        if len(result)>1:
            for chip in result:
                if name.lower() == chip.nameEN.lower() or name == chip.nameJP:
                    result = [chip,]
                    break
        return result

    @commands.command(aliases=["c",])
    async def chip(self, ctx, *, name:str):
        result = self._search(name)
        if not result:
            await ctx.send("Can't find {} in database.".format(name))
            return
        if len(result) > 1:
            await ctx.send("Do you mean:\n```\n{}\nc: cancel\n```".format('\n'.join([str(index+1)+": "+c.nameEN for index, c in enumerate(result)])))
            msg = await self.bot.wait_for("message", check=lambda m:m.author==ctx.author)
            try:
                if int(msg.content)-1 in range(len(result)):
                    chip = result[int(msg.content)-1]
            except:
                return
        else:
            chip = result[0]
        await ctx.send(embed=chip.embed_form(self.emoji))

    @commands.command()
    async def team(self, ctx, *, load:str):
        with ctx.channel.typing():
            chips = []
            for c in load.split(">"):
                try:
                    chips.append(self._search(c)[-1])
                except:
                    pass
            pics = []
            for index, chip in enumerate(chips):
                bytes_ = await request.fetch(self.bot.session, chip.url_thumbnail)
                pics.append(Image.open(BytesIO(bytes_)))

            def construct():
                team_pic = Image.new('RGBA', (520,120))
                pics[0].thumbnail((120, 120))
                team_pic.paste(pics[0], (0, 0))
                for index, pic in enumerate(pics[1:]):
                    pic.thumbnail((100, 100))
                    team_pic.paste(pic, (120+index*100,20))
                return team_pic

            team_pic = await self.bot.loop.run_in_executor(None, construct)
            current_load = BytesIO()
            team_pic.save(current_load, format = "png")
            current_load.name = "current_load.png"
            current_load.seek(0)
            await ctx.send(file=discord.File(current_load))

            element_value = {"fire":0, "ice":0, "lightning":0, "wind":0, "light":0, "dark":0}
            for chip in chips:
                element_value[chip.element] = element_value[chip.element] + chip.element_value
                try:
                    if "Add" in chip.released_ability and "element" in chip.released_ability:
                        new_element = chip.released_ability.split()[1]
                        if new_element in element_value:
                            element_value[new_element] += chip.element_value
                        else:
                            another_element = chip.released_ability.split()[2]
                            element_value[another_element] += int(new_element)
                except:
                    pass
            new_embed = discord.Embed(colour=discord.Colour.teal())
            new_embed.add_field(name="Cost: {}".format(sum([i.cost if not i.released_ability else i.cost-6 if "6." in i.released_ability.split() else i.cost for i in chips])),
                                value="{}{}\n{}{}".format(self.emoji["fire"], element_value["fire"], self.emoji["wind"], element_value["wind"]))
            new_embed.add_field(name="HP: {}".format(sum([i.HP for i in chips])),
                                value="{}{}\n{}{}".format(self.emoji["ice"], element_value["ice"], self.emoji["light"], element_value["light"]))
            new_embed.add_field(name="CP: {}".format(sum([i.CP for i in chips])),
                                value="{}{}\n{}{}".format(self.emoji["lightning"], element_value["lightning"], self.emoji["dark"], element_value["dark"]))
            await ctx.send(embed=new_embed)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(EsBot(bot))
