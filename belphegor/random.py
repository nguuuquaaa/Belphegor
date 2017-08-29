import discord
from discord.ext import commands
from .utils import checks, request
import aiohttp
import json
import xmltodict
import random

#==================================================================================================================================================

class RandomBot:
    '''
    Random pictures from various image boards.
    '''

    def __init__(self, bot):
	    self.bot = bot

    @commands.group(aliases=["random",])
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def r(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(title=":frame_photo: Random image", colour = discord.Colour.teal())
            embed.add_field(name="Command", value="`>>random`, `>>r` - Get a random picture from an image board")
            embed.add_field(name="Subcommands", value=
                            "`danbooru`, `d` - [Danbooru](https://danbooru.donmai.us)\n"
                            "`safebooru`, `s` - [Safebooru](https://safebooru.org)\n"
                            "`konachan`, `k` - [Konachan](http://konachan.net)\n"
                            "`yandere`, `y` - [Yandere](https://yande.re)\n\n"
                            "`hentai`, `h` - [NSFW Danbooru](https://danbooru.donmai.us)\n"
                            "Usable in channel with nsfw prefix only")
            embed.add_field(name="Notes", value=
                            "A subcommand is meant to be used with main command.\n"
                            "For example, `>>r d touhou` is a valid command.\n\n")
            await ctx.send(embed=embed)

    async def get_image_danbooru(self, rating, tag):
        bytes_ = await request.fetch(self.bot.session, f"https://danbooru.donmai.us/posts.json?tags=rating%3A{rating}+{tag}&limit=1&random=true")
        pic = json.loads(bytes_)
        embed = discord.Embed(title="Danbooru", url=f"https://danbooru.donmai.us/posts/{pic[0]['id']}", colour=discord.Colour.red())
        embed.set_image(url=f"https://danbooru.donmai.us{pic[0]['file_url']}")
        return embed

    async def get_image_konachan(self, tags, page=1):
        bytes_ = await request.fetch(self.bot.session, f"http://konachan.net/post.json?tags={'+'.join(tags)}&limit=100&page={page}")
        pics = json.loads(bytes_)
        pic = random.choice(pics)
        if pic["rating"] != "s":
            return discord.Embed(title="NSFW", url=f"http://konachan.net/post/show/{pic['id']}", colour=discord.Colour.red())
        embed = discord.Embed(title="Konachan", url=f"http://konachan.net/post/show/{pic['id']}", colour=discord.Colour.red())
        embed.set_image(url=f"http:{pic['sample_url']}")
        return embed

    async def get_image_safebooru(self, tags, page=1):
        bytes_ = await request.fetch(self.bot.session, f"https://safebooru.org/index.php?page=dapi&s=post&q=index&tags={'+'.join(tags)}&limit=100&pid={page}")
        data = xmltodict.parse(bytes_.decode("utf-8"))
        pic = random.choice(data['posts']['post'])
        embed = discord.Embed(title="Safebooru", url=f"https://safebooru.org/index.php?page=post&s=view&id={pic['@id']}", colour=discord.Colour.red())
        embed.set_image(url=f"http:{pic['@file_url']}")
        return embed

    async def get_image_yandere(self, tags, page=1):
        bytes_ = await request.fetch(self.bot.session, f"https://yande.re/post.json?tags={'+'.join(tags)}&limit=100&page={page}")
        pics = json.loads(bytes_)
        pic = random.choice(pics)
        if pic["rating"] != "s":
            return discord.Embed(title="NSFW", url=f"https://yande.re/post/show/{pic['id']}", colour=discord.Colour.red())
        embed = discord.Embed(title="Yandere", url=f"https://yande.re/post/show/{pic['id']}", colour=discord.Colour.red())
        embed.set_image(url=pic['sample_url'])
        return embed

    @r.command(aliases=["h",])
    @checks.nsfw()
    async def hentai(self, ctx, tag=""):
        with ctx.typing():
            embed = await self.get_image_danbooru("explicit", tag)
            await ctx.send(embed=embed)

    @r.command(aliases=["d",])
    async def danbooru(self, ctx, tag=""):
        with ctx.typing():
            embed = await self.get_image_danbooru("safe", tag)
            await ctx.send(embed=embed)

    @r.command(aliases=["k",])
    async def konachan(self, ctx, *tags):
        with ctx.typing():
            embed = await self.get_image_konachan(tags)
            await ctx.send(embed=embed)

    @r.command(aliases=["s",])
    async def safebooru(self, ctx, *tags):
        with ctx.typing():
            embed = await self.get_image_safebooru(tags)
            await ctx.send(embed=embed)

    @r.command(aliases=["y",])
    async def yandere(self, ctx, *tags):
        with ctx.typing():
            embed = await self.get_image_yandere(tags)
            await ctx.send(embed=embed)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(RandomBot(bot))