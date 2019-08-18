import discord
from unicodedata import normalize, category
import re
import asyncio
from datetime import datetime, timedelta
import pytz
from pytz import timezone
from urllib.parse import quote
import collections
import json
import functools

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

def split_iter(txt, *, check=str.isspace, keep_delimiters=True):
    word = []
    escape = False
    for c in txt:
        if escape:
            word.append(c)
            escape = False
        elif check(c):
            if word:
                yield "".join(word)
            word.clear()
            if keep_delimiters:
                yield c
        else:
            if c == "\\":
                escape = True
            word.append(c)
    else:
        if word:
            yield "".join(word)

def split_page(text, split_len, *, check=str.isspace, safe_mode=True, fix="...", strip=None):
    if not text:
        return [""]
    description_page = []
    cur_node = []
    cur_len = 0
    len_fix = len(fix)
    if strip is None:
        clean = str.strip
    else:
        clean = lambda s: s.strip(strip)
    for word in split_iter(text, check=check):
        word = no_mass_mention(word)
        if safe_mode:
            if word.startswith(("http://", "https://")):
                word = safe_url(word)
            else:
                word = discord_escape(word)

        if cur_len + len(word) < split_len:
            cur_node.append(word)
            cur_len += len(word)
        else:
            if len(word) < split_len:
                description_page.append(f"{fix}{clean(''.join(cur_node))}{fix}")
            else:
                left = split_len - cur_len
                cur_node.append(word[:left])
                description_page.append(f"{fix}{clean(''.join(cur_node))}{fix}")
                stuff = (f"{fix}{clean(word[i+left:i+split_len+left])}{fix}" for i in range(0, len(word)-left, split_len))
                description_page.extend(stuff)
                word = description_page.pop(-1)[len_fix:-len_fix]
            cur_node = [word]
            cur_len = len(word)
    if cur_node:
        description_page.append(f"{fix}{clean(''.join(cur_node))}")
    else:
        description_page[-1] = description_page[-1][:-len_fix]
    description_page[0] = description_page[0][len_fix:]
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
        for i, c in enumerate(text):
            if c.isspace():
                break
        text = text[i:]
    text = text.strip("` \n\r\t\v\f")
    return text

_format_regex = re.compile(r"(?<!\\)\{([^\\]+?)\}")
def str_format(text, **kwargs):
    return _format_regex.sub(lambda m: kwargs[m.group(1)], text)

#==================================================================================================================================================

_WHITESPACE = re.compile(r"\s*")

class ConcatJSONDecoder(json.JSONDecoder):
    def decode(self, s, _w=_WHITESPACE.match):
        s = s.strip()
        s_len = len(s)

        objs = []
        end = 0
        while end != s_len:
            obj, end = self.raw_decode(s, idx=_w(s, end).end())
            objs.append(obj)
        return objs

load_concat_json = functools.partial(json.loads, cls=ConcatJSONDecoder)
