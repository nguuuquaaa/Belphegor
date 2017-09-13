import discord
from discord.ext import commands
import time
from datetime import datetime, timezone
import asyncio
from .utils import config, format, checks
import json
import re

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
        return cls(data["event_time"], data["wait_time"], member, channel, data["remind"])

#==================================================================================================================================================

class RemindBot:
    def __init__(self, bot):
        self.bot = bot
        self.active = asyncio.Event()
        try:
            with open(f"{config.data_path}/misc/all_events.json", encoding="utf-8") as file:
                self.all_events = [RemindEvent.from_data(bot, d) for d in json.load(file)]
        except Exception as e:
            print(e)
            self.all_events = []
        self.reminder = bot.loop.create_task(self.check_till_eternity())

    @commands.command()
    @checks.owner_only()
    async def unload_remind(self, ctx):
        self.reminder.cancel()
        self.bot.unload_extension("belphegor.remind")
        await ctx.message.add_reaction("\u2705")

    async def check_till_eternity(self):
        events = self.all_events
        try:
            while True:
                if not events:
                    self.active.clear()
                    await self.active.wait()
                time_left = events[0].event_time - time.time()
                if time_left > 61:
                    await asyncio.sleep(60)
                else:
                    event = events.pop(0)
                    with open(f"{config.data_path}/misc/all_events.json", "w+", encoding="utf-8") as file:
                        json.dump([e.to_dict() for e in events], file, indent=4, ensure_ascii=False)
                    if time_left > 0:
                        self.bot.loop.create_task(self.start_reminder(event))
        except asyncio.CancelledError:
            return

    async def start_reminder(self, remind_event):
        await asyncio.sleep(remind_event.event_time-time.time())
        await remind_event.channel.send(f"{remind_event.member.mention}, {remind_event.wait_time} ago you asked me to remind you: \"{remind_event.remind}\"")

    @commands.group(aliases=["reminder"])
    async def remind(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @remind.command(name="me")
    async def remind_me(self, ctx, *, remind_text):
        wait_time = format.extract_time(remind_text)
        if wait_time > 0:
            if wait_time > 1000000000:
                return await ctx.send("Time too large.")
            wait_text = format.seconds_to_text(wait_time)
            self.all_events.append(RemindEvent(time.time()+wait_time, wait_text, ctx.author, ctx.channel, remind_text))
            self.all_events.sort(key=lambda e:e.event_time)
            self.active.set()
            with open(f"{config.data_path}/misc/all_events.json", "w+", encoding="utf-8") as file:
                json.dump([e.to_dict() for e in self.all_events], file, indent=4, ensure_ascii=False)
            await ctx.send(f"Got it, I'll remind you {wait_text} later.")
        else:
            await ctx.send("Can't read the time.")

    @remind.command(name="list")
    async def remind_list(self, ctx):
        self_events = []
        for event in self.all_events:
            if event.member.id == ctx.author.id:
                self_events.append(event)
        description = []
        cur_time = time.time()
        for i, e in enumerate(self_events):
            if i%20 == 0:
                description.append(f"{i+1}. ***{e.remind}***\n  In {format.seconds_to_text(int(e.event_time-cur_time))}")
            else:
                description[i//20] = f"{description[i//20]}\n\n{i+1}. ***{e.remind}***\n  In {format.seconds_to_text(int(e.event_time-cur_time))}"
        max_page = len(description)
        embed = discord.Embed(title=f"All reminders for {ctx.author.display_name}", colour=discord.Colour.dark_teal())

        def data(page):
            embed.description = f"{description[page]}\n\n(Page {page+1}/{max_page})" if description else "None."
            embed.set_footer(text=datetime.now(timezone.utc).astimezone().strftime("%a, %Y-%m-%d at %I:%M:%S %p, GMT%z"))
            return embed

        await format.embed_page(ctx, max_page=max_page, embed=data)

    @remind.command(name="delete")
    async def remind_delete(self, ctx, position:int):
        self_events = []
        for event in self.all_events:
            if event.member.id == ctx.author.id:
                self_events.append(event)
        if 0 < position <= len(self_events):
            message = await ctx.send(f"Delet this?")
            e_emoji = ("\u2705", "\u274c")
            for e in e_emoji:
                await message.add_reaction(e)
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=lambda r,u:r.emoji in e_emoji and u.id==ctx.author.id and r.message.id==message.id, timeout=60)
                if reaction.emoji == "\u2705":
                    self.all_events.remove(self_events[position-1])
                    with open(f"{config.data_path}/misc/all_events.json", "w+", encoding="utf-8") as file:
                        json.dump([e.to_dict() for e in self.all_events], file, indent=4, ensure_ascii=False)
                    await message.edit(content=f"Deleted.")
                else:
                    await message.edit(content="Cancelled deleting.")
            except asyncio.TimeoutError:
                await message.edit(content="Timeout, cancelled deleting.")
            try:
                await message.clear_reactions()
            except:
                pass
        else:
            await ctx.send("Position out of range.")

    @commands.command()
    async def ftime(self, ctx, *, phrase):
        i = format.extract_time(phrase)
        if i:
            await ctx.send(format.seconds_to_text(i))
        else:
            await ctx.send("Can't extract time.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(RemindBot(bot))
