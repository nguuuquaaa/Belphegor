import discord
from discord.ext import commands
import time
import asyncio
from .utils import config
import json

#==================================================================================================================================================

class RemindEvent:
    def __init__(self, event_time, wait_time, member, channel, remind_text):
        self.event_time = event_time
        self.wait_time = wait_time
        self.member = member
        self.channel = channel
        self.remind = remind_text

    def to_dict(self):
        return {"event_time": self.event_time, "wait_time": self.wait_time, "member_id": self.member.id, "channel_id": self.channel.id, "remind": self.remind}

    @classmethod
    def from_data(cls, bot, data):
        channel = bot.get_channel(data["channel_id"])
        member = discord.utils.find(lambda m:m.id==data["member_id"], channel.guild.members)
        return cls(data["event_time"], data["wait_time"], member, channel, data["remind_text"])

#==================================================================================================================================================

class RemindBot:
    def __init__(self, bot):
        self.bot = bot
        self.active = asyncio.Event()
        self.reminder = bot.loop.create_task(self.check_till_eternity())
        self.all_events = []
        try:
            with open(f"{config.data_path}misc/remind/all_events.json", encoding="utf-8") as file:
                self.all_events = [RemindEvent.from_data(bot, d) for d in json.load(file)]
        except Exception as e:
            print(e)
            pass

    async def check_till_eternity(self):
        events = self.all_events
        while True:
            if not events:
                self.active.clear()
                await self.active.wait()
            time_left = events[0].event_time - time.time()
            if time_left > 61:
                await asyncio.sleep(60)
            elif time_left < 0:
                events.pop(0)
                with open(f"{config.data_path}misc/remind/all_events.json", "w+", encoding="utf-8") as file:
                    json.dump([e.to_dict() for e in events], file, indent="4", ensure_ascii=False)
            else:
                event = events.pop(0)
                with open(f"{config.data_path}misc/remind/all_events.json", "w+", encoding="utf-8") as file:
                    json.dump([e.to_dict() for e in events], file, indent="4", ensure_ascii=False)
                self.bot.loop.create_task(self.start_reminder(event))

    async def start_reminder(self, remind_event):
        await asyncio.sleep(remind_event.event_time-time.time())
        await remind_event.channel.send(f"{remind_event.member.mention}, {remind_event.wait_time} ago you asked me to remind you: \"{remind_event.remind}\"")

    @commands.group(aliases=["remindme"])
    async def remind(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @remind.command(name="in")
    async def remind_in(self, ctx, after, *, remind_text):
        after = after.replace("d", "d-").replace("h", "h-").replace("m", "m-").replace("s", "s-").split("-")
        wt = [(0, 0), (0, 0), (0, 0), (0, 0)]
        for t in after:
            if "d" in t:
                wt[0] = ("day", int(t.replace("d", "")))
            elif "h" in t:
                wt[1] = ("hour", int(t.replace("h", "")))
            elif "m" in t:
                wt[2] = ("minute", int(t.replace("m", "")))
            elif "s" in t:
                wt[3] = ("second", int(t.replace("s", "")))
        wait_time = wt[0][1] * 86400 + wt[1][1] * 3600 + wt[2][1] * 60 + wt[3][1]
        text_body = []
        for item in wt:
            if item[1] > 1:
                text_body.append(f"{item[1]} {item[0]}s")
            elif item[1] == 1:
                text_body.append(f"{item[1]} {item[0]}")
        wt = " ".join(text_body)
        self.all_events.append(RemindEvent(time.time()+wait_time, wt, ctx.author, ctx.channel, remind_text))
        self.all_events.sort(key=lambda e:e.event_time)
        self.active.set()
        with open(f"{config.data_path}misc/remind/all_events.json", "w+", encoding="utf-8") as file:
            json.dump([e.to_dict() for e in self.all_events], file, indent=4, ensure_ascii=False)
        await ctx.send(f"Got it, I'll remind you {wt} later.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(RemindBot(bot))
