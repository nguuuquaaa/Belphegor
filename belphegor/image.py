import discord
from discord.ext import commands
from . import utils
from .utils import checks, request, modding
import aiohttp
import json
import xmltodict
import random
from bs4 import BeautifulSoup as BS
import traceback
import asyncio
from yarl import URL

#==================================================================================================================================================

class NSFW(Exception):
    def __str__(self):
        return "This query is usable NSFW commands only."

#==================================================================================================================================================

RATING = {
    "s": "safe",
    "q": "questionable",
    "e": "explicit"
}

#==================================================================================================================================================

class RandomImage(commands.Cog):
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
                except IndexError:
                    return await ctx.send("No result found.")
                except NSFW:
                    return await ctx.send("This query is usable with NSFW commands only.")
                except KeyError:
                    retries -= 1
                except (json.JSONDecodeError, aiohttp.ClientConnectorError):
                    return await ctx.send(
                        "Oops, this query returned an error.\n"
                        "Probably network hiccup or something. Or maybe the site went down temporary, idk.\n"
                        "Just try again later."
                    )
            await ctx.send("Query failed. Please try again.")
        return new_func

    @modding.help(category="Image", field="Commands", paragraph=0)
    @commands.group(aliases=["random"])
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def r(self, ctx):
        '''
            `>>random`
            Base command. Does nothing by itself but with subcommands can be used to get a random image from various image boards.
        '''
        if ctx.invoked_subcommand is None:
            pass

    def process_tags(self, tags, *, safe, safe_tag="safe"):
        tag_list = list(tags)
        i = 0
        base_rating = frozenset(("s", "q", "e"))
        rating = frozenset()
        rtag = ""
        while i < len(tag_list):
            if tag_list[i].startswith(("rating:", "-rating:")):
                tag = tag_list.pop(i)
                if tag.startswith("rating:"):
                    r = tag[7:8]
                    if r in base_rating:
                        rating = frozenset((r,))
                        rtag = tag
                elif tag.startswith("-rating:"):
                    r = tag[8:9]
                    if r in base_rating:
                        rating = base_rating - frozenset((r,))
                        rtag = tag
            else:
                i += 1

        if safe:
            if "q" in rating or "e" in rating:
                raise NSFW
            else:
                rtag = f"rating:{safe_tag}"
        else:
            if len(rating) == 0:
                rtag = f"-rating:{safe_tag}"

        return rtag, ' '.join(tag_list)

    @retry_wrap
    async def get_image_danbooru(self, tags, *, safe):
        rating, tags = self.process_tags(tags, safe=safe)
        params = {
            "tags":   f"{rating} {tags}",
            "limit":  1,
            "random": "true"
        }
        bytes_ = await self.bot.fetch("https://danbooru.donmai.us/posts.json", params=params)
        pic = json.loads(bytes_)[0]
        tag_str = utils.split_page(pic.get('tag_string', ''), 1800)
        embed = discord.Embed(
            title="Danbooru",
            description=f"**Tags:** {tag_str[0]}\n\n**Rating:** {RATING.get(pic.get('rating'), 'N/A')}",
            url=f"https://danbooru.donmai.us/posts/{pic['id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=pic["file_url"] if pic["file_url"].startswith("http") else f"https://danbooru.donmai.us{pic['file_url']}")
        return embed

    @retry_wrap
    async def get_image_konachan(self, tags, *, safe, page=1):
        rating, tags = self.process_tags(tags, safe=safe)
        params = {
            "tags":   f"{rating} order:random {tags}",
            "limit":  1,
            "page":   page
        }
        domain = "net" if safe else "com"
        bytes_ = await self.bot.fetch(f"http://konachan.{domain}/post.json", params=params)
        pic = json.loads(bytes_)[0]
        tag_str = utils.split_page(pic.get('tags', ''), 1800)
        embed = discord.Embed(
            title="Konachan",
            description=f"**Tags:** {tag_str[0]}\n\n**Rating:** {RATING.get(pic.get('rating'), 'N/A')}",
            url=f"http://konachan.{domain}/post/show/{pic['id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=pic["file_url"] if pic["file_url"].startswith("http") else f"https:{pic['file_url']}")
        return embed

    @retry_wrap
    async def get_image_safebooru(self, tags, *, safe, page=1):
        rating, tags = self.process_tags(tags, safe=safe)
        params = {
            "page":   "dapi",
            "s":      "post",
            "q":      "index",
            "tags":   f"{rating} {tags}",
            "limit":  100,
            "pid":   page
        }
        bytes_ = await self.bot.fetch("https://safebooru.org/index.php", params=params)
        data = xmltodict.parse(bytes_.decode("utf-8"))
        pic = random.choice(data['posts']['post'])
        tag_str = utils.split_page(pic.get('@tags', '').strip(), 1800)
        embed = discord.Embed(
            title="Safebooru",
            description=f"**Tags:** {tag_str[0]}\n\n**Rating:** {RATING.get(pic.get('@rating'), 'N/A')}",
            url=f"https://safebooru.org/index.php?page=post&s=view&id={pic['@id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=pic["@file_url"] if pic["@file_url"].startswith("http") else f"https:{pic['@file_url']}")
        return embed

    @retry_wrap
    async def get_image_yandere(self, tags, *, safe, page=1):
        rating, tags = self.process_tags(tags, safe=safe, safe_tag="s")
        params = {
            "tags":   f"{rating} {tags}",
            "limit":  100,
            "page":   page
        }
        bytes_ = await self.bot.fetch("https://yande.re/post.json", params=params)
        pics = json.loads(bytes_)
        pic = random.choice(pics)
        tag_str = utils.split_page(pic.get('tags', ''), 1800)
        embed = discord.Embed(
            title="Yandere",
            description=f"**Tags:** {tag_str[0]}\n\n**Rating:** {RATING.get(pic.get('rating'), 'N/A')}",
            url=f"https://yande.re/post/show/{pic['id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=pic['file_url'])
        return embed

    @retry_wrap
    async def get_image_sancom(self, tags):
        rating, tags = self.process_tags(tags, safe=False, safe_tag="s")
        params = {
            "tags":   f"{rating} order:random {tags}",
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
        pic_tags = " ".join([t.find("a").text.strip().replace(" ", "_") for t in relevant.find_all(True, recursive=False)])
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

    @modding.help(brief="[Danbooru](https://danbooru.donmai.us/)", category="Image", field="Commands", paragraph=0)
    @r.command(aliases=["d",])
    async def danbooru(self, ctx, *tags):
        '''
            `>>random danbooru <optional: tag>`
            Get a random safe-rating image from danbooru.
        '''
        await self.get_image_danbooru(ctx, tags, safe=True)

    @modding.help(brief="[NSFW Danbooru](https://danbooru.donmai.us)", category="Image", field="Commands", paragraph=1)
    @r.command(aliases=["dh"])
    @checks.nsfw()
    async def danbooru_h(self, ctx, *tags):
        '''
            `>>random danbooru_h <optional: tag>`
            Get a random questionable/explicit-rating image from danbooru.
            Only usable in nsfw channel.
        '''
        await self.get_image_danbooru(ctx, tags, safe=False)

    @modding.help(brief="[Konachan](http://konachan.net)", category="Image", field="Commands", paragraph=0)
    @r.command(aliases=["k",])
    async def konachan(self, ctx, *tags):
        '''
            `>>random konachan <optional: tag>`
            Get a random safe-rating image from konachan.
        '''
        await self.get_image_konachan(ctx, tags, safe=True)

    @modding.help(brief="[NSFW Konachan](http://konachan.com)", category="Image", field="Commands", paragraph=1)
    @r.command(aliases=["kh",])
    @checks.nsfw()
    async def konachan_h(self, ctx, *tags):
        '''
            `>>random konachan_h <optional: tag>`
            Get a random questionable/explicit-rating image from konachan.
            Only usable in nsfw channel.
        '''
        await self.get_image_konachan(ctx, tags, safe=False)

    @modding.help(brief="[Safebooru](https://safebooru.org)", category="Image", field="Commands", paragraph=0)
    @r.command(aliases=["s",])
    async def safebooru(self, ctx, *tags):
        '''
            `>>random safebooru <optional: list of tags>`
            Get a random safe-rating image from safebooru.
        '''
        await self.get_image_safebooru(ctx, tags, safe=True)

    @modding.help(brief="[Yandere](https://yande.re)", category="Image", field="Commands", paragraph=0)
    @r.command(aliases=["y",])
    async def yandere(self, ctx, *tags):
        '''
            `>>random yandere <optional: list of tags>`
            Get a random questionable/explicit-rating image from yandere.
        '''
        await self.get_image_yandere(ctx, tags, safe=True)

    @modding.help(brief="[NSFW Sankaku Complex](https://chan.sankakucomplex.com)", category="Image", field="Commands", paragraph=1)
    @r.command(aliases=["sc",])
    @checks.nsfw()
    async def sancom(self, ctx, *tags):
        '''
            `>>random sancom <optional: 1 or 2 tags>`
            Get a random questionable/explicit-rating image from Sankaku Complex.
            Only usable in nsfw channel.
        '''
        async with self.sc_lock:
            async with ctx.typing():
                await self.get_image_sancom(ctx, tags)

    @r.command(hidden=True, name="retry")
    @checks.owner_only()
    async def setretry(self, ctx, number:int):
        if number <= 0:
            await ctx.send("Number must be positive.")
        elif number > 10:
            await ctx.send("Sorry, can't retry that many times.")
        else:
            self.retry = number
            await ctx.send(f"Number of retries has been set to {number}.")

    @modding.help(brief="Get sauce", category="Image", field="Commands", paragraph=2)
    @commands.command()
    async def saucenao(self, ctx, url: modding.URLConverter()=None):
        '''
            `>>saucenao <optional: either uploaded image or url>`
            Find the sauce of the image.
            If no argument is provided, wait 2 minutes for uploaded image.
        '''
        if not url:
            if not ctx.message.attachments:
                msg = await ctx.send("You want sauce of what? Post the dang url or upload the dang pic here.")
                try:
                    message = await self.bot.wait_for("message", check=lambda m: m.author.id==ctx.author.id and (m.attachments or m.content), timeout=120)
                except asyncio.TimeoutError:
                    return await msg.edit(content="That's it, I'm not waiting anymore.")
            else:
                message = ctx.message
            if message.attachments:
                url = URL(message.attachments[0].url)
            else:
                url = await modding.URLConverter().convert(ctx, message.content)

        await ctx.trigger_typing()
        payload = aiohttp.FormData()
        payload.add_field("file", b"", filename="", content_type="application/octet-stream")
        payload.add_field("url", str(url))
        payload.add_field("frame", "1")
        payload.add_field("hide", "0")
        payload.add_field("database", "999")
        async with self.bot.session.post("https://saucenao.com/search.php", headers={"User-Agent": request.USER_AGENT}, data=payload) as response:
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
                try:
                    title = title_tag.get_text().strip().splitlines()[0]
                except IndexError:
                    title = "no title"
            else:
                result_content = tag.find("div", class_="resultcontent")
                for br in result_content.find_all("br"):
                    br.replace_with("\n")
                title = utils.get_element(result_content.get_text().strip().splitlines(), 0, default="No title")
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
    bot.add_cog(RandomImage(bot))
