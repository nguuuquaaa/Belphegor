from unicodedata import normalize, category
import re
import asyncio
from datetime import datetime, timedelta, timezone

_keep_char = (".", "_", " ")

def safe_filename(any_string):
    return ''.join([c for c in any_string if c.isalnum() or c in _keep_char])

_keep_special_char = ("\n", "\t")

def unifix(any_string):
    return "".join([c for c in normalize("NFKD", any_string) if category(c)[0]!="C" or c in _keep_special_char]).strip()

_loop = asyncio.get_event_loop()

async def embed_page(ctx, *, max_page, embed, timeout=60, target=None):
    message = await ctx.send(embed=embed(0))
    target = target or ctx.author
    current_page = 0
    possible_reactions = ("\u23ee", "\u25c0", "\u25b6", "\u23ed", "\u274c")
    for r in possible_reactions:
        _loop.create_task(message.add_reaction(r))
    while True:
        try:
            reaction, user = await ctx.bot.wait_for("reaction_add", check=lambda r,u: u.id==target.id and r.emoji in possible_reactions and r.message.id==message.id, timeout=timeout)
        except:
            try:
                return await message.clear_reactions()
            except:
                return
        if reaction.emoji == "\u25c0":
            current_page = max(current_page-1, 0)
            await message.edit(embed=embed(current_page))
        elif reaction.emoji == "\u25b6":
            current_page = min(current_page+1, max_page-1)
            await message.edit(embed=embed(current_page))
        elif reaction.emoji == "\u23ee":
            current_page = max(current_page-10, 0)
            await message.edit(embed=embed(current_page))
        elif reaction.emoji == "\u23ed":
            current_page = min(current_page+10, max_page-1)
            await message.edit(embed=embed(current_page))
        else:
            try:
                return await message.clear_reactions()
            except:
                return
        try:
            await message.remove_reaction(reaction, user)
        except:
            pass

async def yes_no_prompt(ctx, *, sentences, timeout=60, target=None):
    message = await ctx.send(sentences["initial"])
    target = target or ctx.author
    possible_reactions = ("\u2705", "\u274c")
    for r in possible_reactions:
        _loop.create_task(message.add_reaction(r))
    try:
        reaction, user = await ctx.bot.wait_for("reaction_add", check=lambda r,u: u.id==target.id and r.emoji in possible_reactions and r.message.id==message.id, timeout=timeout)
    except:
        _loop.create_task(message.edit(content=sentences["timeout"]))
        try:
            _loop.create_task(message.clear_reactions())
        except:
            pass
        return False
    try:
        _loop.create_task(message.clear_reactions())
    except:
        pass
    if reaction.emoji == "\u2705":
        _loop.create_task(message.edit(content=sentences["yes"]))
        return True
    else:
        _loop.create_task(message.edit(content=sentences["no"]))
        return False

def split_page(text, split_len):
    description = re.split(r"(\s)", text)
    description_page = ["",]
    cur_index = 0
    for word in description:
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
    wt = [("year", seconds//31536000), ("month", seconds%31536000//2592000), ("week", seconds%31536000%2592000//604800), ("day", seconds%31536000%2592000%604800//86400), ("hour", seconds%86400//3600), ("minute", seconds%3600//60), ("second", seconds%60)]
    text_body = ""
    for item in wt:
        if item[1] > 1:
            text_body = f"{text_body} {item[1]} {item[0]}s"
        elif item[1] == 1:
            text_body = f"{text_body} {item[1]} {item[0]}"
    return text_body.strip()

time_regex = re.compile(r"(\d+\.?\d*)(?:\s*)(w(?:(?:eek)?s?)?|d(?:(?:ay)s?)?|h(?:(?:our)s?)?|m(?:(?:in)(?:ute)?s?)?|s(?:(?:ec)(?:ond)?s?)?)(?:\b)", flags=re.I)

def extract_time(text):
    extract = time_regex.findall(text)
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
    return timedelta(**result)

def now_time():
    return datetime.now(timezone.utc)

def format_time(dt_obj):
    return dt_obj.strftime("%a, %Y-%m-%d at %I:%M:%S %p, GMT%z")