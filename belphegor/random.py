import discord
from discord.ext import commands
from . import utils
from .utils import checks
import aiohttp
import json
import xmltodict
import random
from bs4 import BeautifulSoup as BS
import traceback
import asyncio

RATING = {
    "s": "safe",
    "q": "questionable",
    "e": "explicit"
}

#==================================================================================================================================================

class Random:
    '''
    Random pictures from various image boards.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.retry = 3
        self.sc_lock = asyncio.Lock()

    def retry_wrap(func):
        async def new_func(self, ctx, *args, **kwargs):
            retries = self.retry
            while retries > 0:
                try:
                    embed = await func(self, *args, **kwargs)
                    return await ctx.send(embed=embed)
                except (IndexError, KeyError):
                    return await ctx.send("No result found.")
                except:
                    print(traceback.format_exc())
                    retries -= 1
            await ctx.send("Query failed. Please try again.")
        return new_func

    @commands.group(aliases=["random",])
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def r(self, ctx):
        if ctx.invoked_subcommand is None:
            cmd = self.bot.get_command("help").get_command("random")
            await ctx.invoke(cmd)

    @retry_wrap
    async def get_image_danbooru(self, tag, *, safe):
        params = {
            "tags":   f"{'' if safe else '-'}rating:safe {tag}",
            "limit":  1,
            "random": "true"
        }
        bytes_ = await utils.fetch(self.bot.session, "https://danbooru.donmai.us/posts.json", params=params)
        pic = json.loads(bytes_)[0]
        tag_str = utils.split_page(pic.get('tag_string', ''), 1800)
        embed = discord.Embed(
            title="Danbooru",
            description=f"**Tags:** {utils.discord_escape(tag_str[0])}\n\n**Rating:** {RATING.get(pic.get('rating'), 'N/A')}",
            url=f"https://danbooru.donmai.us/posts/{pic['id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=f"https://danbooru.donmai.us{pic['file_url']}")
        return embed

    @retry_wrap
    async def get_image_konachan(self, tags, *, safe, page=1):
        params = {
            "tags":   f"{'' if safe else '-'}rating:safe order:random {tags}",
            "limit":  1,
            "page":   page
        }
        domain = "net" if safe else "com"
        bytes_ = await utils.fetch(self.bot.session, f"http://konachan.{domain}/post.json", params=params)
        pic = json.loads(bytes_)[0]
        tag_str = utils.split_page(pic.get('tags', ''), 1800)
        embed = discord.Embed(
            title="Konachan",
            description=f"**Tags:** {utils.discord_escape(tag_str[0])}\n\n**Rating:** {RATING.get(pic.get('rating'), 'N/A')}",
            url=f"http://konachan.{domain}/post/show/{pic['id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=pic['sample_url'].strip("/"))
        return embed

    @retry_wrap
    async def get_image_safebooru(self, tags, *, safe, page=1):
        params = {
            "page":   "dapi",
            "s":      "post",
            "q":      "index",
            "tags":   f"{'' if safe else '-'}rating:safe {tags}",
            "limit":  100,
            "pid":   page
        }
        bytes_ = await utils.fetch(self.bot.session, "https://safebooru.org/index.php", params=params)
        data = xmltodict.parse(bytes_.decode("utf-8"))
        pic = random.choice(data['posts']['post'])
        tag_str = utils.split_page(pic.get('@tags', '').strip(), 1800)
        embed = discord.Embed(
            title="Safebooru",
            description=f"**Tags:** {utils.discord_escape(tag_str[0])}\n\n**Rating:** {RATING.get(pic.get('@rating'), 'N/A')}",
            url=f"https://safebooru.org/index.php?page=post&s=view&id={pic['@id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=f"http:{pic['@file_url']}")
        return embed

    @retry_wrap
    async def get_image_yandere(self, tags, *, safe, page=1):
        params = {
            "tags":   f"{'' if safe else '-'}rating:s {tags}",
            "limit":  100,
            "page":   page
        }
        bytes_ = await utils.fetch(self.bot.session, "https://yande.re/post.json", params=params)
        pics = json.loads(bytes_)
        pic = random.choice(pics)
        tag_str = utils.split_page(pic.get('tags', ''), 1800)
        embed = discord.Embed(
            title="Yandere",
            description=f"**Tags:** {utils.discord_escape(tag_str[0])}\n\n**Rating:** {RATING.get(pic.get('rating'), 'N/A')}",
            url=f"https://yande.re/post/show/{pic['id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=pic['sample_url'])
        return embed

    @retry_wrap
    async def get_image_sancom(self, tags):
        params = {
            "tags":   f"-rating:s order:random {tags}",
            "commit": "Search"
        }
        bytes_ = await utils.fetch(self.bot.session, "https://chan.sankakucomplex.com/", params=params)
        data = BS(bytes_.decode("utf-8"), "lxml")
        items = tuple(
            data.find_all(
                lambda x:
                    getattr(x, "name", None)=="span"
                    and x.get("class", None)==["thumb", "blacklisted"]
                    and x.parent.get("class", None)!=["popular-preview-post"]
            )
        )
        item = random.choice(items)
        post_url = f"https://chan.sankakucomplex.com{item.find('a')['href']}"
        bytes_ = await utils.fetch(self.bot.session, post_url)
        post_data = BS(bytes_.decode("utf-8"), "lxml")
        img_link = post_data.find("a", id="highres")
        relevant = post_data.find("ul", id="tag-sidebar")
        pic_tags = " ".join([t.find("a").text.strip().replace(" ", r"\_") for t in relevant.find_all(True, recursive=False)])
        tag_str = utils.split_page(pic_tags, 1800)
        stats = post_data.find("div", id="stats")
        rating = stats.find("ul").find_all(True, recursive=False)[-1].get_text().strip()
        rating = rating.partition(" ")[2]
        embed = discord.Embed(
            title="Sankaku Complex",
            description=f"**Tags:** {tag_str[0]}\n\n**Rating:** {rating}",
            url=post_url,
            colour=discord.Colour.red()
        )
        embed.set_image(url=f"https:{img_link['href']}")
        return embed

    @r.command(aliases=["d",])
    async def danbooru(self, ctx, tag=""):
        async with ctx.typing():
            await self.get_image_danbooru(ctx, tag, safe=True)

    @r.command(aliases=["dh"])
    @checks.nsfw()
    async def danbooru_h(self, ctx, tag=""):
        async with ctx.typing():
            await self.get_image_danbooru(ctx, tag, safe=False)

    @r.command(aliases=["k",])
    async def konachan(self, ctx, *, tags=""):
        async with ctx.typing():
            await self.get_image_konachan(ctx, tags, safe=True)

    @r.command(aliases=["kh",])
    @checks.nsfw()
    async def konachan_h(self, ctx, *, tags=""):
        async with ctx.typing():
            await self.get_image_konachan(ctx, tags, safe=False)

    @r.command(aliases=["s",])
    async def safebooru(self, ctx, *, tags=""):
        async with ctx.typing():
            await self.get_image_safebooru(ctx, tags, safe=True)

    @r.command(aliases=["y",])
    async def yandere(self, ctx, *, tags=""):
        async with ctx.typing():
            await self.get_image_yandere(ctx, tags, safe=True)

    @r.command(aliases=["sc",])
    @checks.nsfw()
    async def sancom(self, ctx, *, tags=""):
        async with self.sc_lock:
            async with ctx.typing():
                await self.get_image_sancom(ctx, tags)

    @r.command()
    @checks.owner_only()
    async def setretry(self, ctx, number:int):
        if number <= 0:
            await ctx.send("Number must be positive.")
        elif number > 10:
            await ctx.send("Sorry, can't retry that many times.")
        else:
            self.retry = number
            await ctx.send(f"Number of retries has been set to {number}.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Random(bot))
