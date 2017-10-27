import discord
from discord.ext import commands
import time
from datetime import datetime, timezone
import asyncio
from . import utils
import json
import re

#==================================================================================================================================================

class RemindBot:
    def __init__(self, bot):
        self.bot = bot
        self.active = asyncio.Event()
        self.event_list = bot.db.remind_event_list
        self.reminder = bot.loop.create_task(self.check_till_eternity())

    async def check_till_eternity(self):
        events = self.event_list
        try:
            while True:
                closest_event = await events.find_one({}, sort=[("event_time", 1)])
                if closest_event is None:
                    self.active.clear()
                    await self.active.wait()
                else:
                    remind_event = closest_event.copy()
                    remind_event["create_time"] = remind_event["create_time"].replace(tzinfo=timezone.utc)
                    remind_event["event_time"] = remind_event["event_time"].replace(tzinfo=timezone.utc)
                    time_left = (remind_event["event_time"] - utils.now_time()).total_seconds()
                    print(time_left)
                    if time_left > 65:
                        await asyncio.sleep(60)
                    else:
                        if time_left > 0:
                            self.bot.loop.create_task(self.start_reminder(remind_event, time_left))
                        else:
                            await self.do_remind(remind_event, "Oops I forgot to tell you but ")
                        await events.delete_one(closest_event)
        except asyncio.CancelledError:
            return

    async def do_remind(self, remind_event, optional_text=""):
        wait_time = utils.now_time() - remind_event["create_time"]
        wait_time_text = utils.seconds_to_text(wait_time.total_seconds())
        channel = self.bot.get_channel(remind_event["channel_id"])
        member = channel.guild.get_member(remind_event["author_id"])
        await channel.send(f"{optional_text}{member.mention}, {wait_time_text} ago you asked me to remind you: \"{remind_event['text']}\"")

    async def start_reminder(self, remind_event, time_left):
        await asyncio.sleep(time_left)
        await self.do_remind(remind_event)

    @commands.group(aliases=["reminder"])
    async def remind(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @remind.command(name="me")
    async def remind_me(self, ctx, *, remind_text):
        try:
            wait_time = utils.extract_time(remind_text)
            seconds = wait_time.total_seconds()
        except:
            return await ctx.send("Time too large.")
        if seconds > 0:
            create_time = utils.now_time()
            new_event = {
                "create_time":  create_time,
                "event_time": create_time + wait_time,
                "author_id": ctx.author.id,
                "channel_id": ctx.channel.id,
                "text": remind_text
            }
            if seconds < 65:
                self.bot.loop.create_task(self.start_reminder(new_event, seconds))
            else:
                await self.event_list.insert_one(new_event)
                self.active.set()
            await ctx.send(f"Got it, I'll remind you {utils.seconds_to_text(seconds)} later.")
        else:
            await ctx.send("Can't read the time.")

    @remind.command(name="list")
    async def remind_list(self, ctx):
        self_events = []
        async for ev in self.event_list.find({"author_id": ctx.author.id}, sort=[("event_time", 1)]):
            ev["create_time"] = ev["create_time"].replace(tzinfo=timezone.utc)
            ev["event_time"] = ev["event_time"].replace(tzinfo=timezone.utc)
            self_events.append(ev)
        description = []
        cur_time = utils.now_time()
        embeds = []
        max_page = (len(self_events) - 1) // 5 + 1
        for index in range(0, len(self_events), 5):
            desc = "\n\n".join([
                f"`{i+1}.` ***{e['text']}***\n  In {utils.seconds_to_text((e['event_time']-cur_time).total_seconds())}"
                for i, e in enumerate(self_events[index:index+5])
            ])
            embed = discord.Embed(
                title=f"All reminders for {ctx.author.display_name}",
                description=f"{desc}\n\n(Page {index//5+1}/{max_page})"
            )
            embed.set_footer(text=utils.format_time(cur_time))
            embeds.append(embed)
        await ctx.embed_page(embeds)

    @remind.command(name="delete")
    async def remind_delete(self, ctx, position:int):
        self_events = [ev async for ev in self.event_list.find({"author_id": ctx.author.id}, sort={"event_time": 1})]
        if 0 < position <= len(self_events):
            sentences = {
                "initial":  "Delet this?",
                "yes":      "Deleted.",
                "no":       "Cancelled deleting.",
                "timeout":  "Timeout, cancelled deleting."
            }
            check = await ctx.yes_no_prompt(sentences)
            await self.event_list.delete_one(self_events[position-1])
        else:
            await ctx.send("Position out of range.")

    @commands.command()
    async def ftime(self, ctx, *, phrase):
        try:
            i = utils.extract_time(phrase).total_seconds()
        except:
            await ctx.send("Time too large.")
        if i > 0:
            await ctx.send(utils.seconds_to_text(i))
        else:
            await ctx.send("Can't extract time.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(RemindBot(bot))
