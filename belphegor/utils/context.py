import discord
from discord.ext import commands
from . import checks, string_utils as belfmt, paginator, data_type
import asyncio
import re
import time
import json
import io

#==================================================================================================================================================

def _insert_spaces(attrs):
    iter_attrs = iter(attrs)
    yield f"${next(iter_attrs)}"
    for a in iter_attrs:
        yield " "
        yield f"${a}"

#==================================================================================================================================================

class BelphegorContext(commands.Context):
    async def send_json(self, obj, *, filename="file.json", **kwargs):
        text = json.dumps(obj, indent=4, ensure_ascii=False)
        bytesio = io.BytesIO(text.encode("utf-8"))
        await self.send(
            file=discord.File(bytesio, filename),
            **kwargs
        )

    async def confirm(self):
        await self.message.add_reaction("\u2705")

    async def deny(self):
        await self.message.add_reaction("\u274c")

    async def yes_no_prompt(self, sentences, *, timeout=60, target=None, delete_mode=False):
        _loop = self.bot.loop
        message = await self.send(sentences["initial"])
        target = target or self.author
        possible_reactions = ("\u2705", "\u274c")
        for r in possible_reactions:
            _loop.create_task(message.add_reaction(r))
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=lambda r,u: u.id==target.id and r.emoji in possible_reactions and r.message.id==message.id,
                timeout=timeout
            )
        except:
            result = None
            if not delete_mode:
                _loop.create_task(message.edit(content=sentences["timeout"]))
        else:
            if reaction.emoji == "\u2705":
                result = True
                if not delete_mode:
                    _loop.create_task(message.edit(content=sentences["yes"]))
            else:
                result = False
                if not delete_mode:
                    _loop.create_task(message.edit(content=sentences["no"]))
        if delete_mode:
            _loop.create_task(message.delete())
        else:
            _loop.create_task(paginator.try_it(message.clear_reactions()))
        return result

    async def search(self, name, pool, *, cls=data_type.BaseObject, colour=None, atts=[], aliases_att=None, index_att=None, name_att, emoji_att=None, prompt=None, sort={}):
        if index_att:
            try:
                item_id = int(name)
            except ValueError:
                pass
            else:
                result = await pool.find_one({index_att: item_id})
                if result:
                    return cls(result)
                else:
                    raise checks.CustomError(f"Can't find {name} in database.")

        match_query = {
            "$and": [
                {
                    "all_att_concat": {
                        "$regex": re.escape(n),
                        "$options": "i"
                    }
                } for n in name.split()
            ]
        }
        if aliases_att:
            match_query = {
                "$or": [
                    match_query,
                    {
                        aliases_att: {
                            "$regex": ".*?".join(map(re.escape, name.split())),
                            "$options": "i"
                        }
                    }
                ]
            }

        pipeline = [
            {
                "$addFields": {
                    "all_att_concat": {
                        "$concat": list(_insert_spaces(atts))
                    }
                }
            },
            {
                "$match": match_query
            }
        ]
        if sort:
            add_fields = {}
            sort_order = {}
            for key, value in sort.items():
                if isinstance(value, int):
                    sort_order[key] = value
                elif isinstance(value, (list, tuple)):
                    new_field = f"_sort_{key}"
                    add_fields[new_field] = {"$indexOfArray": [value, f"${key}"]}
                    sort_order[new_field] = 1
            if add_fields:
                pipeline.append({"$addFields": add_fields})
            pipeline.append({"$sort": sort_order})
        cursor = pool.aggregate(pipeline)
        if prompt is False:
            lower_name = name.lower()
            async for item_data in cursor:
                if lower_name in (item_data.get(att, "").lower() for att in atts):
                    break
            try:
                return cls(item_data)
            except:
                raise checks.CustomError(f"Can't find {name} in database.")
        else:
            result = [cls(item_data) async for item_data in cursor]
            if not result:
                raise checks.CustomError(f"Can't find {name} in database.")
            elif len(result) == 1 and not prompt:
                return result[0]
            emojis = self.cog.emojis

            paging = paginator.Paginator(
                result, 10,
                title="Do you mean:",
                description=lambda i, x: f"`{i+1}:` {emojis.get(getattr(x, emoji_att), '') if emoji_att else ''}{getattr(x, name_att)}",
                colour=colour
            )
            t = self.bot.loop.create_task(paging.navigate(self))
            index = await self.wait_for_choice(max=len(result))
            t.cancel()
            if index is None:
                return None
            else:
                return result[index-1]

    async def wait_for_choice(self, *, max, target=None, timeout=600):
        target = target or self.author
        try:
            msg = await self.bot.wait_for("message", check=lambda m: m.author.id==target.id and m.channel.id==self.channel.id, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        try:
            result = int(msg.content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip())
        except:
            return None
        if 0 < result <= max:
            return result
        else:
            return None

    async def progress_bar(self, job, messages={}, *, interval=5):
        initial = messages.get("initial", "")
        done = messages.get("done", "")
        msg = await self.send(f"{initial}{belfmt.progress_bar(0)}")
        prev = time.monotonic()
        async for progress in job:
            cur = time.monotonic()
            if cur - prev >= interval:
                await msg.edit(content=f"{initial}{belfmt.progress_bar(progress)}")
                prev = cur
        await msg.edit(content=f"{done}{belfmt.progress_bar(1)}")
