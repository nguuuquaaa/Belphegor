import discord
from discord.ext import commands
import time
from datetime import datetime, timedelta
import pytz
import asyncio
from . import utils
import json
import re
import weakref

#==================================================================================================================================================

class Remind:
    def __init__(self, bot):
        self.bot = bot
        self.active = asyncio.Event()
        self.event_list = bot.db.remind_event_list
        self.reminder = weakref.ref(bot.loop.create_task(self.check_till_eternity()))

    def __unload(self):
        self.reminder().cancel()

    async def check_till_eternity(self):
        while True:
            cur = self.event_list.find().sort("event_time").limit(1)
            result = await cur.to_list(length=1)
            self.active.clear()
            if not result:
                await self.active.wait()
            else:
                remind_event = result[0]
                remind_event["event_time"] = remind_event["event_time"].replace(tzinfo=pytz.utc)
                time_left = (remind_event["event_time"] - utils.now_time()).total_seconds()
                if time_left > 60:
                    try:
                        await asyncio.wait_for(self.active.wait(), timeout=time_left-60)
                    except asyncio.TimeoutError:
                        pass
                    else:
                        continue

                self.start_reminder(remind_event)
                await asyncio.shield(self.event_list.delete_one({"_id": remind_event["_id"]}))

    def start_reminder(self, remind_event):
        async def reminder():
            time_left = remind_event["event_time"] - utils.now_time()
            time_left_seconds = time_left.total_seconds()
            if time_left_seconds > 0:
                await asyncio.sleep(time_left.total_seconds())
                add_text = ""
                delta = 0
            else:
                add_text = "Oops, I just realized I forgot to tell you, tehepero (ᵒ ڡ <)๑⌒☆\n"
                delta = time_left_seconds

            wait_time_text = utils.seconds_to_text(remind_event["wait_time"]+delta)
            channel = self.bot.get_channel(remind_event["channel_id"])
            member = channel.guild.get_member(remind_event["author_id"])
            if channel and member:
                await channel.send(f"{add_text}{member.mention}, {wait_time_text} ago you asked me to remind you: \"{remind_event['text']}\"")

        self.bot.loop.create_task(reminder())

    @commands.group(aliases=["reminder"])
    async def remind(self, ctx):
        '''
            `>>remind`
            Base command. Does nothing, but with subcommands can be used to set and view reminders.
        '''
        if ctx.invoked_subcommand is None:
            pass

    @remind.command(name="me")
    async def remind_me(self, ctx, *, remind_text):
        '''
            `>>remind me <reminder>`
            Set a reminder.
            Use ~~machine~~human-readable time format to set timer, i.e `in 10h` or `10 days 5 hours`.
        '''
        try:
            remind_text, wait_time = utils.extract_time(remind_text)
        except OverflowError:
            return await ctx.send("Time too large.")
        else:
            seconds = wait_time.total_seconds()
        if seconds > 0:
            now_time = utils.now_time()
            new_event = {
                "event_time": now_time + wait_time,
                "wait_time": seconds,
                "author_id": ctx.author.id,
                "channel_id": ctx.channel.id,
                "text": remind_text
            }
            if seconds <= 60:
                self.start_reminder(new_event)
            else:
                await self.event_list.insert_one(new_event)
                self.active.set()
            await ctx.send(f"Got it, I'll remind you {utils.seconds_to_text(seconds)} later.")
        else:
            await ctx.send("Can't read the time.")

    @remind.command(name="list")
    async def remind_list(self, ctx):
        '''
            `>>remind list`
            Display all your reminders, except those that occur in less than 1 minute.
        '''
        self_events = []
        async for ev in self.event_list.find({"author_id": ctx.author.id}).sort("event_time"):
            ev["event_time"] = ev["event_time"].replace(tzinfo=pytz.utc)
            self_events.append(ev)
        description = []
        cur_time = utils.now_time()
        embeds = utils.embed_page_format(
            self_events, 5,
            title=f"All reminders for {ctx.author.display_name}",
            description=lambda i, x: f"`{i+1}.` \"{x['text']}\"\n  In {utils.seconds_to_text((x['event_time']-cur_time).total_seconds())}",
            footer=utils.format_time(cur_time)
        )
        if embeds:
            await ctx.embed_page(embeds)
        else:
            await ctx.send("You have no reminder.")

    @remind.command(name="delete")
    async def remind_delete(self, ctx, position: int):
        '''
            `>>remind delete <position>`
            Delete a reminder. Position is based on `>>remind list` command.
        '''
        self_events = [ev async for ev in self.event_list.find({"author_id": ctx.author.id}).sort("event_time")]
        if 0 < position <= len(self_events):
            sentences = {
                "initial":  "Delet this?",
                "yes":      "Deleted.",
                "no":       "Cancelled deleting.",
                "timeout":  "Timeout, cancelled deleting."
            }
            check = await ctx.yes_no_prompt(sentences)
            if check:
                await self.event_list.delete_one({"_id": self_events[position-1]["_id"]})
        else:
            await ctx.send("Position out of range.")

    @commands.command(hidden=True)
    async def ftime(self, ctx, *, phrase):
        try:
            text, time_ext = utils.extract_time(phrase)
        except OverflowError:
            return await ctx.send("Time too large.")
        else:
            time_ext = time_ext.total_seconds()
        if time_ext > 0:
            await ctx.send(utils.seconds_to_text(time_ext))
        else:
            await ctx.send("Can't extract time.")

    @commands.command(aliases=["time"])
    async def currenttime(self, ctx):
        '''
            `>>currenttime`
            Show current time in UTC.
        '''
        cur_time = utils.now_time()
        await ctx.send(utils.format_time(cur_time))

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Remind(bot))
