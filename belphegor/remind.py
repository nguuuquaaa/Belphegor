import discord
from discord.ext import commands
import time
from datetime import datetime, timezone
import asyncio
from . import utils
import json
import re

#==================================================================================================================================================

class Remind:
    def __init__(self, bot):
        self.bot = bot
        self.active = asyncio.Event()
        self.event_list = bot.db.remind_event_list
        self.reminder = bot.loop.create_task(self.check_till_eternity())

    def cleanup(self):
        self.reminder.cancel()

    async def check_till_eternity(self):
        events = self.event_list
        while True:
            closest_event = await events.find_one({}, sort=[("event_time", 1)])
            if closest_event is None:
                self.active.clear()
                await self.active.wait()
            else:
                remind_event = closest_event.copy()
                remind_event["event_time"] = remind_event["event_time"].replace(tzinfo=timezone.utc)
                time_left = (remind_event["event_time"] - utils.now_time()).total_seconds()
                if time_left > 65:
                    await asyncio.sleep(60)
                else:
                    if time_left > 0:
                        self.bot.loop.create_task(self.start_reminder(remind_event, time_left))
                    else:
                        await self.do_remind(remind_event, "Oops I forgot to tell you but ")
                    await events.delete_one(closest_event)

    async def do_remind(self, remind_event, optional_text=""):
        wait_time_text = utils.seconds_to_text(remind_event["wait_time"])
        channel = self.bot.get_channel(remind_event["channel_id"])
        member = channel.guild.get_member(remind_event["author_id"])
        await channel.send(f"{optional_text}{member.mention}, {wait_time_text} ago you asked me to remind you: \"{remind_event['text']}\"")

    async def start_reminder(self, remind_event, time_left):
        await asyncio.sleep(time_left)
        await self.do_remind(remind_event)

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
            Use ~~machine~~human-readable time format to set timer, i.e `in 10h` or `in 10 days`.
        '''
        try:
            remind_text, wait_time = utils.extract_time(remind_text)
        except:
            return await ctx.send("Time too large.")
        else:
            seconds = wait_time.total_seconds()
        if seconds > 0:
            new_event = {
                "wait_time":  seconds,
                "event_time": utils.now_time() + wait_time,
                "author_id": ctx.author.id,
                "channel_id": ctx.channel.id,
                "text": remind_text
            }
            if seconds <= 65:
                self.bot.loop.create_task(self.start_reminder(new_event, seconds))
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
            Display all your reminders.
        '''
        self_events = []
        async for ev in self.event_list.find({"author_id": ctx.author.id}, sort=[("event_time", 1)]):
            ev["event_time"] = ev["event_time"].replace(tzinfo=timezone.utc)
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
            Delete a reminder.
        '''
        self_events = [ev async for ev in self.event_list.find({"author_id": ctx.author.id}, sort=[("event_time", 1)])]
        if 0 < position <= len(self_events):
            sentences = {
                "initial":  "Delet this?",
                "yes":      "Deleted.",
                "no":       "Cancelled deleting.",
                "timeout":  "Timeout, cancelled deleting."
            }
            check = await ctx.yes_no_prompt(sentences)
            if check:
                await self.event_list.delete_one(self_events[position-1])
        else:
            await ctx.send("Position out of range.")

    @commands.command(hidden=True)
    async def ftime(self, ctx, *, phrase):
        try:
            text, time_ext = utils.extract_time(phrase)
            time_ext = time_ext.total_seconds()
        except:
            return await ctx.send("Time too large.")
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
