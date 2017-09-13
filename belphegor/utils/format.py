from unicodedata import normalize
import re

def unifix(any_string):
    return normalize("NFKD", any_string).strip()

async def embed_page(ctx, *, max_page, embed):
    message = await ctx.send(embed=embed(0))
    current_page = 0
    possible_reactions = ("\u23ee", "\u23ed", "\u274c")
    for r in possible_reactions:
        await message.add_reaction(r)
    while True:
        try:
            reaction, user = await ctx.bot.wait_for("reaction_add", check=lambda r,u:u.id==ctx.author.id and r.emoji in possible_reactions and r.message.id==message.id, timeout=60)
        except:
            try:
                return await message.clear_reactions()
            except:
                return
        if reaction.emoji == "\u23ee":
            if current_page > 0:
                current_page -= 1
                await message.edit(embed=embed(current_page))
            try:
                await message.remove_reaction(reaction, user)
            except:
                pass
        elif reaction.emoji == "\u23ed":
            if current_page < max_page - 1:
                current_page += 1
                await message.edit(embed=embed(current_page))
            try:
                await message.remove_reaction(reaction, user)
            except:
                pass
        else:
            try:
                return await message.clear_reactions()
            except:
                return

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
    wt = [("year", seconds//31536000), ("month", seconds%31536000//2592000), ("week", seconds%31536000%2592000//604800), ("day", seconds%31536000%2592000%604800//86400), ("hour", seconds%86400//3600), ("minute", seconds%3600//60), ("second", seconds%60)]
    text_body = []
    for item in wt:
        if item[1] > 1:
            text_body.append(f"{item[1]} {item[0]}s")
        elif item[1] == 1:
            text_body.append(f"{item[1]} {item[0]}")
    return " ".join(text_body)

time_regex = re.compile(r"(\d+\.?\d*)(?:\s*)(y(?:(?:ear)?s?)?|w(?:(?:eek)?s?)?|d(?:(?:ay)s?)?|h(?:(?:our)s?)?|m(?:(?:in)(?:ute)?s?)?|s(?:(?:ec)(?:ond)?s?)?)(?:\b)", flags=re.I)

def extract_time(text):
    extract = time_regex.findall(text)
    if extract:
        wait_time = 0
        for wt in extract:
            fc = wt[1][:1].lower()
            if fc == "y":
                wait_time += float(wt[0]) * 31536000
            elif fc == "w":
                wait_time += float(wt[0]) * 604800
            elif fc == "d":
                wait_time += float(wt[0]) * 86400
            elif fc == "h":
                wait_time += float(wt[0]) * 3600
            elif fc == "m":
                wait_time += float(wt[0]) * 60
            elif fc == "s":
                wait_time += float(wt[0])
        wait_time = int(wait_time)
        return wait_time
    else:
        return 0