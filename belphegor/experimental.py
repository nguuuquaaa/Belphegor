import discord
from discord.ext import commands
from . import utils
from .utils import config, data_type, checks
import PIL
import io
import pymongo
from datetime import datetime, timedelta
import pytz
import weakref
import collections
from PIL import ImageFont
import random

#==================================================================================================================================================

BEGINNING = datetime(2018, 6, 19, 0, 0, 0, tzinfo=pytz.utc)

#==================================================================================================================================================

class MemberStats:
    __slots__ = ("id", "guild_ids", "last_updated")

    def __init__(self, id, *, guild_ids, last_updated):
        self.id = id
        self.guild_ids = guild_ids
        self.last_updated = last_updated

    def process_status(self, stt, *, update=False):
        start = self.last_updated
        end = utils.now_time()

        start_hour = (start - BEGINNING).total_seconds() / 3600
        end_hour = (end - BEGINNING).total_seconds() / 3600
        if end_hour - start_hour > 720:
            start_hour = end_hour - 720

        first_mark = int(start_hour)
        last_mark = int(end_hour)
        marks = tuple(range(first_mark+1, last_mark+1))
        left_marks = (start_hour, *marks)
        right_marks = (*marks, end_hour)

        items = []
        for left, right in zip(left_marks, right_marks):
            if right-left > 0:
                items.append({"mark": int(left), "stt": stt, "dur": right-left})

        if update:
            self.last_updated = end
        return items

#==================================================================================================================================================
class Statistics:
    def __init__(self, bot):
        self.bot = bot
        self.user_data = bot.db.user_data
        self.belphegor_config = bot.db.belphegor_config

        now = utils.now_time()
        self.all_users = {}
        try:
            all_users = bot.saved_stuff.pop("all_users")
        except KeyError:
            for guild in self.bot.guilds:
                for member in guild.members:
                    if member.id in self.all_users:
                        self.all_users[member.id].guild_ids.append(guild.id)
                    else:
                        self.all_users[member.id] = MemberStats(member.id, guild_ids=[guild.id], last_updated=now)
        else:
            for key, value in all_users.items():
                self.all_users[key] = MemberStats(value.id, guild_ids=value.guild_ids, last_updated=value.last_updated)

    def __unload(self):
        self.bot.saved_stuff["all_users"] = self.all_users

    def get_update_requests(self, member_stats):
        m = self.bot.get_guild(member_stats.guild_ids[0]).get_member(member_stats.id)
        items = member_stats.process_status(m.status.value, update=True)
        last_mark = items[-1]["mark"]
        reqs = [
            pymongo.UpdateOne(
                {"user_id": m.id},
                {"$pull": {"status": {"mark": {"$lt": last_mark-720}}}}
            ),
            pymongo.UpdateOne(
                {"user_id": m.id},
                {"$push": {"status": {"$each": items}}, "$setOnInsert": {"user_id": m.id, "timezone": 0}},
                upsert=True
            )
        ]
        return reqs

    async def update_all(self):
        reqs = []
        for member_stats in self.all_users.values():
            await self.user_data.bulk_write(self.get_update_requests(member_stats))

    async def update(self, member):
        member_stats = self.all_users[member.id]
        await self.user_data.bulk_write(self.get_update_requests(member_stats))

    async def on_member_join(self, member):
        if member.id in self.all_users:
            self.all_users[member.id].guild_ids.append(member.guild.id)
        else:
            self.all_users[member.id] = MemberStats(member.id, guild_ids=[member.guild.id], last_updated=utils.now_time())

    async def on_member_remove(self, member):
        member_stats = self.all_users[member.id]
        member_stats.guild_ids.remove(member.guild.id)
        if not member_stats.guild_ids:
            self.all_users.pop(member.id)

    async def on_guild_join(self, guild):
        now = utils.now_time()
        for member in guild.members:
            if member.id in self.all_users:
                self.all_users[member.id].guild_ids.append(member.guild.id)
            else:
                self.all_users[member.id] = MemberStats(id=member.id, guild_ids=[guild.id], last_updated=now)

    async def on_guild_remove(self, guild):
        for member in guild.members:
            member_stats = self.all_users[member.id]
            member_stats.guild_ids.remove(guild.id)
            if not member_stats.guild_ids:
                self.all_users.pop(member.id)

    async def on_member_update(self, before, after):
        if before.status != after.status and before.guild.id == self.all_users[before.id].guild_ids[0]:
            await self.update(before)

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def guildstatus(self, ctx):
        await ctx.trigger_typing()
        statuses = (
            {"name": "online", "count": 0, "color": discord.Colour.green().to_rgba()},
            {"name": "dnd", "count": 0, "color": discord.Colour.red().to_rgba()},
            {"name": "idle", "count": 0, "color": discord.Colour.orange().to_rgba()},
            {"name": "offline", "count": 0, "color": discord.Colour.light_grey().to_rgba()}
        )
        guild = ctx.guild
        for m in guild.members:
            for i in ("online", "dnd", "idle", "offline"):
                if m.status == getattr(discord.Status, i):
                    utils.get_element(statuses, lambda x: x["name"] == i)["count"] += 1

        explode = [0, 0, 0, 40]
        maxi = 3
        maxv = float("inf")

        for i in range(3):
            v = statuses[i]["count"]
            if 0 < v < maxv:
                explode[maxi] = 0
                explode[i] = 40
                maxi = i
                maxv = v

        bytes_ = await utils.pie_chart(statuses, unit="members", outline=(0, 0, 0, 0), explode=explode, outline_width=10, loop=self.bot.loop)
        await ctx.send(file=discord.File(bytes_, "statuses.png"))

    async def fetch_total_status(self, member):
        now = utils.now_time()
        mark = int((now - BEGINNING).total_seconds() / 3600)
        member_data = [s async for s in self.user_data.aggregate([
            {
                "$match": {"user_id": member.id}
            },
            {
                "$unwind": "$status"
            },
            {
                "$redact": {
                    "$cond": {
                        "if": {"$lt": ["$status.mark", mark-720]},
                        "then": "$$PRUNE",
                        "else": "$$KEEP"
                    }
                }
            },
            {
                "$group": {
                    "_id": "$status.stt",
                    "dur": {
                        "$sum": "$status.dur"
                    }
                }
            }
        ])]

        statuses = (
            {"name": "online", "count": 0, "color": discord.Colour.green().to_rgba()},
            {"name": "dnd", "count": 0, "color": discord.Colour.red().to_rgba()},
            {"name": "idle", "count": 0, "color": discord.Colour.orange().to_rgba()},
            {"name": "offline", "count": 0, "color": discord.Colour.light_grey().to_rgba()}
        )

        for item in statuses:
            data = utils.get_element(member_data, lambda x: x["_id"]==item["name"])
            if data:
                item["count"] = data["dur"]
            if item["name"] == member.status.value:
                item["count"] += (now - self.all_users[member.id].last_updated).total_seconds() / 3600

        return statuses

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def piestatus(self, ctx, member: discord.Member=None):
        await ctx.trigger_typing()
        statuses = await self.fetch_total_status(member or ctx.author)
        bytes_ = await utils.pie_chart(statuses, unit="hours", outline=(0, 0, 0, 0), outline_width=10, loop=self.bot.loop)
        await ctx.send(file=discord.File(bytes_, filename="pie_status.png"))

    async def fetch_hourly_status(self, member, *, offset):
        now = utils.now_time()
        mark = int((now - BEGINNING).total_seconds() / 3600)
        member_data = [s async for s in self.user_data.aggregate([
            {
                "$match": {"user_id": member.id}
            },
            {
                "$unwind": "$status"
            },
            {
                "$redact": {
                    "$cond": {
                        "if": {"$lt": ["$status.mark", mark-720]},
                        "then": "$$PRUNE",
                        "else": "$$KEEP"
                    }
                }
            },
            {
                "$group": {
                    "_id": {"stt": "$status.stt", "mark": {"$mod": [{"$add": ["$status.mark", offset]}, 24]}},
                    "dur": {"$sum": "$status.dur"}
                }
            }
        ])]

        statuses = (
            {"name": "online", "count": collections.OrderedDict(((i, 0) for i in range(24))), "color": discord.Colour.green().to_rgba()},
            {"name": "dnd", "count": collections.OrderedDict(((i, 0) for i in range(24))), "color": discord.Colour.red().to_rgba()},
            {"name": "idle", "count": collections.OrderedDict(((i, 0) for i in range(24))), "color": discord.Colour.orange().to_rgba()},
            {"name": "offline", "count": collections.OrderedDict(((i, 0) for i in range(24))), "color": discord.Colour.light_grey().to_rgba()}
        )

        for item in statuses:
            for hour in range(24):
                data = utils.get_element(member_data, lambda x: x["_id"]["stt"]==item["name"] and x["_id"]["mark"]==hour)
                if data:
                    item["count"][hour] = data["dur"]
            if item["name"] == member.status.value:
                processed_stt = self.all_users[member.id].process_status(member.status.value)
                for inst in processed_stt:
                    item["count"][(inst["mark"]+offset)%24] += inst["dur"]

        return statuses

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def linestatus(self, ctx, member: discord.Member=None, offset: int=0):
        await ctx.trigger_typing()
        offset = (offset + 12) % 24 - 12
        target = member or ctx.author
        statuses = await self.fetch_hourly_status(target, offset=offset)
        title = f"{target.name}'s hourly status (offset {offset:+d})"
        bytes_ = await utils.line_chart(statuses, unit_y="hours", unit_x="time\nof day", title=title, loop=self.bot.loop)
        await ctx.send(file=discord.File(bytes_, filename="line_status.png"))

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def areastatus(self, ctx, member: discord.Member=None, offset: int=0):
        await ctx.trigger_typing()
        offset = (offset + 12) % 24 - 12
        target = member or ctx.author
        statuses = await self.fetch_hourly_status(target, offset=offset)

        #transform to percentage
        x_keys = statuses[0]["count"].keys()
        totals = collections.OrderedDict(((key, sum((item["count"][key] for item in statuses))) for key in x_keys))
        draw_data = []
        accumulate = {}
        for d in statuses:
            item = {"name": d["name"], "color": d["color"]}
            count = collections.OrderedDict()
            for key, value in d["count"].items():
                count[key] = value / totals[key] * 100 + accumulate.get(key, 0)
            item["count"] = count
            draw_data.append(item)
            accumulate = count

        #draw
        title = f"{target.name}'s hourly status (offset {offset:+d})"
        try:
            bytes_ = await utils.stacked_area_chart(draw_data, unit_y="%", unit_x="time\nof day", title=title, loop=self.bot.loop)
        except ZeroDivisionError:
            await ctx.send("I need at least 1 day worth of data to perform this command.")
        else:
            await ctx.send(file=discord.File(bytes_, filename="area_status.png"))

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Statistics(bot))
