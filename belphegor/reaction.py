import discord
from discord.ext import commands
import random
from .utils import config

#==================================================================================================================================================

class Reaction:
    def __init__(self, bot):
        self.bot = bot
        self.links = {"wut":        ("http://i.imgur.com/DISTSLM.gif",),

                      "shock":      ("http://i.imgur.com/AULoJbG.gif",
                                     "http://i.imgur.com/LOjYw9G.gif",
                                     "http://i.imgur.com/dqPEqbm.gif",
                                     "http://i.imgur.com/aEOAnYI.gif"),

                      "fliptable":  ("http://i.imgur.com/B2Qq1H9.gif",
                                     "http://i.imgur.com/7ikdAHG.gif",
                                     "http://i.imgur.com/C54jkI7.gif"),

                      "lmao":       ("http://i.imgur.com/G3cQjyl.gif",
                                     "http://i.imgur.com/jNhQ0LT.gif",
                                     "http://i.imgur.com/widchH6.gif"),

                      "damnyou":    ("http://i.imgur.com/FjQ0Emf.gif",
                                     "http://i.imgur.com/lL11RBr.gif",
                                     "http://i.imgur.com/3UXSfFT.gif",
                                     "http://i.imgur.com/xcLkeTk.gif",
                                     "http://i.imgur.com/Ey2qYil.gif",
                                     "http://i.imgur.com/W3Sjbwy.gif"),

                      "uwa":        ("http://i.imgur.com/ijWjY7G.gif",
                                     "http://i.imgur.com/QL1oNqA.gif"),

                      "yay":        ("http://i.imgur.com/RM4WZZt.gif",
                                     "http://i.imgur.com/FBLltze.gif",
                                     "http://i.imgur.com/CrWBRvs.gif"),

                      "goodnight":  ("http://i.imgur.com/p5PFUd1.gif",),

                      "morepls":    ("http://i.imgur.com/rWiJiDG.gif",
                                     "http://i.imgur.com/MQ2AsSw.gif"),

                      "cry":        ("http://i.imgur.com/0GBqYX3.gif",
                                     "http://i.imgur.com/pkRzYDF.gif"),

                      "loli":       ("http://i.imgur.com/AtOVXCj.gif",),}
        for name, links in self.links.items():
            self.add_meme(name, links)

    def add_meme(self, name, links):
        setattr(self, "meme_" + name, [])
        for link in links:
            new_embed = discord.Embed()
            new_embed.set_image(url=link)
            getattr(self, "meme_" + name).append(new_embed)

    @commands.command()
    async def lenny(self, ctx):
        await ctx.send("( ͡° ͜ʖ ͡°)")

    @commands.command(aliases=["huh",])
    async def wut(self, ctx):
        await ctx.send(embed=random.choice(self.meme_wut))

    @commands.command(aliases=["shocked",])
    async def shock(self, ctx):
        await ctx.send(embed=random.choice(self.meme_shock))

    @commands.command(aliases=["tableflip",])
    async def fliptable(self, ctx):
        await ctx.send(embed=random.choice(self.meme_fliptable))

    @commands.command(aliases=["lol"])
    async def lmao(self, ctx):
        await ctx.send(embed=random.choice(self.meme_lmao))

    @commands.command(aliases=["angry", "gotohell"])
    async def damnyou(self, ctx):
        await ctx.send(embed=random.choice(self.meme_damnyou))

    @commands.command(aliases=["uwaa", "waa"])
    async def uwa(self, ctx):
        await ctx.send(embed=random.choice(self.meme_uwa))

    @commands.command(aliases=["dowant", "yes"])
    async def yay(self, ctx):
        await ctx.send(embed=random.choice(self.meme_yay))

    @commands.command(aliases=["g9",])
    async def goodnight(self, ctx):
        await ctx.send(embed=random.choice(self.meme_goodnight))

    @commands.command(aliases=["lewdpls",])
    async def morepls(self, ctx):
        await ctx.send(embed=random.choice(self.meme_morepls))

    @commands.command()
    async def loli(self, ctx):
        await ctx.send(embed=random.choice(self.meme_loli))

    @commands.command()
    async def cry(self, ctx):
        await ctx.send(embed=random.choice(self.meme_cry))

    @commands.command()
    async def shrug(self, ctx):
        await ctx.send("¯\_(ツ)_/¯")

    @commands.command(aliases=["e",])
    async def emoji(self, ctx, *args):
        out = ""
        for name in args:
            emoji = discord.utils.find(lambda a:a.name==name, self.bot.get_guild(config.test_server_id).emojis)
            out += str(emoji)
        if out:
            await ctx.send(out)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Reaction(bot))
