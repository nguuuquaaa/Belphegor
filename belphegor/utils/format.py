import discord
from unicodedata import normalize, category
import re
import asyncio
from datetime import datetime, timedelta
import pytz
from pytz import timezone
from urllib.parse import quote

_keep_char = (".", "_", " ")

def safe_filename(any_string):
    return ''.join((c for c in any_string if c.isalnum() or c in _keep_char))

_keep_special_char = ("\n", "\t")

def unifix(any_string):
    return "".join((c for c in normalize("NFKC", any_string) if category(c)[0]!="C" or c in _keep_special_char)).strip()

_split_regex = re.compile(r"(\s)")

def split_page(text, split_len, *, safe_mode=True):
    description = _split_regex.split(text)
    description_page = ["",]
    cur_index = 0
    for word in description:
        if word=="@everyone":
            word = "@\u200beveryone"
        elif word=="@here":
            word = "@\u200bhere"
        if safe_mode:
            if word[:7]=="http://" or word[:8]=="https://":
                word = safe_url(word)
            else:
                word = discord_escape(word)
        cur_node = description_page[cur_index]
        if len(cur_node) + len(word) < split_len:
            description_page[cur_index] = f"{cur_node}{word}"
        else:
            if len(word) < split_len:
                description_page[cur_index] = f"{cur_node}..."
                description_page.append(f"...{word}")
                cur_index += 1
            else:
                left = split_len - len(cur_node)
                description_page[cur_index] = f"{cur_node}{word[:left]}..."
                stuff = [f"...{word[i+left:i+split_len+left]}..." for i in range(0, len(word)-left, split_len)]
                stuff[-1] = stuff[-1][:-3]
                description_page.extend(stuff)
                cur_index += len(stuff)
    return description_page

def seconds_to_text(seconds):
    seconds = int(seconds)
    wt = [
        ("year", seconds//31536000),
        ("month", seconds%31536000//2592000),
        ("week", seconds%31536000%2592000//604800),
        ("day", seconds%31536000%2592000%604800//86400),
        ("hour", seconds%86400//3600),
        ("minute", seconds%3600//60),
        ("second", seconds%60)
    ]
    text_body = ""
    for item in wt:
        if item[1] > 1:
            text_body = f"{text_body} {item[1]} {item[0]}s"
        elif item[1] == 1:
            text_body = f"{text_body} {item[1]} {item[0]}"
    return text_body.strip()

time_regex = re.compile(
    r"(?:[\s\b]*)"
    r"(?:for|in|and|,|;|&)?(?:\s*)"
    r"(\d+\.?\d*)(?:\s*)"
    r"(w(?:(?:eek)?s?)?|d(?:(?:ay)s?)?|h(?:(?:(?:ou)?r)s?)?|m(?:(?:in)(?:ute)?s?)?|s(?:(?:ec)(?:ond)?s?)?)"
    r"(?:[\s\b]*)",
    flags=re.I
)

def extract_time(text):
    extract = time_regex.findall(text)
    new_text = time_regex.sub("", text)
    result = {"weeks": 0, "days": 0, "hours": 0, "minutes": 0, "seconds": 0}
    if extract:
        for wt in extract:
            fc = wt[1][:1].lower()
            if fc == "w":
                result["weeks"] += float(wt[0])
            elif fc == "d":
                result["days"] += float(wt[0])
            elif fc == "h":
                result["hours"] += float(wt[0])
            elif fc == "m":
                result["minutes"] += float(wt[0])
            elif fc == "s":
                result["seconds"] += float(wt[0])
    return new_text, timedelta(**result)

def now_time(tzinfo=pytz.utc):
    return datetime.now(tzinfo)

def format_time(dt_obj):
    return dt_obj.strftime("%a, %Y-%m-%d at %I:%M:%S %p, GMT%z")

jp_timezone = timezone("Asia/Tokyo")

def jp_time(dt_obj):
    return dt_obj.astimezone(jp_timezone).strftime("%a, %Y-%m-%d at %I:%M:%S %p, GMT%z (Tokyo/Japan)")

discord_regex = re.compile(r"(?<!\\)[*_\[\]~`]")

def discord_escape(any_string):
    return discord_regex.sub(lambda m: f"\\{m.group(0)}", any_string)

def safe_url(any_url):
    return quote(any_url, safe=r":/&$+,;=@#~%")

def to_int(any_obj, *, default=None):
    try:
        return int(any_obj)
    except:
        return default

def get_element(container, predicate, *, default=None):
    result = default
    if isinstance(predicate, int):
        try:
            result = container[predicate]
        except IndexError:
            pass
    elif callable(predicate):
        for item in container:
            try:
                if predicate(item):
                    result = item
                    break
            except:
                pass
    else:
        raise TypeError
    return result

def _raw_page_format(container, per_page, *, separator="\n", book=None, book_amount=None, title=None, description=None, colour=None, author=None, footer=None, thumbnail_url=None):
    embeds = []
    page_amount = (len(container) - 1) // per_page + 1
    if per_page:
        for index in range(0, len(container), per_page):
            if book is None:
                desc = separator.join((description(i, item) for i, item in enumerate(container[index:index+per_page])))
                paging = f"(Page {index//per_page+1}/{page_amount})"
            else:
                desc = separator.join((description(i, item, book) for i, item in enumerate(container[index:index+per_page])))
                paging = f"(Page {index//per_page+1}/{page_amount} - Book {book+1}/{book_amount})"
            embed = discord.Embed(
                title=title,
                description=f"{desc}\n\n{paging}",
                colour=colour or discord.Embed.Empty
            )
            if author:
                embed.set_author(name=author)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
            if footer:
                embed.set_footer(text=footer)
            embeds.append(embed)
    else:
        embed = discord.Embed(title=title, description=description, colour=colour)
        if author:
            embed.set_author(name=author)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        if footer:
            embed.set_footer(text=footer)
        embeds.append(embed)
    return embeds

def page_format(container, *args, **kwargs):
    embeds = []
    if container:
        if isinstance(container[0], (list, tuple)):
            book_amount = len(container)
            title = kwargs.pop("title", None)
            if callable(title):
                return [_raw_page_format(items, *args, title=title(n), book=n, book_amount=book_amount, **kwargs) for n, items in enumerate(container)]
            else:
                return [_raw_page_format(items, *args, title=title, book=n, book_amount=book_amount, **kwargs) for n, items in enumerate(container)]
        else:
            return _raw_page_format(container, *args, **kwargs)
    else:
        return None
