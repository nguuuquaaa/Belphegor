import discord
from discord.ext import commands
from . import utils
from .utils import modding, config, checks
from bs4 import BeautifulSoup as BS
import aiohttp
import asyncio

#==================================================================================================================================================

class Google(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.google_session = aiohttp.ClientSession()
        self.google_lock = asyncio.Lock()
        self.google_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, sdch",
            "Connection": "keep-alive",
            "User-Agent": config.USER_AGENT
        }

    def cog_unload(self):
        self.bot.create_task_and_count(self.google_session.close())

    def _parse_google(self, html):
        soup = BS(html, "lxml")
        for script in soup("script"):
            script.decompose()

        search_results = []
        all_tags = soup.find_all(lambda x: x.name=="div" and x.get("class")==["g"] and len(x.attrs)==1)
        for tag in all_tags:
            a = tag.find("a")
            h3 = a.find("h3")
            if h3:
                title = h3.text
            else:
                title = a.text
            search_results.append((title, a["href"]))
            if len(search_results) > 4:
                break

        #video
        tag = soup.find("div", class_="FGpTBd")
        if tag:
            other = "\n\n".join([f"<{t[1]}>" for t in search_results[:4]])
            return f"**Search result:**\n{tag.find('a')['href']}\n\n**See also:**\n{other}"

        g_container = soup.find(lambda x: x.name=="div" and "obcontainer" in x.get("class", []))
        if g_container:
            #unit convert
            try:
                results = g_container.find_all(True, recursive=False)
                embed = discord.Embed(title="Search result:", description=f"**Unit convert - {results[0].find('option', selected=1).text}**", colour=discord.Colour.dark_orange())
                embed.add_field(name=results[1].find("option", selected=1).text, value=results[1].find("input")["value"])
                embed.add_field(name=results[3].find("option", selected=1).text, value=results[3].find("input")["value"])
                if search_results:
                    embed.add_field(name="See also:", value="\n\n".join((f"[{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[:4])), inline=False)
                return embed
            except:
                pass

            #timezone convert
            zone_data = g_container.find("div", class_="sL6Rbf")
            if zone_data:
                try:
                    text = []
                    for stuff in zone_data.find_all(True, recursive=False):
                        table = stuff.find("table")
                        if table:
                            for tr in table.find_all(True, recursive=False):
                                text.append(tr.get_text())
                        else:
                            text.append(stuff.get_text().strip())
                    outtxt = "\n".join(text)
                    embed = discord.Embed(
                        title="Search result:",
                        description=f"**Timezone**\n{outtxt}",
                        colour=discord.Colour.dark_orange()
                    )
                    if search_results:
                        embed.add_field(name="See also:", value="\n\n".join((f"[{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[:4])), inline=False)
                    return embed
                except:
                    pass

            #currency convert
            input_value = g_container.find("input", id="knowledge-currency__src-input")
            input_type = g_container.find("select", id="knowledge-currency__src-selector")
            output_value = g_container.find("input", id="knowledge-currency__tgt-input")
            output_type = g_container.find("select", id="knowledge-currency__tgt-selector")
            if all((input_value, input_type, output_value, output_type)):
                try:
                    embed = discord.Embed(title="Search result:", description="**Currency**", colour=discord.Colour.dark_orange())
                    embed.add_field(name=input_type.find("option", selected=1).text, value=input_value["value"])
                    embed.add_field(name=output_type.find("option", selected=1).text, value=output_value["value"])
                    if search_results:
                        embed.add_field(name="See also:", value="\n\n".join((f"[{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[:4])), inline=False)
                    return embed
                except:
                    pass

            #calculator
            inp = soup.find("span", class_="cwclet")
            out = soup.find("span", class_="cwcot")
            if inp or out:
                try:
                    embed = discord.Embed(title="Search result:", description=f"**Calculator**\n{inp.text}\n\n {out.text}", colour=discord.Colour.dark_orange())
                    if search_results:
                        embed.add_field(name="See also:", value="\n\n".join((f"[{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[:4])), inline=False)
                    return embed
                except:
                    pass

        #wiki
        tag = soup.find("div", class_="knowledge-panel")
        if tag:
            try:
                title = tag.find("div", class_="kno-ecr-pt").span.text
                desc = tag.find("div", class_="kno-rdesc")
                img_box = tag.find("div", class_="kno-ibrg")
                if desc:
                    url_tag = desc.find("a")
                    if url_tag:
                        url = f"\n[{url_tag.text}]({utils.safe_url(url_tag['href'])})"
                    else:
                        url = ""
                    description = f"**{title}**\n{desc.find('span').text.replace('MORE', '').replace('…', '')}{url}"
                else:
                    description = f"**{title}**"
                embed = discord.Embed(title="Search result:", description=description, colour=discord.Colour.dark_orange())
                try:
                    raw_img_url = URL(img_box.find("a")["href"])
                    img_url = raw_img_url.query.get("imgurl", "")
                    if img_url.startswith(("http://", "https://")):
                        embed.set_thumbnail(url=img_url)
                except:
                    pass
                embed.add_field(name="See also:", value="\n\n".join((f"[{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[:4])), inline=True)
                return embed
            except:
                pass

        #definition
        tag = soup.find("div", class_="lr_container")
        if tag:
            try:
                relevant_data = tag.find_all(
                    lambda t:
                        (
                            t.name=="div"
                            and (
                                t.get("data-dobid")=="dfn"
                                or t.get("class") in (["lr_dct_sf_h"], ["xpdxpnd", "vk_gy"], ["vmod", "vk_gy"])
                                or t.get("style")=="float:left"
                            )
                        )
                        or
                        (
                            t.name=="span"
                            and (
                                t.get("data-dobid")=="hdw"
                                or t.get("class")==["lr_dct_ph"]
                            )
                        )
                )
                word = ""
                pronoun = ""
                current_page = -1
                defines = []
                for t in relevant_data:
                    if t.name == "span":
                        if t.get("data-dobid") == "hdw":
                            word = t.text
                        else:
                            pronoun = t.text
                    else:
                        if t.get("class") == ["lr_dct_sf_h"]:
                            current_page += 1
                            defines.append(f"**{word}**\n/{pronoun}\n")
                        elif "vk_gy" in t.get("class", []):
                            form = ""
                            for child_t in t.find_all(True):
                                if child_t.name == "b":
                                    form = f"{form}*{child_t.find(text=True, recursive=False)}*"
                                else:
                                    form = f"{form}{child_t.find(text=True, recursive=False)}"
                            defines[current_page] = f"{defines[current_page]}\n{form}"
                        elif t.get("style") == "float:left":
                            defines[current_page] = f"{defines[current_page]}\n**{t.text}**"
                        else:
                            defines[current_page] = f"{defines[current_page]}\n- {t.text}"
                see_also = "\n\n".join((f"[{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[1:5]))
                embeds = []
                max_page = len(defines)
                for i, d in enumerate(defines):
                    embed = discord.Embed(title="Search result:", description=f"{defines[i]}\n\n(Page {i+1}/{max_page})", colour=discord.Colour.dark_orange())
                    embed.add_field(name="See also:", value=see_also, inline=False)
                    embeds.append(embed)
                return embeds
            except:
                pass

        #weather
        tag = soup.find("div", class_="card-section", id="wob_wc")
        if tag:
            try:
                more_link = tag.next_sibling.find("a")
                embed = discord.Embed(
                    title="Search result:",
                    description=f"**Weather**\n[{more_link.text}]({utils.safe_url(more_link['href'])})",
                    colour=discord.Colour.dark_orange()
                )
                embed.set_thumbnail(url=f"https:{tag.find('img', id='wob_tci')['src']}")
                embed.add_field(
                    name=tag.find("div", class_="vk_gy vk_h").text,
                    value=f"{tag.find('div', id='wob_dts').text}\n{tag.find('div', id='wob_dcp').text}",
                    inline=False
                )
                embed.add_field(name="Temperature", value=f"{tag.find('span', id='wob_tm').text}°C | {tag.find('span', id='wob_ttm').text}°F")
                embed.add_field(name="Precipitation", value=tag.find('span', id='wob_pp').text)
                embed.add_field(name="Humidity", value=tag.find('span', id='wob_hm').text)
                embed.add_field(name="Wind", value=tag.find('span', id='wob_ws').text)
                embed.add_field(name="See also:", value="\n\n".join((f"[{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[1:5])), inline=False)
                return embed
            except:
                pass

        #simple wiki
        tag = soup.find(lambda x: x.name=="div" and x.get("class")==["mod"] and x.get("style")=="clear:none")
        if tag:
            try:
                embed = discord.Embed(title="Search result:", description=f"{tag.text}\n[{search_results[0].h3.text}]({search_results[0]['href']})", colour=discord.Colour.dark_orange())
                embed.add_field(name="See also:", value="\n\n".join((f"[{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[1:5])), inline=False)
                return embed
            except:
                pass

        #translate
        tag = soup.find("div", id="tw-container")
        if tag:
            try:
                s = tag.find("div", id="tw-source")
                inp = s.find("textarea", id="tw-source-text-ta")
                inp_lang = s.find("div", class_="tw-lang-selector-wrapper").find("option", selected="1")
                t = tag.find("div", id="tw-target")
                out = t.find("pre", id="tw-target-text")
                out_lang = t.find("div", class_="tw-lang-selector-wrapper").find("option", selected="1")
                link = tag.next_sibling.find("a")
                embed = discord.Embed(title="Search result:", description=f"[Google Translate]({link['href']})", colour=discord.Colour.dark_orange())
                embed.add_field(name=inp_lang.text, value=inp.text)
                embed.add_field(name=out_lang.text, value=out.text)
                embed.add_field(name="See also:", value="\n\n".join((f"[{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[0:4])), inline=False)
                return embed
            except:
                pass

        #non-special search
        if not search_results:
            return None

        other = "\n\n".join((f"<{r[1]}>" for r in search_results[1:5]))
        return f"**Search result:**\n{search_results[0][1]}\n**See also:**\n{other}"

    @modding.help(brief="Google search", category="Misc", field="Commands", paragraph=2)
    @commands.command(aliases=["g"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def google(self, ctx, *, query):
        '''
            `>>google <query>`
            Google search.
            There's a 10-second cooldown per user.
        '''
        params = {
            "hl": "en",
            "q": query
        }

        await ctx.trigger_typing()
        async with self.google_lock:
            bytes_ = await utils.fetch(self.google_session, "https://www.google.com/search", headers=self.google_headers, params=params, timeout=10)
            result = self._parse_google(bytes_.decode("utf-8"))
            if isinstance(result, discord.Embed):
                await ctx.send(embed=result)
            elif isinstance(result, str):
                await ctx.send(result)
            elif isinstance(result, list):
                paging = utils.Paginator(result, render=False)
                await paging.navigate(ctx)
            else:
                await ctx.send("No result found.\nEither query yields nothing or Google blocked me (REEEEEEEEEEEEEEEEEEEEEEEE)")

    @google.error
    async def google_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Whoa slow down your Google search! You can only search once every 10 seconds.")

    @modding.help(brief="Google, but translate", category="Misc", field="Commands", paragraph=2)
    @commands.command(aliases=["translate", "trans"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def gtrans(self, ctx, *, query):
        '''
            `>>gtrans <text>`
            Google translate.
            Input is automatically detected, output is English.
            There's a 10-second cooldown per user.
        '''
        await ctx.trigger_typing()
        params = {
            "tl": "en",
            "hl": "en",
            "sl": "auto",
            "ie": "UTF-8",
            "q": query
        }
        if not ctx.channel.is_nsfw():
            params["safe"] = "active"
        bytes_ = await self.bot.fetch("http://translate.google.com/m", headers=self.google_headers, params=params, timeout=10)

        data = BS(bytes_.decode("utf-8"), "lxml")
        tag = data.find("div", class_="t0")
        embed = discord.Embed(colour=discord.Colour.dark_orange())
        embed.add_field(name="Detect", value=query)
        embed.add_field(name="English", value=tag.get_text())
        await ctx.send(embed=embed)

    @gtrans.error
    async def gtrans_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Whoa slow down your Google translate! You can only do it once every 10 seconds.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Google(bot))
