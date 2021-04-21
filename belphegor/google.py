import discord
from discord.ext import commands
from . import utils
from .utils import modding, request, checks
from bs4 import BeautifulSoup as BS
import aiohttp
import asyncio
from yarl import URL

#==================================================================================================================================================

SUPERSCRIPT = {
    "0": "0x2070",
    "1": "0x00b9",
    "2": "0x00b2",
    "3": "0x00b3",
    "4": "0x2074",
    "5": "0x2075",
    "6": "0x2076",
    "7": "0x2077",
    "8": "0x2078",
    "9": "0x2079"
}

ALL_LANGUAGES = {
    "af": "Afrikaans", "sq": "Albanian", "am": "Amharic", "ar": "Arabic", 
    "hy": "Armenian", "az": "Azerbaijani", "eu": "Basque", "be": "Belarusian", 
    "bn": "Bengali", "bs": "Bosnian", "bg": "Bulgarian", "ca": "Catalan", 
    "ceb": "Cebuano", "ny": "Chichewa", "zh-CN": "Chinese (Simplified)", 
    "co": "Corsican", "hr": "Croatian", "cs": "Czech", "da": "Danish", 
    "nl": "Dutch", "en": "English", "eo": "Esperanto", "et": "Estonian", 
    "tl": "Filipino", "fi": "Finnish", "fr": "French", "fy": "Frisian", 
    "gl": "Galician", "ka": "Georgian", "de": "German", "el": "Greek", 
    "gu": "Gujarati", "ht": "Haitian Creole", "ha": "Hausa", "haw": "Hawaiian", 
    "iw": "Hebrew", "hi": "Hindi", "hmn": "Hmong", "hu": "Hungarian", 
    "is": "Icelandic", "ig": "Igbo", "id": "Indonesian", "ga": "Irish",
    "it": "Italian", "ja": "Japanese", "jw": "Javanese", "kn": "Kannada", 
    "kk": "Kazakh", "km": "Khmer", "rw": "Kinyarwanda", "ko": "Korean", 
    "ku": "Kurdish (Kurmanji)", "ky": "Kyrgyz", "lo": "Lao", "la": "Latin", 
    "lv": "Latvian", "lt": "Lithuanian", "lb": "Luxembourgish", "mk": "Macedonian", 
    "mg": "Malagasy", "ms": "Malay", "ml": "Malayalam", "mt": "Maltese", 
    "mi": "Maori", "mr": "Marathi", "mn": "Mongolian", "my": "Myanmar (Burmese)", 
    "ne": "Nepali", "no": "Norwegian", "or": "Odia (Oriya)", "ps": "Pashto", 
    "fa": "Persian", "pl": "Polish", "pt": "Portuguese", "pa": "Punjabi", 
    "ro": "Romanian", "ru": "Russian", "sm": "Samoan", "gd": "Scots Gaelic", 
    "sr": "Serbian", "st": "Sesotho", "sn": "Shona", "sd": "Sindhi", 
    "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian", "so": "Somali", 
    "es": "Spanish", "su": "Sundanese", "sw": "Swahili", "sv": "Swedish", 
    "tg": "Tajik", "ta": "Tamil", "tt": "Tatar", "te": "Telugu", 
    "th": "Thai", "tr": "Turkish", "tk": "Turkmen", "uk": "Ukrainian", 
    "ur": "Urdu", "ug": "Uyghur", "uz": "Uzbek", "vi": "Vietnamese", 
    "cy": "Welsh", "xh": "Xhosa", "yi": "Yiddish", "yo": "Yoruba", 
    "zu": "Zulu", "zh-TW": "Chinese (Traditional)"
}

SORTED_LANGUAGES = sorted(ALL_LANGUAGES.items(), key=lambda x: x[1])

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
            "User-Agent": request.USER_AGENT
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
            other = "\n".join([f"\u2022 <{t[1]}>" for t in search_results[:4]])
            return f"**Search result:**\n\u2022 {tag.find('a')['href']}\n**See also:**\n{other}"

        g_container = soup.find(lambda x: x.name=="div" and "obcontainer" in x.get("class", []))
        if g_container:
            #unit convert
            try:
                results = g_container.find_all(True, recursive=False)
                embed = discord.Embed(title="Search result:", description=f"**Unit convert - {results[0].find('option', selected=1).text}**", colour=discord.Colour.dark_orange())
                embed.add_field(name=results[1].find("option", selected=1).text, value=results[1].find("input")["value"])
                embed.add_field(name=results[3].find("option", selected=1).text, value=results[3].find("input")["value"])
                if search_results:
                    embed.add_field(name="See also:", value="\n".join((f"\u2022 [{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[:4])), inline=False)
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
                        embed.add_field(name="See also:", value="\n".join((f"\u2022 [{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[:4])), inline=False)
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
                        embed.add_field(name="See also:", value="\n".join((f"\u2022 [{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[:4])), inline=False)
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
                        embed.add_field(name="See also:", value="\n".join((f"\u2022 [{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[:4])), inline=False)
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
                embed.add_field(name="See also:", value="\n".join((f"\u2022 [{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[:4])), inline=True)
                return embed
            except:
                pass

        #definition
        tags = soup.find_all("div", class_="lr_dct_ent")
        if tags:
            try:
                defines = []
                for tag in tags:
                    top_box = tag.find("div", class_="Jc6jBf")
                    gsrt = top_box.find("div", class_="gsrt")
                    name = gsrt.find("span").text
                    pronounce = top_box.find("div", class_="lr_dct_ent_ph").text
                    for relevant in tag.find("div", class_="vmod").find_all("div", class_="vmod", recursive=False):
                        form_tag = relevant.find("div", class_="vk_gy")
                        form = []
                        for ft in form_tag.find_all("span", recursive=False):
                            for child in ft.children:
                                if child.name == "b":
                                    text = f"*{child.text}*"
                                elif child.name is None:
                                    text = child
                                else:
                                    text = child.text
                                if text:
                                    form.append(text)

                        page = [f"**{name}**", pronounce, "\n", "".join(form)]
                        definition_box = relevant.find("ol", class_="lr_dct_sf_sens")
                        for each in definition_box.find_all("li", recursive=False):
                            deeper = each.find("div", class_="lr_dct_sf_sen")
                            number = deeper.find("div", style="float:left")
                            list_of_definitions = "\n".join(f"- {t.text}" for t in deeper.find_all("div", attrs={"data-dobid": "dfn"}))
                            page.append(f"**{number.text}**\n{list_of_definitions}")

                        defines.append("\n".join(page))

                see_also = "\n\n".join((f"[{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[1:5]))
                embeds = []
                max_page = len(defines)
                for i, d in enumerate(defines):
                    embed = discord.Embed(title="Search result:", description=f"{defines[i]}\n\n(Page {i+1}/{max_page})", colour=discord.Colour.dark_orange())
                    embed.add_field(name="See also:", value=see_also, inline=False)
                    embeds.append(embed)
                return embeds
            except:
                import traceback
                traceback.print_exc()

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
                embed.add_field(name="See also:", value="\n".join((f"\u2022 [{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[1:5])), inline=False)
                return embed
            except:
                pass

        #simple wiki
        tag = soup.find(lambda x: x.name=="div" and x.get("class")==["mod"] and x.get("style")=="clear:none")
        if tag:
            try:
                embed = discord.Embed(title="Search result:", description=f"{tag.text}\n[{search_results[0].h3.text}]({search_results[0]['href']})", colour=discord.Colour.dark_orange())
                embed.add_field(name="See also:", value="\n".join((f"\u2022 [{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[1:5])), inline=False)
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
                embed.add_field(name="See also:", value="\n".join((f"\u2022 [{utils.discord_escape(t[0])}]({utils.safe_url(t[1])})" for t in search_results[0:4])), inline=False)
                return embed
            except:
                pass

        #non-special search
        if not search_results:
            return None

        other = "\n".join((f"\u2022 <{r[1]}>" for r in search_results[1:5]))
        return f"**Search result:**\n\u2022 {search_results[0][1]}\n**See also:**\n{other}"

    @modding.help(brief="Google search", category="Misc", field="Commands", paragraph=2)
    @commands.command(aliases=["g"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def google(self, ctx, *, query):
        '''
            `>>google <query>`
            Google search.
        '''
        params = {
            "hl": "en",
            "q": query
        }

        await ctx.trigger_typing()
        async with self.google_lock:
            bytes_ = await utils.fetch(
                self.google_session,
                "https://www.google.com/search",
                headers=self.google_headers,
                params=params,
                timeout=10
            )
            result = self._parse_google(bytes_.decode("utf-8"))
            if isinstance(result, discord.Embed):
                await ctx.send(embed=result)
            elif isinstance(result, str):
                await ctx.send(result)
            elif isinstance(result, list):
                paging = utils.Paginator(result, render=False)
                await paging.navigate(ctx)
            else:
                await ctx.send("No result found.\n... Either that or Google blocked me (in that case REEEEEEEEEEEEEEEEEEEEEEEEEE)")

    @google.error
    async def google_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Whoa slow down your Google search! You can only search once every 10 seconds.")

    @modding.help(brief="Google, but translate", category="Misc", field="Commands", paragraph=2)
    @commands.group(aliases=["translate", "trans"], invoke_without_command=True)
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def gtrans(self, ctx, *, query: modding.KeyValue({"from": str, "to": str})):
        '''
            `>>gtrans <text> <keyword: from> <keyword: to>`
            Google translate text.
            Default keyword from (input language code) is auto (detect language).
            Default keyword to (output language code) is en (English).
            You can use `>>gtrans langs` for a list of supported languages.
        '''
        await ctx.trigger_typing()
        tl_from = query.getone("from", "auto")
        tl_to = query.getone("to", "en")
        text = query.getalltext("")
        if (tl_from == "auto" or tl_from in ALL_LANGUAGES) and tl_to in ALL_LANGUAGES:
            pass
        else:
            return await ctx.send("Unrecognized language.")
        params = {
            "tl": tl_to,
            "hl": "en",
            "sl": tl_from,
            "ie": "UTF-8",
            "q": text
        }
        if not ctx.channel.is_nsfw():
            params["safe"] = "active"
        bytes_ = await utils.fetch(
            self.google_session,
            "http://translate.google.com/m",
            headers=self.google_headers,
            params=params,
            timeout=10
        )

        data = BS(bytes_.decode("utf-8"), "lxml")
        tag = data.find("div", class_="result-container")
        result = tag.get_text()
        if len(result) > 1000:
            result = f"{result[:1000]}..."
        embed = discord.Embed(
            title="Result",
            colour=discord.Colour.dark_orange(),
            url=str(URL.build(
                scheme="https",
                host="translate.google.com",
                query={
                    "sl": tl_from,
                    "tl": tl_to,
                    "op": "translate",
                    "text": text
                }
            ))
        )
        embed.add_field(name=ALL_LANGUAGES.get(tl_from, "Detect language"), value=text, inline=False)
        embed.add_field(name=ALL_LANGUAGES[tl_to], value=result, inline=False)
        await ctx.send(embed=embed)

    @modding.help(brief="Supported languages", category="Misc", field="Commands", paragraph=2)
    @gtrans.group(name="languages", aliases=["langs"])
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def gtrans_langauges(self, ctx):
        '''
            `>>gtrans languages`
            Show supported languages for using with from/to keywords in gtrans command.
        '''
        paging = utils.Paginator(
            SORTED_LANGUAGES, 10,
            title="All languages",
            description=lambda i, x: f"`{x[0]}` - {x[1]}"
        )
        await paging.navigate(ctx)

    @gtrans.error
    async def gtrans_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Whoa slow down your Google translate! You can only do it once every 10 seconds.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Google(bot))
