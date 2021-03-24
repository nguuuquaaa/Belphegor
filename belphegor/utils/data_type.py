import discord
from discord.ext import commands
from . import checks, format as belfmt, paginator
import asyncio
import re
import copy
import collections
from datetime import datetime, timedelta
import pytz
import itertools
import time

#==================================================================================================================================================

def to_int(any_obj, base=10, *, default=None):
    try:
        return int(any_obj, base)
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
        raise TypeError("Predicate is an int or a callable.")
    return result

def _insert_spaces(attrs):
    iter_attrs = iter(attrs)
    yield f"${next(iter_attrs)}"
    for a in iter_attrs:
        yield " "
        yield f"${a}"

def circle_iter(iterable, with_index=False):
    if iterable:
        if with_index:
            while True:
                for i, item in enumerate(iterable):
                    yield i, item
        else:
            while True:
                for item in iterable:
                    yield item
    else:
        raise ValueError("Cannot circle-iterate empty container.")

#==================================================================================================================================================

class BaseObject:
    def __init__(self, data):
        for key, value in data.items():
            if key[0] != "_":
                setattr(self, key, value)

#==================================================================================================================================================

class BelphegorContext(commands.Context):
    async def send_text_or_file(self, content, *, extension=None, **kwargs):
        if len(content) > 1950:
            if extension is None:
                filename = "file.txt"
            else:
                filename = f"file.{extension}"
            kwargs["file"] = discord.File.from_str(content, filename)
            await self.send(**kwargs)
        else:
            if extension is None:
                await self.send(content, **kwargs)
            else:
                await self.send(f"```{extension}\n{content}\n```", **kwargs)

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

    async def search(self, name, pool, *, cls=BaseObject, colour=None, atts=[], index_att=None, name_att, emoji_att=None, prompt=None, sort={}):
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
        pipeline = [
            {
                "$addFields": {
                    "all_att_concat": {
                        "$concat": list(_insert_spaces(atts))
                    }
                }
            },
            {
                "$match": {
                    "$and": [
                        {
                            "all_att_concat": {
                                "$regex": re.escape(n),
                                "$options": "i"
                            }
                        } for n in name.split()
                    ]
                }
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
            result = int(msg.content)
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

#==================================================================================================================================================

class Observer:
    __slots__ = ("_item", "_flag")

    def __init__(self, item=None):
        self._item = item
        self._flag = asyncio.Event()

    def clear(self):
        self._flag.clear()

    def edit(self, att, value):
        setattr(self._item, att, value)
        self._flag.set()

    def assign(self, item):
        self._item = item
        self._flag.set()

    def call(self, method, *args, **kwargs):
        ret = getattr(self._item, method)(*args, **kwargs)
        self._flag.set()
        return ret

    async def wait(self, *, timeout=None):
        if isinstance(timeout, (int, float)):
            await asyncio.wait_for(self._flag.wait(), timeout)
        elif timeout is None:
            await self._flag.wait()
        else:
            raise TypeError("Watchu thonk timeout iz?")

    @property
    def item(self):
        return copy.copy(self._item)

    @item.setter
    def item(self, value):
        raise AttributeError("Dun explicitly do dis.")

    def __bool__(self):
        return bool(self._item)

#==================================================================================================================================================

class AutoCleanupDict:
    END_OF_TIME = datetime(year=9999, month=1, day=1, tzinfo=pytz.utc)

    def __init__(self, limit=120, *, loop=None):
        self.limit = limit
        self.loop = loop or asyncio.get_event_loop()
        self.container = {}
        self.deadline = collections.OrderedDict()
        self.active = asyncio.Event()
        self.working_task = self.loop.create_task(self.check_deadline())

    def update_deadline(self, key):
        self.deadline[key] = belfmt.now_time() + timedelta(seconds=self.limit)
        self.deadline.move_to_end(key)
        self.active.set()

    def __getitem__(self, key):
        return self.container[key]

    def __setitem__(self, key, value):
        self.container[key] = value
        self.update_deadline(key)

    def get(self, key, default=None):
        return self.container.get(key, default)

    def _pop_key(self, key, default=None):
        self.deadline.pop(key, None)
        value = self.container.pop(key, default)
        self.loop.create_task(self.on_pop_item(key, value))
        return value

    def pop(self, key, default=None):
        self.active.set()
        return self._pop_key(key, default)

    async def check_deadline(self):
        active = self.active
        container = self.container
        deadline = self.deadline
        _pop_key = self._pop_key
        del self
        while True:
            active.clear()
            if container:
                first_key, first_deadline = next(iter(deadline.items()))
                try:
                    await asyncio.wait_for(active.wait(), (first_deadline - belfmt.now_time()).total_seconds())
                except asyncio.TimeoutError:
                    _pop_key(first_key)
            else:
                await active.wait()

    def cleanup(self):
        self.working_task.cancel()

    def __del__(self):
        self.cleanup()

    def register_event_handler(self, event_name, coro_func):
        if not asyncio.iscoroutinefunction(coro_func):
            raise TypeError("Event handler must be a coroutine.")

        setattr(self, "on_"+event_name, coro_func)
        return coro_func

    async def on_pop_item(self, key, value):
        pass
