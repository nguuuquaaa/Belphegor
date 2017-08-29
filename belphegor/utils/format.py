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
    description = [d for d in re.split(r"(\n)|( )", text) if d]
    description_page = ["",]
    cur_index = 0
    for word in description:
        cur_node = description_page[cur_index]
        if len(cur_node) + len(word) < split_len:
            description_page[cur_index] = f"{cur_node}{word}"
        else:
            description_page[cur_index] = f"{cur_node}..."
            if len(word) < split_len:
                description_page.append(f"...{word}")
                cur_index += 1
            else:
                stuff = [f"...{word[i:i+split_len]}..." for i in range(0, len(word), split_len)]
                description_page.extend(stuff)
                cur_index += len(stuff)
    return description_page