import discord
from discord.ext import commands
from . import utils
from .utils import checks, config
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

class RImage:
    '''
    Random pictures from various image boards.
    Also sauce find. Since everyone needs sauce.
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

    @commands.group(aliases=["random"])
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def r(self, ctx):
        '''
            `>>random`
            Base command. Does nothing by itself.
        '''
        if ctx.invoked_subcommand is None:
            pass

    @retry_wrap
    async def get_image_danbooru(self, tag, *, safe):
        params = {
            "tags":   f"{'' if safe else '-'}rating:safe {tag}",
            "limit":  1,
            "random": "true"
        }
        bytes_ = await self.bot.fetch("https://danbooru.donmai.us/posts.json", params=params)
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
        bytes_ = await self.bot.fetch(f"http://konachan.{domain}/post.json", params=params)
        pic = json.loads(bytes_)[0]
        tag_str = utils.split_page(pic.get('tags', ''), 1800)
        embed = discord.Embed(
            title="Konachan",
            description=f"**Tags:** {utils.discord_escape(tag_str[0])}\n\n**Rating:** {RATING.get(pic.get('rating'), 'N/A')}",
            url=f"http://konachan.{domain}/post/show/{pic['id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=f"http:{pic['file_url']}")
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
        bytes_ = await self.bot.fetch("https://safebooru.org/index.php", params=params)
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
        bytes_ = await self.bot.fetch("https://yande.re/post.json", params=params)
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
        bytes_ = await self.bot.fetch("https://chan.sankakucomplex.com/", params=params)
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
        bytes_ = await self.bot.fetch(post_url)
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
        '''
            `>>random danbooru <optional: tag>`
            Get a random safe-rating image from danbooru.
        '''
        async with ctx.typing():
            await self.get_image_danbooru(ctx, tag, safe=True)

    @r.command(aliases=["dh"])
    @checks.nsfw()
    async def danbooru_h(self, ctx, tag=""):
        '''
            `>>random danbooru_h <optional: tag>`
            Get a random questionable/explicit-rating image from danbooru.
            Only usable in nsfw channel.
        '''
        async with ctx.typing():
            await self.get_image_danbooru(ctx, tag, safe=False)

    @r.command(aliases=["k",])
    async def konachan(self, ctx, *, tags=""):
        '''
            `>>random konachan <optional: tag>`
            Get a random safe-rating image from konachan.
        '''
        async with ctx.typing():
            await self.get_image_konachan(ctx, tags, safe=True)

    @r.command(aliases=["kh",])
    @checks.nsfw()
    async def konachan_h(self, ctx, *, tags=""):
        '''
            `>>random konachan_h <optional: tag>`
            Get a random questionable/explicit-rating image from konachan.
            Only usable in nsfw channel.
        '''
        async with ctx.typing():
            await self.get_image_konachan(ctx, tags, safe=False)

    @r.command(aliases=["s",])
    async def safebooru(self, ctx, *, tags=""):
        '''
            `>>random safebooru <optional: list of tags>`
            Get a random safe-rating image from safebooru.
        '''
        async with ctx.typing():
            await self.get_image_safebooru(ctx, tags, safe=True)

    @r.command(aliases=["y",])
    async def yandere(self, ctx, *, tags=""):
        '''
            `>>random yandere <optional: list of tags>`
            Get a random questionable/explicit-rating image from yandere.
        '''
        async with ctx.typing():
            await self.get_image_yandere(ctx, tags, safe=True)

    @r.command(aliases=["sc",])
    @checks.nsfw()
    async def sancom(self, ctx, *, tags=""):
        '''
            `>>random sancom <optional: 1 or 2 tags>`
            Get a random questionable/explicit-rating image from Sankaku Complex.
            Only usable in nsfw channel.
        '''
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

    @commands.command()
    async def saucenao(self, ctx, url=None):
        '''
            `>>saucenao <optional: either uploaded image or url>`
            Find the sauce of the image.
            If no argument is provided, wait 2 minutes for uploaded image.
        '''
        if not url:
            msg = ctx.message
            if not msg.attachments:
                await msg.add_reaction("\U0001f504")
                try:
                    msg = await self.bot.wait_for("message", check=lambda m:m.author.id==ctx.author.id and m.attachments, timeout=120)
                except asyncio.TimeoutError:
                    pass
                finally:
                    try:
                        await ctx.message.clear_reactions()
                    except:
                        pass
            url = msg.attachments[0].url
        async with ctx.typing():
            payload = aiohttp.FormData()
            payload.add_field("file", b"", filename="", content_type="application/octet-stream")
            payload.add_field("url", url)
            payload.add_field("frame", "1")
            payload.add_field("hide", "0")
            payload.add_field("database", "999")
            async with self.bot.session.post("https://saucenao.com/search.php", headers={"User-Agent": config.USER_AGENT}, data=payload) as response:
                bytes_ = await response.read()
            data = BS(bytes_.decode("utf-8"), "lxml")
            result = []
            hidden_result = []
            for tag in data.find_all(lambda x: x.name=="div" and x.get("class") in [["result"], ["result", "hidden"]] and not x.get("id")):
                content = tag.find("td", class_="resulttablecontent")
                title_tag = content.find("div", class_="resulttitle")
                if title_tag:
                    for br in title_tag.find_all("br"):
                        br.replace_with("\n")
                    title = title_tag.get_text().strip().splitlines()[0]
                else:
                    result_content = tag.find("div", class_="resultcontent")
                    for br in result_content.find_all("br"):
                        br.replace_with("\n")
                    title = result_content.get_text().strip().splitlines()[0]
                similarity = content.find("div", class_="resultsimilarityinfo").text
                content_url = content.find("a", class_="linkify")
                if not content_url:
                    content_url = content.find("div", class_="resultmiscinfo").find("a")
                if content_url:
                    r = {"title": title, "similarity": similarity, "url": content_url["href"]}
                else:
                    r = {"title": title, "similarity": similarity, "url": ""}
                if "hidden" in tag["class"]:
                    hidden_result.append(r)
                else:
                    result.append(r)
            if result:
                embed = discord.Embed(
                    title="Sauce found?",
                    description="\n".join((f"[{r['title']} ({r['similarity']})]({r['url']})" for r in result))
                )
                embed.set_footer(text="Powered by https://saucenao.com")
                await ctx.send(embed=embed)
            else:
                msg = await ctx.send("No result found.")
                if hidden_result:
                    sentences = {"initial":  "Do you want to show low similarity results?"}
                    result = await ctx.yes_no_prompt(sentences, delete_mode=True)
                    if result:
                        await msg.delete()
                        embed = discord.Embed(
                            title="Low similarity results:",
                            description="\n".join((f"[{r['title']} ({r['similarity']})]({r['url']})" for r in hidden_result))
                        )
                        embed.set_footer(text="Powered by https://saucenao.com")
                        await ctx.send(embed=embed)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(RImage(bot))
