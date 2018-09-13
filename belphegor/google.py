import discord
from discord.ext import commands
from . import utils
from .utils import token
import multiprocessing
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import os
import sys
from bs4 import BeautifulSoup as BS
import asyncio
import weakref
import traceback
import functools
import queue
import time
import signal
from yarl import URL

#==================================================================================================================================================

def try_coro(func):
    @functools.wraps(func)
    async def new_func(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except:
            traceback.print_exc()
    return new_func

def try_sync(func):
    @functools.wraps(func)
    def new_func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            traceback.print_exc()
    return new_func

search_queue = multiprocessing.Queue()
result_queue = multiprocessing.Queue()

#==================================================================================================================================================

BASE_URL = "https://www.google.com"

class GoogleEngine:
    def __init__(self, driver):
        self.driver = driver

    @classmethod
    def setup_browser(cls, *, user_agent=None, proxy_host=None, proxy_port=None, email=None, password=None, safe=False):
        options = Options()
        options.add_argument("--headless")
        if user_agent:
            options.add_argument("--user-agent"+user_agent)
        options.add_argument("--incognito")
        options.add_argument("--window-size=1920,1080")

        if sys.platform == "win32":
            options.add_argument("--disable-gpu")
        else:
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")

        if proxy_host and proxy_port:
            options.add_argument(f"--proxy-server={proxy_host}:{proxy_port}")

        cwd = os.getcwd()
        try:
            driver = webdriver.Chrome(f"{cwd}/chromedriver", options=options)
            driver.get(BASE_URL)

            #login
            elem = driver.find_element_by_css_selector("a#gb_70")
            elem.click()

            #email
            email = email or token.G_EMAIL
            elem = driver.find_element_by_css_selector("input[type=email]")
            elem.clear()
            elem.send_keys(email)
            elem.send_keys(Keys.RETURN)

            #password
            password = password or token.G_PASSWORD
            elem = driver.find_element_by_css_selector("input[type=password]")
            elem.clear()
            elem.send_keys(password)
            elem.send_keys(Keys.RETURN)

            #in case we get "you need to update these shit"
            driver.get(BASE_URL)

            #switch to English
            try:
                elem = driver.find_element_by_css_selector("#gws-output-pages-elements-homepage_additional_languages__als > div > a:nth-child(1)")
            except:
                pass
            else:
                if elem.text.strip() == "English":
                    elem.click()

            #if safe search is on
            if safe:
                #first do a random search
                elem = driver.find_element_by_css_selector("input[name=q]")
                elem.clear()
                elem.send_keys("google")
                elem.send_keys(Keys.RETURN)

                #then open search preference
                elem = driver.find_element_by_css_selector("#abar_button_opt")
                elem.click()

                elem = driver.find_element_by_css_selector("#lb > div > a:nth-child(1)")
                elem.click()

                #switch safe search on
                #sometimes this doesn't load immediately, so wait a bit_length
                time.sleep(1)
                elem = driver.find_element_by_css_selector("#ssc > span > div")
                elem.click()

                #and save
                elem = driver.find_element_by_css_selector("#form-buttons > div.jfk-button-action")
                elem.click()

                #there's a popup here so dismiss it
                alert = driver.switch_to.alert
                alert.dismiss()
        except:
            print("error, written source to g.html")
            with open("g.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.get(BASE_URL)

        return cls(driver)

    def search(self, query):
        elem = self.driver.find_element_by_css_selector("input[name=q]")
        elem.clear()
        elem.send_keys(query)
        elem.send_keys(Keys.RETURN)
        soup = BS(self.driver.page_source, "lxml")
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
                    img_url = raw_img_url.query.get("imgurl")
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
        return f"**Search result:**\n{search_results[0][0]}\n**See also:**\n{other}"

    def close(self):
        self.driver.close()

#==================================================================================================================================================

class Google:
    def __init__(self, bot):
        self.bot = bot

        self.google_result = weakref.ref(bot.loop.create_task(self.google_result_queue()))
        self.orders = {}

    def __unload(self):
        gs = self.google_result()
        if gs:
            gs.cancel()

    @try_coro
    async def google_result_queue(self):
        loop = self.bot.loop
        while True:
            try:
                ret = await loop.run_in_executor(None, result_queue.get, True, 5)
            except queue.Empty:
                continue

            if ret[1]:
                self.orders[ret[0]].set_result(ret[2])
            else:
                self.orders[ret[0]].set_exception(ret[2])

    @commands.command(aliases=["g"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def google(self, ctx, *, query):
        '''
            `>>google <query>`
            Google search.
            Safe search is enabled in non-nsfw channels and disabled in nsfw channels.
            There's a 10-second cooldown per user.
        '''
        await ctx.trigger_typing()

        if ctx.channel.is_nsfw():
            safe = True
        else:
            safe = False

        fut = self.bot.loop.create_future()
        mid = ctx.message.id
        self.orders[mid] = fut

        st = time.perf_counter()
        search_queue.put((mid, safe, query))
        ed = time.perf_counter()

        result = await fut
        if isinstance(result, discord.Embed):
            await ctx.send(embed=result)
        elif isinstance(result, str):
            await ctx.send(result)
        elif not result:
            await ctx.send("No result found.\nEither query yields nothing or Google blocked me (REEEEEEEEEEEEEEEEEEEEEEEE)")
        elif isinstance(result, list):
            paging = utils.Paginator(result, render=False)
            await paging.navigate(ctx)
        else:
            raise result

    @google.error
    async def google_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Whoa slow down your Google search! You can only search once every 10 seconds.")

    @commands.command(aliases=["translate", "trans"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def gtrans(self, ctx, *, search):
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
            "q": quote(search)
        }
        bytes_ = await self.bot.fetch("http://translate.google.com/m", params=params)

        data = BS(bytes_.decode("utf-8"), "lxml")
        tag = data.find("div", class_="t0")
        embed = discord.Embed(colour=discord.Colour.dark_orange())
        embed.add_field(name="Detect", value=search)
        embed.add_field(name="English", value=tag.get_text())
        await ctx.send(embed=embed)

    @gtrans.error
    async def gtrans_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Whoa slow down your Google translate! You can only do it once every 10 seconds.")

#==================================================================================================================================================

class RunGoogleInBackground(multiprocessing.Process):
    @try_sync
    def run(self):
        drivers = (GoogleEngine.setup_browser(safe=False), GoogleEngine.setup_browser(safe=True))
        signal.signal(signal.SIGTERM, lambda signum, frame: drivers[0].close() and drivers[1].close())
        print("google ready")
        while self.running:
            try:
                item = search_queue.get(True, 5)
            except queue.Empty:
                continue
            mid = item[0]
            driver = drivers[item[1]]
            query = item[2]
            try:
                ret = driver.search(query)
                no_error = True
            except Exception as e:
                ret = e
                no_error = False
            finally:
                result_queue.put((mid, no_error, ret))
        drivers[0].close()
        drivers[1].close()

def setup(bot):
    process = RunGoogleInBackground()
    process.running = True
    process.start()
    bot.add_cog(Google(bot))
    bot.saved_stuff["google"] = process

def teardown(bot):
    process = bot.saved_stuff.pop("google")
    process.running = False
