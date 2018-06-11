import discord
from unicodedata import normalize, category
import re
import asyncio
from datetime import datetime, timedelta
import pytz
from pytz import timezone
from urllib.parse import quote
import collections

#==================================================================================================================================================

_keep_char = (".", "_", " ")

def safe_filename(any_string):
    return ''.join((c for c in any_string if c.isalnum() or c in _keep_char))

_keep_special_char = ("\n", "\t")

def unifix(any_string):
    return "".join((c for c in normalize("NFKC", any_string) if category(c)[0]!="C" or c in _keep_special_char)).strip()

def no_mass_mention(word):
    if word == "@everyone":
        return "@\u200beveryone"
    elif word == "@here":
        return "@\u200bhere"
    else:
        return word

_split_regex = re.compile(r"(\s)")

def split_page(text, split_len, *, safe_mode=True):
    description = _split_regex.split(text)
    description_page = ["",]
    cur_index = 0
    for word in description:
        word = no_mass_mention(word)
        if safe_mode:
            if word.startswith(("http://", "https://")):
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
    r"(y(?:ears?)?|mo(?:nths?)?|w(?:eeks?)?|d(?:ays?)?|h(?:(?:ou)?rs?)?|m(?:in(?:ute)?s?)?|s(?:ec(?:ond)?s?)?)"
    r"(?:[\s\b]*)",
    flags=re.I
)

def extract_time(text):
    extract = time_regex.findall(text)
    new_text = time_regex.sub("", text)
    result = {"years": 0, "months": 0, "weeks": 0, "days": 0, "hours": 0, "minutes": 0, "seconds": 0}
    if extract:
        for wt in extract:
            fc = wt[1]
            if fc.startswith("y"):
                result["years"] += float(wt[0])
            elif fc.startswith("mo"):
                result["months"] += float(wt[0])
            elif fc.startswith("w"):
                result["weeks"] += float(wt[0])
            elif fc.startswith("d"):
                result["days"] += float(wt[0])
            elif fc.startswith("h"):
                result["hours"] += float(wt[0])
            elif fc.startswith("m"):
                result["minutes"] += float(wt[0])
            elif fc.startswith("s"):
                result["seconds"] += float(wt[0])
    result["days"] += result.pop("years") * 365
    result["days"] += result.pop("months") * 30
    return new_text, timedelta(**result)

def now_time(tzinfo=pytz.utc):
    return datetime.now(tzinfo)

def format_time(dt_obj):
    return dt_obj.strftime("%a, %Y-%m-%d at %I:%M:%S %p, UTC%z")

jp_timezone = timezone("Asia/Tokyo")

def jp_time(dt_obj):
    return dt_obj.astimezone(jp_timezone).strftime("%a, %Y-%m-%d at %I:%M:%S %p, UTC%z (Tokyo/Japan)")

discord_regex = re.compile(r"[*_\[\]~`\\<>]")

def discord_escape(any_string):
    return discord_regex.sub(lambda m: f"\\{m.group(0)}", any_string)

def safe_url(any_url):
    return quote(any_url, safe=r":/&$+,;=@#~%?")

def progress_bar(rate, length=2):
    rate = rate if rate <= 1 else 1
    bf = "\u2588" * int(rate*10*length)
    c = "\u2591"
    return f"Progress: {bf:{c}<{10*length}} {rate*100:.2f}%"

def clean_codeblock(text):
    if text.startswith("```"):
        text = text.partition("\n")[2]
    text = text.strip("` \n")
    return text

_format_regex = re.compile(r"(?<!\\)\{([^\\]+)\}")
def str_format(text, **kwargs):
    return _format_regex.sub(lambda m: kwargs[m.group(1)], text)
