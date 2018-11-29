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
DISCORDPY_GUILD_ID = 336642139381301249

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
        self.command_data = bot.db.command_data

        self.command_run_count = bot.saved_stuff.pop("command_run_count", {})

        now = utils.now_time()
        self.all_users = {}
        try:
            all_users = bot.saved_stuff.pop("all_users")
        except KeyError:
            dpy_guild = bot.get_guild(DISCORDPY_GUILD_ID)
            for member in dpy_guild.members:
                self.all_users[member.id] = MemberStats(member.id, last_updated=now)
        else:
            for key, value in all_users.items():
                self.all_users[key] = MemberStats(value.id, last_updated=value.last_updated)

    def __unload(self):
        self.bot.saved_stuff["all_users"] = self.all_users
        self.bot.saved_stuff["command_run_count"] = self.command_run_count

    def get_update_requests(self, member_stats, member=None):
        if member:
            m = member
        else:
            g = self.bot.get_guild(DISCORDPY_GUILD_ID)
            m = g.get_member(member_stats.id)
            if not m:
                return []

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
        all_reqs = []
        for member_stats in self.all_users.values():
            reqs = self.get_update_requests(member_stats)
            all_reqs.extend(reqs)
            if len(all_reqs) >= 100:
                await self.user_data.bulk_write(all_reqs)
                all_reqs.clear()
        if all_reqs:
            await self.user_data.bulk_write(all_reqs)

    async def update(self, member):
        member_stats = self.all_users[member.id]
        reqs = self.get_update_requests(member_stats, member)
        if reqs:
            await self.user_data.bulk_write(reqs)

    async def on_member_join(self, member):
        if member.guild.id == DISCORDPY_GUILD_ID:
            self.all_users[member.id] = MemberStats(member.id, last_updated=utils.now_time())

    async def on_member_remove(self, member):
        if member.guild.id == DISCORDPY_GUILD_ID:
            self.all_users.pop(member.id)

    async def on_member_update(self, before, after):
        if before.guild.id == DISCORDPY_GUILD_ID:
            if before.status != after.status:
                try:
                    m = self.all_users[before.id]
                except KeyError:
                    m = MemberStats(id=before.id, last_updated=utils.now_time())
                    self.all_users[before.id] = m
                else:
                    if before:
                        await self.update(before)

    @commands.command()
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

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @checks.in_certain_guild(DISCORDPY_GUILD_ID)
    async def piestatus(self, ctx, member: discord.Member=None):
        '''
           `>>piestatus <optional: member>`
            Display pie chart showing total status of target member.
            Default member is command invoker.
        '''
        await ctx.trigger_typing()
        target = member or ctx.author
        statuses = await self.fetch_total_status(target)
        bytes_ = await utils.pie_chart(statuses, title=f"{target.display_name}'s total status", unit="hours", outline=(0, 0, 0, 0), outline_width=10, loop=self.bot.loop)
        await ctx.send(file=discord.File(bytes_, filename="pie_status.png"))

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

    def better_offset(self, offset):
        return (offset + 11) % 24 - 11

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @checks.in_certain_guild(DISCORDPY_GUILD_ID)
    async def linestatus(self, ctx, member: discord.Member=None, offset=None):
        '''
           `>>linestatus <optional: member> <optional: offset>`
            Display line chart showing hourly status of target member.
            Default member is command invoker. Default offset target's pre-set timezone, or 0 if not set.
        '''
        await ctx.trigger_typing()
        if offset is not None:
            try:
                offset = int(offset)
            except:
                return await ctx.send("Offset should be an integer.")
            else:
                offset = self.better_offset(offset)
        target = member or ctx.author
        offset, statuses = await self.fetch_hourly_status(target, offset=offset)
        title = f"{target.display_name}'s hourly status (offset {offset:+d})"
        bytes_ = await utils.line_chart(statuses, unit_y="hours", unit_x="time\nof day", title=title, loop=self.bot.loop)
        await ctx.send(file=discord.File(bytes_, filename="line_status.png"))

    @commands.command()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    @checks.in_certain_guild(DISCORDPY_GUILD_ID)
    async def areastatus(self, ctx, member: discord.Member=None, offset=None):
        '''
           `>>areastatus <optional: member> <optional: offset>`
            Display stacked area chart showing hourly status percentage of target member.
            Default member is command invoker. Default offset target's pre-set timezone, or 0 if not set.
        '''
        await ctx.trigger_typing()
        if offset is not None:
            try:
                offset = int(offset)
            except:
                return await ctx.send("Offset should be an integer.")
            else:
                offset = self.better_offset(offset)
        target = member or ctx.author
        offset, statuses = await self.fetch_hourly_status(target, offset=offset)

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
        title = f"{target.display_name}'s hourly status (offset {offset:+d})"
        try:
            bytes_ = await utils.stacked_area_chart(draw_data, unit_y="%", unit_x="time\nof day", title=title, loop=self.bot.loop)
        except ZeroDivisionError:
            await ctx.send("I need at least 1 day worth of data to perform this command.")
        else:
            await ctx.send(file=discord.File(bytes_, filename="area_status.png"))

    @commands.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    @checks.in_certain_guild(DISCORDPY_GUILD_ID)
    async def timezone(self, ctx, offset: int):
        '''
           `>>timezone <offset>`
            Set default offset.
        '''
        offset = self.better_offset(offset)
        await self.user_data.update_one({"user_id": ctx.author.id}, {"$set": {"timezone": offset}})
        await ctx.send(f"Default offset has been set to {offset:+d}")

    async def on_command_completion(self, ctx):
        cmd = ctx.command.qualified_name
        self.command_run_count[cmd] = self.command_run_count.get(cmd, 0) + 1
        await self.command_data.update_one({"name": cmd}, {"$inc": {"total_count": 1}}, upsert=True)

    @commands.command(hidden=True)
    async def topcmd(self, ctx):
        all_cmds = sorted(list(self.command_run_count.items()), key=lambda x: x[1], reverse=True)

        embed = discord.Embed(title="Commands run")
        total = (x[1] for x in all_cmds)
        embed.add_field(name="Total", value=f"{sum(total)}", inline=False)

        top = []
        rest = []
        for cmd in all_cmds:
            if len(top) >= 3:
                rest.append(cmd)
            else:
                top.append(cmd)

        top_cmd_txt = "\n".join((f"{i+1}\u20e3 {x[0]} - {x[1]} times" for i, x in enumerate(top)))
        the_rest = ", ".join((f"{x[0]} ({x[1]})" for x in rest))
        the_rest_pages = utils.split_page(the_rest, 1000, check=lambda x: x==",", fix="")
        embed.add_field(name="Top commands", value=top_cmd_txt, inline=False)
        embed.add_field(name="Other", value=the_rest_pages[0], inline=False)

        await ctx.send(embed=embed)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Statistics(bot))
