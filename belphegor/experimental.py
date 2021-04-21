import discord
from discord.ext import commands
from . import utils
from .utils import config, checks, modding
import PIL
import io
import pymongo
from datetime import datetime, timedelta
import pytz
import collections
import json
import asyncio
import traceback

#==================================================================================================================================================

BEGINNING = datetime(2018, 6, 19, 0, 0, 0, tzinfo=pytz.utc)
BATCH_SIZE = 1000
WAIT_TIME = 300

#==================================================================================================================================================

class WTFException(Exception):
    pass

#==================================================================================================================================================

class MemberStats:
    __slots__ = ("id", "last_updated")

    def __init__(self, id, *, last_updated):
        self.id = id
        self.last_updated = last_updated

    def process_status(self, stt, *, update=False):
        start = self.last_updated
        end = utils.now_time()

        if end > start:
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
        else:
            return []

#==================================================================================================================================================

class Statistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_data = bot.db.user_data
        self.belphegor_config = bot.db.belphegor_config

        self.fetch_ready = asyncio.Event()
        self.done_update_event = asyncio.Event()
        self.done_update_event.clear()

        self.all_users = {}
        try:
            all_users = bot.saved_stuff.pop("all_users")
        except KeyError:
            self.fetch_ready.clear()
            bot.loop.create_task(self.fetch_users())
        else:
            self.fetch_ready.set()
            self.all_users.update(all_users)

        self.all_requests = bot.saved_stuff.pop("status_updates", asyncio.Queue())
        self.update_task = bot.create_task_and_count(self.update_regularly())
        self.clear_task = bot.create_task_and_count(self.clear_old_data())

    def cog_unload(self):
        self.bot.saved_stuff["all_users"] = self.all_users
        self.bot.saved_stuff["status_updates"] = self.all_requests
        try:
            self.update_task.cancel()
        except:
            pass
        try:
            self.clear_task.cancel()
        except:
            pass

    async def fetch_users(self):
        user_ids = []
        async for doc in self.user_data.aggregate([
            {
                "$group": {
                    "_id": None,
                    "user_ids": {
                        "$push": "$user_id"
                    }
                }
            }
        ]):
            user_ids = doc["user_ids"]
        now = utils.now_time()
        for user_id in user_ids:
            self.all_users[user_id] = MemberStats(user_id, last_updated=now)

        self.fetch_ready.set()

    async def clear_old_data(self):
        try:
            while True:
                await asyncio.sleep(3600)
                end = utils.now_time()
                end_hour = (end - BEGINNING).total_seconds() / 3600
                last_mark = int(end_hour)
                await self.user_data.update_many({}, {"$pull": {"status": {"mark": {"$lt": last_mark-720}}}})
        except asyncio.CancelledError:
            pass

    def get_first_member(self, user_id):
        for g in self.bot.guilds:
            m = g.get_member(user_id)
            if m:
                return m

    def get_update_request(self, member_stats, status):
        member_id = member_stats.id
        items = member_stats.process_status(status, update=True)
        if items:
            return pymongo.UpdateOne(
                {"user_id": member_id},
                {"$push": {"status": {"$each": items}}}
            )
        else:
            return None

    async def update_regularly(self):
        all_reqs = []

        async def update():
            await self.user_data.bulk_write(all_reqs)
            all_reqs.clear()

        try:
            while True:
                try:
                    req = await asyncio.wait_for(self.all_requests.get(), WAIT_TIME)
                except asyncio.TimeoutError:
                    if all_reqs:
                        await asyncio.shield(update())
                else:
                    all_reqs.append(req)
                    if len(all_reqs) >= BATCH_SIZE:
                        await asyncio.shield(update())
        except asyncio.CancelledError:
            if all_reqs:
                await update()
            self.done_update_event.set()
        except Exception as e:
            text = traceback.format_exc()
            if len(text) > 1950:
                text = f"{e.__class__.__name__}: {e}"
            await self.bot.error_hook.execute(f"```\n{text}\n```")

    async def update_all(self):
        try:
            await asyncio.wait_for(self.done_update_event.wait(), 30)
        except asyncio.TimeoutError:
            return

        all_reqs = []
        for user_id, member_stats in self.all_users.items():
            member = self.get_first_member(user_id)
            req = self.get_update_request(member_stats, member.status.value)
            if req:
                all_reqs.append(req)

        for index in range(0, len(all_reqs), BATCH_SIZE):
            batch = all_reqs[index:index+BATCH_SIZE]
            await self.user_data.bulk_write(batch)

    async def update(self, member):
        member_stats = self.all_users.get(member.id)
        if member_stats:
            req = self.get_update_request(member_stats, member.status.value)
            if req:
                await self.all_requests.put(req)

    # @commands.Cog.listener()
    # async def on_member_join(self, member):
    #    if member.bot and member.id not in self.all_users:
    #        await self.update_opt_in(member, True)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.id in self.all_users:
            for g in self.bot.guilds:
                m = g.get_member(member.id)
                if m and m.guild != member.guild:
                    break
            else:
                await self.update_opt_in(member, False)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.status != after.status:
            if getattr(before, "id", None) in self.all_users:
                await self.update(before)

    async def check_opt_in_user(self, member):
        await self.fetch_ready.wait()
        if member.id in self.all_users:
            return
        else:
            raise checks.CustomError(f"{member.name} hasn't toggled presence record on yet.")

    @modding.help(brief="Server members status summary", category="Experimental", field="Status", paragraph=0)
    @commands.command(aliases=["serverstatus"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def guildstatus(self, ctx):
        '''
           `>>guildstatus`
            Display pie chart showing current guild status.
        '''
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

        for i in range(4):
            v = statuses[i]["count"]
            if 0 < v < maxv:
                explode[maxi] = 0
                explode[i] = 40
                maxi = i
                maxv = v

        bytes_ = await utils.pie_chart(
            statuses, title=f"{ctx.guild.name}'s current status", unit="members",
            outline=(0, 0, 0, 0), explode=explode, outline_width=10, loop=self.bot.loop
        )
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

    @modding.help(brief="User status summary ([example](https://i.imgur.com/QG7K34e.png))", category="Experimental", field="Status", paragraph=0)
    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def piestatus(self, ctx, member: discord.Member=None):
        '''
           `>>piestatus <optional: member>`
            Display pie chart showing total status of target member.
            Default member is command invoker.
        '''
        target = member or ctx.author
        await self.check_opt_in_user(target)
        await ctx.trigger_typing()
        statuses = await self.fetch_total_status(target)
        bytes_ = await utils.pie_chart(statuses, title=f"{target.display_name}'s total status", unit="hours", outline=(0, 0, 0, 0), outline_width=10, loop=self.bot.loop)
        await ctx.send(file=discord.File(bytes_, filename="pie_status.png"))

    async def fetch_daily_status(self, member):
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
                    "_id": {"stt": "$status.stt", "day": {"$floor": {"$divide": [{"$subtract": ["$status.mark", mark]}, 24]}}},
                    "dur": {"$sum": "$status.dur"}
                }
            }
        ])]

        statuses = (
            {"name": "online", "count": collections.OrderedDict(((i, 0) for i in range(30, 0, -1))), "color": discord.Colour.green().to_rgba()},
            {"name": "dnd", "count": collections.OrderedDict(((i, 0) for i in range(30, 0, -1))), "color": discord.Colour.red().to_rgba()},
            {"name": "idle", "count": collections.OrderedDict(((i, 0) for i in range(30, 0, -1))), "color": discord.Colour.orange().to_rgba()},
            {"name": "offline", "count": collections.OrderedDict(((i, 0) for i in range(30, 0, -1))), "color": discord.Colour.light_grey().to_rgba()}
        )

        for item in statuses:
            for day in range(-30, 0):
                data = utils.get_element(member_data, lambda x: x["_id"]["day"]==day and x["_id"]["stt"]==item["name"])
                if data:
                    item["count"][-day] = data["dur"]
            if item["name"] == member.status.value:
                processed_stt = self.all_users[member.id].process_status(member.status.value)
                for inst in processed_stt:
                    _x = -(inst["mark"]-mark)//24
                    if _x < 0:
                        item["count"][_x] += inst["dur"]

        return statuses

    @modding.help(brief="User status by past day", category="Experimental", field="Status", paragraph=0)
    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def linestatus(self, ctx, member: discord.Member=None):
        '''
           `>>linestatus <optional: member>`
            Display line chart showing daily status of target member.
            Default member is command invoker. Default offset target's pre-set timezone, or 0 if not set.
        '''
        target = member or ctx.author
        await self.check_opt_in_user(target)
        await ctx.trigger_typing()
        statuses = await self.fetch_daily_status(target)
        title = f"{target.display_name}'s status by day"
        try:
            bytes_ = await utils.line_chart(statuses, unit_y="hours", unit_x="past day", title=title, loop=self.bot.loop)
        except ZeroDivisionError:
            await ctx.send("I need at least 1 hour worth of data to perform this command.")
        else:
            await ctx.send(file=discord.File(bytes_, filename="line_status.png"))

    def better_offset(self, offset):
        return (offset + 11) % 24 - 11

    async def fetch_hourly_status(self, member, *, offset):
        now = utils.now_time()
        mark = int((now - BEGINNING).total_seconds() / 3600)
        if offset is None:
            offset = "$timezone"
        raw_data = [s async for s in self.user_data.aggregate([
            {
                "$match": {"user_id": member.id}
            },
            {
                "$facet": {
                    "data": [
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
                    ],
                    "timezone": [
                        {"$project": {"_id": False, "timezone": "$timezone"}}
                    ]
                }
            }
        ])][0]
        member_data = raw_data["data"]
        if isinstance(offset, str):
            r = raw_data["timezone"]
            if r:
                offset = r[0]["timezone"]
            else:
                offset = 0

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

        return offset, statuses

    @modding.help(brief="User status by daily hour", category="Experimental", field="Status", paragraph=0)
    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def areastatus(self, ctx, member: discord.Member=None, offset=None):
        '''
           `>>areastatus <optional: member> <optional: offset>`
            Display stacked area chart showing hourly status percentage of target member.
            Default member is command invoker. Default offset target's pre-set timezone, or 0 if not set.
        '''
        target = member or ctx.author
        await self.check_opt_in_user(target)
        await ctx.trigger_typing()
        if offset is not None:
            try:
                offset = int(offset)
            except:
                return await ctx.send("Offset should be an integer.")
            else:
                offset = self.better_offset(offset)
        offset, statuses = await self.fetch_hourly_status(target, offset=offset)

        #transform to percentage
        x_keys = statuses[0]["count"].keys()
        totals = collections.OrderedDict(((key, sum((item["count"][key] for item in statuses))) for key in x_keys))
        draw_data = []
        for d in statuses:
            item = {"name": d["name"], "color": d["color"]}
            count = collections.OrderedDict()
            for key, value in d["count"].items():
                t = totals[key]
                if t > 0:
                    count[key] = value / t * 100
                else:
                    count[key] = 0
            item["count"] = count
            draw_data.append(item)

        #draw
        title = f"{target.display_name}'s status by time of day (offset {offset:+d})"
        try:
            bytes_ = await utils.stacked_area_chart(draw_data, unit_y="%", unit_x="time\nof day", title=title, loop=self.bot.loop)
        except ZeroDivisionError:
            await ctx.send("I need at least 1 day worth of data to perform this command.")
        else:
            await ctx.send(file=discord.File(bytes_, filename="area_status.png"))

    async def fetch_weekly_status(self, member):
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
                        "if": {"$lt": ["$status.mark", mark-672]},
                        "then": "$$PRUNE",
                        "else": "$$KEEP"
                    }
                }
            },
            {
                "$group": {
                    "_id": {"stt": "$status.stt", "week": {"$floor": {"$divide": [{"$subtract": ["$status.mark", mark]}, 168]}}},
                    "dur": {"$sum": "$status.dur"}
                }
            }
        ])]

        statuses = (
            {"name": "online", "count": collections.OrderedDict(((i, 0) for i in range(4, 0, -1))), "color": discord.Colour.green().to_rgba()},
            {"name": "dnd", "count": collections.OrderedDict(((i, 0) for i in range(4, 0, -1))), "color": discord.Colour.red().to_rgba()},
            {"name": "idle", "count": collections.OrderedDict(((i, 0) for i in range(4, 0, -1))), "color": discord.Colour.orange().to_rgba()},
            {"name": "offline", "count": collections.OrderedDict(((i, 0) for i in range(4, 0, -1))), "color": discord.Colour.light_grey().to_rgba()}
        )

        for item in statuses:
            for week in range(-4, 0):
                data = utils.get_element(member_data, lambda x: x["_id"]["week"]==week and x["_id"]["stt"]==item["name"])
                if data:
                    item["count"][-week] = data["dur"]
            if item["name"] == member.status.value:
                processed_stt = self.all_users[member.id].process_status(member.status.value)
                for inst in processed_stt:
                    _x = -(inst["mark"]-mark)//168
                    if _x < 0:
                        item["count"][_x] += inst["dur"]

        return statuses

    @modding.help(brief="User status by past week", category="Experimental", field="Status", paragraph=0)
    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def barstatus(self, ctx, member: discord.Member=None):
        '''
           `>>barstatus <optional: member>`
            Display bar chart showing weekly status of target member.
            Default member is command invoker. Default offset target's pre-set timezone, or 0 if not set.
        '''
        target = member or ctx.author
        await self.check_opt_in_user(target)
        await ctx.trigger_typing()
        statuses = await self.fetch_weekly_status(target)
        title = f"{target.display_name}'s status by week"
        try:
            bytes_ = await utils.bar_chart(statuses, unit_y="hours", unit_x="past week", title=title, loop=self.bot.loop)
        except ZeroDivisionError:
            await ctx.send("I need at least 1 hour worth of data to perform this command.")
        else:
            await ctx.send(file=discord.File(bytes_, filename="bar_status.png"))

    @modding.help(brief="Set default timezone for chart commands", category="Experimental", field="Status", paragraph=1)
    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def timezone(self, ctx, offset: int):
        '''
           `>>timezone <offset>`
            Set default offset for chart commands..
        '''
        await self.check_opt_in_user(ctx.author)
        offset = self.better_offset(offset)
        await self.user_data.update_one({"user_id": ctx.author.id}, {"$set": {"timezone": offset}})
        await ctx.send(f"Default offset has been set to {offset:+d}")

    async def update_opt_in(self, member, add):
        await self.fetch_ready.wait()
        member_id = member.id
        if add:
            self.all_users[member_id] = MemberStats(member_id, last_updated=utils.now_time())
            await self.user_data.update_one(
                {"user_id": member_id},
                {"$set": {"user_id": member_id, "timezone": 0, "status": []}},
                upsert=True
            )
        else:
            self.all_users.pop(member_id, None)
            await self.user_data.delete_many({"user_id": member_id})

    @modding.help(brief="Toggle presence tracking, required for user charts", category="Experimental", field="Status", paragraph=1)
    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def togglestats(self, ctx, member: discord.Member=None):
        '''
           `>>togglestats <optional: member>`
            Toggle presence tracking on/off for chart commands.
            If member is a bot, then toggle tracking for that bot, else ignore.
            Bot tracking cannot be turned off.
        '''
        if member:
            if not member.bot:
                return await ctx.send("You can only toggle presence tracking for bots.")
        else:
            member = ctx.author
        if member.id not in self.all_users:
            sentences = {
                "initial": "By using this command, you agree to let this bot record and publicize your presence data in detail.\n" \
                    "Do you wish to proceed?",
                "yes": "Your presence data will be recorded from now on.",
                "no": "Cancelled.",
                "timeout": "Cancelled."
            }
            result = await ctx.yes_no_prompt(sentences)
            if result:
                await self.update_opt_in(member, True)
        else:
            if member.bot:
                return await ctx.send("Bot tracking cannot be turned off.")
            else:
                sentences = {
                    "initial": "Your presence data will be erased, and will not be recorded from now on.\n" \
                        "Do you wish to proceed?",
                    "yes": "Done.",
                    "no": "Cancelled.",
                    "timeout": "Cancelled."
                }
                result = await ctx.yes_no_prompt(sentences)
                if result:
                    await self.update_opt_in(member, False)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Statistics(bot))
