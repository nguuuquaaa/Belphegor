import discord
from discord.ext import commands
from . import checks, string_utils as belfmt, paginator
import asyncio
import re
import copy
import collections
from datetime import datetime, timedelta
import pytz
import itertools
import time
import json
import io

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
