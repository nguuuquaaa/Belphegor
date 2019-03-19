import discord
from discord.ext import commands
from . import utils
from .utils import config, modding
import json
import re
import datetime
import pytz
import inspect
import os
import sys
import collections

#==================================================================================================================================================

ISO_DATE = re.compile(r"([0-9]{4})\-([0-9]{2})\-([0-9]{2})T([0-9]{2})\:([0-9]{2})\:([0-9]{2})Z")
ENGLISH = {
    1: "once",
    2: "twice",
    3: "thrice"
}

def _return_embed(e):
    def func():
        return e
    return func

#==================================================================================================================================================

class Help(commands.Cog):
    '''
        Help and utility commands.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")
        test_guild = self.bot.get_guild(config.TEST_GUILD_ID)
        self.otogi_guild = self.bot.get_guild(config.OTOGI_GUILD_ID)
        creampie_guild = self.bot.get_guild(config.CREAMPIE_GUILD_ID)
        self.emojis = {}
        for emoji_name in ("mochi", "ranged"):
            self.emojis[emoji_name] = discord.utils.find(lambda e: e.name==emoji_name, creampie_guild.emojis)
        for emoji_name in ("hu", "python"):
            self.emojis[emoji_name] = discord.utils.find(lambda e: e.name==emoji_name, test_guild.emojis)
        bot.loop.create_task(self.get_webhook())
        self.setup_help()

    def setup_help(self):
        infodump = {
            None: {
                "emoji":    "\u21a9",
                "desc":     "[Support server but not really active](https://discord.gg/qnavjMy)",
                "thumb":    self.bot.user.avatar_url,
                "footer":   "Universal prefix: bot mention \u2022 Default prefix: >>",
                "fields":   {
                    "Categories" : [
                        [
                            "`>>help` - Show this message\n"
                            f"{self.emojis['mochi']} Otogi: Spirit Agents stuff\n"
                            f"{self.emojis['hu']} PSO2 stuff\n"
                            "\U0001f3b2 Play board games\n"
                            "\U0001f5bc Image search/random\n"
                            "\U0001f3b5 Music\n"
                            "\U0001f4d4 Role/server stuff\n"
                            "\U0001f3f7 Tag and sticker\n"
                            "\u2699 Miscellaneous commands\n\n"
                            "You can also use `>>help help` to get a rough idea of how to use this help and `>>help <full command name>` to get specific command usage."
                        ]
                    ]
                }
            },
            "Otogi": {
                "emoji":    self.emojis["mochi"],
                "desc":
                    "Data taken from [Otogi Wikia](http://otogi.wikia.com/) and [Otogi Effective Stats Spreadsheet](https://docs.google.com/spreadsheets/d/1oJnQ5TYL5d9LJ04HMmsuXBvJSAxqhYqcggDZKOctK2k/edit#gid=0)",
                "thumb":    getattr(self.otogi_guild, "icon_url", None),
                "footer":   None,
                "fields":   {}
            },
            "PSO2": {
                "emoji":    self.emojis["hu"],
                "desc":
                    "Data taken from [swiki](http://pso2es.swiki.jp/), [Arks-Visiphone](http://pso2.arks-visiphone.com/wiki/Main_Page) and DB Kakia.\n\n"
                    "Special thanks to ACF for letting me use his EQ API.\n"
                    "`>>set eq` - Set EQ alert channel\n"
                    "`>>set eqmini` - EQ alert, but less spammy\n"
                    "`>>unset eq` - Unset EQ alert channel",
                "thumb":    "http://i.imgur.com/aNAG34t.jpg",
                "footer":   None,
                "fields":   {}
            },
            "Games": {
                "emoji":    "\U0001f3b2",
                "desc":
                    "Mostly under construction, but you can play games with your fellow server members.\n"
                    "Each game has their own set of commands.",
                "thumb":    None,
                "footer":   None,
                "fields":   {}
            },
            "Image": {
                "emoji":    "\U0001f5bc",
                "desc":
                    "Get random picture from an image board.\n"
                    "Or get image sauce. Everyone loves sauce.",
                "thumb":    None,
                "footer":   None,
                "fields":   {}
            },
            "Music": {
                "emoji":    "\U0001f3b5",
                "desc":     "So many music bots out there but I want to have my own, so here it is.",
                "thumb":    None,
                "footer":   None,
                "fields":   {}
            },
            "Guild": {
                "emoji":    "\U0001f4d4",
                "desc":
                    "Server-related commands.\n"
                    "Cannot be used in DM, obviously.",
                "thumb":    None,
                "footer":   None,
                "fields":   {}
            },
            "Tag & sticker": {
                "emoji":    "\U0001f3f7",
                "desc":
                    "A tag is a shortcut text.\n"
                    "Sometimes you want to copy-paste a goddamn long guide or so (it sucks), but you can just put into a tag with short name then call it later.\n"
                    "Tags are server-specific.\n\n"
                    "A sticker is just a fancy tag specialized around image.\n"
                    "Use $stickername anywhere admidst message to trigger sticker send.\n"
                    "Only one sticker shows up per message.\n"
                    "Sticker is universal server-wise.",
                "thumb":    None,
                "footer":   None,
                "fields":   {}
            },
            "Misc": {
                "emoji":    "\u2699",
                "desc":     None,
                "thumb":    None,
                "footer":   None,
                "fields":   {}
            }
        }

        bot = self.bot

        command_set = set()
        for command in (cmd for cmd in bot.all_commands.values() if not (cmd in command_set or command_set.add(cmd))):
            try:
                category = command.category
            except AttributeError:
                continue

            field = command.field
            brief = command.brief
            paragraph = command.paragraph

            embed_info = infodump[category]["fields"]
            if field in embed_info:
                field_info = embed_info[field]
            else:
                field_info = []
                embed_info[field] = field_info
            while paragraph + 1 > len(field_info):
                field_info.append([])

            paragraph_info = field_info[paragraph]

            usage = ", ".join((f"`>>{n}`" for n in sorted((command.name, *command.aliases), key=lambda x: len(x))))
            if brief:
                paragraph_info.append(f"{usage} - {brief}")
            else:
                paragraph_info.append(usage)

            for subcommand in getattr(command, "commands", ()):
                try:
                    sub_category = subcommand.category
                except AttributeError:
                    continue
                subparagraph = subcommand.paragraph
                while subparagraph + 1 > len(field_info):
                    field_info.append([])
                paragraph_info = field_info[subparagraph]
                paragraph_info.append(f"\u2517 `{subcommand.name}` - {subcommand.brief}")

        paging = utils.Paginator([])
        for category, data in infodump.items():
            if category is None:
                title = f"{self.emojis['ranged']} {self.bot.user}"
            else:
                title = f"{data['emoji']} {category}"
            embed = discord.Embed(title=title, description=data["desc"] or discord.Embed.Empty, colour=discord.Colour.teal())
            for name, field_info in data["fields"].items():
                total = ("\n".join(p) for p in field_info if p)
                embed.add_field(name=name, value="\n\n".join(total), inline=False)

            thumb = data["thumb"]
            if thumb:
                embed.set_thumbnail(url=thumb)

            footer = data["footer"]
            if footer:
                embed.set_footer(text=footer)

            paging.set_action(data["emoji"], _return_embed(embed))

        self.help_paging = paging

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.command.name == "reload":
            self.setup_help()

    @commands.command()
    async def help(self, ctx, *, command_name=None):
        '''
            `>>help <optional: command>`
            Display help. Navigating by using reactions.

            If you see this
            \u200b    `>>command` - this is
            \u200b    \u2517 `sub1` - an
            \u200b    \u2517 `sub2` - example
            Then it means `sub1` and `sub2` are subcommands of `command` and the usage is `>>command` for the parent and `>>command sub1` and `>>command sub2` for subcommands. This usage also reflects in specific command help.


            Specific command usage usually has this format
            ```>>command name <argument> <optional: argument> <keyword: _|arg|ument>```
            - `>>` is the default prefix of Belphegor, some servers may not have this due to custom prefixes.
            - `command name` and `<argument>` are self-explanatory.
            - `<optional: argument>` is just argument with a default value.
            Arguments and optional arguments are positional, which means you must enter input value in order, and if you want to change the last optional argument you must enter the value for all previous arguments too.


            - `<keyword: _|arg|ument>` is argument in the form of `name=value`.
            `_`, `arg` and `ument` are name, and `_` means you can omit the name part and just enter `value`. If value contains whitespaces, you must enclosed it in quote characters.
            Here's a list of all quote characters: `" "`, `‘ ’`, `‚ ‛`, `“ ”`, `„ ‟`, `⹂ ⹂`, `「 」`, `『 』`, `〝 〞`, `﹁ ﹂`, `﹃ ﹄`, `＂ ＂`, `｢ ｣`, `« »`, `‹ ›`, `《 》`, `〈 〉`
            If value contains quote characters you must enclosed it in another quote characters.
            Keyword arguments are non-positional, which mean you can place it in any order whatsoever.
        '''
        if command_name is None:
            await self.help_paging.navigate(ctx, timeout=120)
        else:
            command = self.bot.get_command(command_name)
            if command:
                if not command.hidden:
                    embed = discord.Embed(colour=discord.Colour.teal())
                    embed.add_field(name="Parent command", value=f"`{command.full_parent_name}`" if command.full_parent_name else "None")
                    embed.add_field(name="Name", value=f"`{command.name}`")
                    embed.add_field(name="Aliases", value=", ".join((f"`{a}`" for a in command.aliases)) if command.aliases else "None")
                    embed.add_field(
                        name="Subcommands",
                        value=", ".join((f"`{s.name}`" for s in getattr(command, "commands", ()) if not s.hidden)) or "None",
                        inline=False
                    )
                    all_checks = set(command.checks)
                    cmd = command
                    while cmd.parent:
                        cmd = cmd.parent
                        if not getattr(cmd, "invoke_without_command", False):
                            all_checks.update(cmd.checks)
                    ch = ", ".join((c.__name__[6:].replace("guild", "server").replace("_", " ") for c in all_checks))
                    if ch:
                        ch = f"Limit: {ch}"
                    cooldown = command._buckets._cooldown
                    if cooldown:
                        cd = f"Rate: {ENGLISH.get(cooldown.rate, f'{cooldown.rate} times')} per {utils.seconds_to_text(cooldown.per)} (each {cooldown.type.name.replace('guild', 'server')})"
                    else:
                        cd = None
                    embed.add_field(
                        name="Restriction",
                        value="\n".join(filter(None, (ch, cd))) or "None",
                        inline=False
                    )
                    if command.help:
                        usage = command.help.partition("\n")
                        things = usage[2].split("\n\n\n")
                        if len(things) > 1:
                            embed.add_field(name="Usage", value=f"```\n{usage[0].strip('`')}\n```\n{things[0]}", inline=False)
                            for thing in things[1:]:
                                embed.add_field(name="\u200b", value=f"\u200b{thing}", inline=False)
                        else:
                            usage = f"``{usage[0]}``\n{usage[2]}"
                            embed.add_field(name="Usage", value=usage, inline=False)
                    else:
                        embed.add_field(name="Usage", value="Not yet documented.", inline=False)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"Command `{command_name}` isn't available to public.")
            else:
                await ctx.send(f"Command `{command_name}` doesn't exist.")

    async def get_webhook(self):
        feedback_channel = self.bot.get_channel(config.FEEDBACK_CHANNEL_ID)
        all_webhooks = await feedback_channel.webhooks()
        self.feedback_wh = all_webhooks[0]

    @modding.help(brief="Feedback anything", category=None, field="Other", paragraph=0)
    @commands.command()
    async def feedback(self, ctx, *, content):
        '''
            `>>feedback <anything goes here>`
            Feedback.
            Bugs, inconvenience or suggestion, all welcomed.
        '''
        embed = discord.Embed(title=ctx.author.id, description=content)
        await self.feedback_wh.execute(embed=embed, username=str(ctx.author), avatar_url=ctx.author.avatar_url_as(format="png"))
        await ctx.confirm()

    @modding.help(brief="Bot info", category=None, field="Other", paragraph=0)
    @commands.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def about(self, ctx):
        '''
            `>>about`
            Bot info.
        '''
        await ctx.trigger_typing()
        bot = self.bot
        owner = bot.get_user(config.OWNER_ID)
        bytes_ = await utils.fetch(
            bot.session,
            "https://api.github.com/repos/nguuuquaaa/Belphegor/commits",
            headers={"User-Agent": owner.name}
        )
        now_time = utils.now_time()
        commits = json.loads(bytes_)
        desc = []
        for c in commits[:3]:
            m = ISO_DATE.fullmatch(c["commit"]["committer"]["date"])
            dt = ""
            if m:
                committed_time = datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6)), 0, pytz.utc)
                delta = int((now_time - committed_time).total_seconds())
                if delta >= 86400:
                    dt = f" ({delta//86400}d ago)"
                elif delta % 86400 >= 3600:
                    dt = f" ({delta//3600}h ago)"
                elif delta % 3600 >= 60:
                    dt = f" ({delta//60}m ago)"
                else:
                    dt = f" ({delta%60}s ago)"
            desc.append(f"[`{c['sha'][:7]}`]({c['html_url']}) {c['commit']['message']}{dt}")
        embed = discord.Embed(
            description=
                f"{bot.user.name} is a multi-purpose bot with lots of experimental and unnecessary commands.\n"
                "Also PSO2 and Otogi stuff. These works at least.",
            colour=discord.Colour.blue()
        )
        embed.set_author(name=str(bot.user), icon_url=bot.user.avatar_url)
        embed.add_field(name="Lastest changes", value="\n".join(desc), inline=False)
        embed.add_field(name="Owner", value=owner.mention if owner in getattr(ctx.guild, "members", ()) else str(owner))
        v = sys.version_info
        embed.add_field(name="Written in", value=f"{self.emojis['python']} {v.major}.{v.minor}.{v.micro}")
        embed.add_field(name="Library", value="[discord.py\\[rewrite\\]](https://github.com/Rapptz/discord.py/tree/rewrite)")
        embed.add_field(name="Created at", value=str(bot.user.created_at)[:10])
        process = bot.process
        with process.oneshot():
            cpu_percentage = process.cpu_percent(None)
            embed.add_field(name="Process", value=f"CPU: {(cpu_percentage/bot.cpu_count):.2f}%\nRAM: {(process.memory_full_info().uss/1024/1024):.2f} MBs")
        uptime = int((now_time - bot.start_time).total_seconds())
        d, h = divmod(uptime, 86400)
        h, m = divmod(h, 3600)
        m, s = divmod(m, 60)
        embed.add_field(name="Uptime", value=f"{d}d {h}h{m}m{s}s")

        embed.add_field(name="Servers", value=f"{len(bot.guilds)} servers")
        ch_count = 0
        txt_count = 0
        ctgr_count = 0
        voice_count = 0
        member_count = 0
        off_members = set()
        for g in bot.guilds:
            ch_count += len(g.channels)
            txt_count += len(g.text_channels)
            ctgr_count += len(g.categories)
            voice_count += len(g.voice_channels)
            member_count += g.member_count
            for m in g.members:
                if m.status is discord.Status.offline:
                    off_members.add(m.id)
        off_count = len(off_members)
        user_count = len(bot.users)
        embed.add_field(name="Members", value=f"{member_count} members\n{user_count} unique\n{user_count-off_count} online\n{off_count} offline")
        embed.add_field(name="Channels", value=f"{ch_count} total\n{ctgr_count} categories\n{txt_count} text channels\n{voice_count} voice channels")
        embed.set_footer(text=utils.format_time(now_time.astimezone()))

        await ctx.send(embed=embed)

    @modding.help(brief="Invite link", category=None, field="Other", paragraph=0)
    @commands.command()
    async def invite(self, ctx):
        '''
            `>>invite`
            Bot invite link.
        '''
        perms = discord.Permissions()
        perms.manage_guild = True
        perms.manage_roles = True
        perms.manage_channels = True
        perms.kick_members = True
        perms.ban_members = True
        perms.read_messages = True
        perms.send_messages = True
        perms.manage_messages = True
        perms.embed_links = True
        perms.attach_files = True
        perms.read_message_history = True
        perms.add_reactions = True
        perms.connect = True
        perms.speak = True
        perms.use_voice_activation = True
        perms.external_emojis = True

        minimal = discord.Permissions()
        minimal.read_messages = True
        minimal.send_messages = True
        minimal.embed_links = True
        minimal.attach_files = True
        minimal.add_reactions = True
        minimal.external_emojis = True

        await ctx.send(
            f"Full perms: <{discord.utils.oauth_url(ctx.me.id, perms)}>\n"
            f"Minimal: <{discord.utils.oauth_url(ctx.me.id, minimal)}>"
        )

    @commands.command()
    async def source(self, ctx, *, name=None):
        '''
            `>>source <command>`
            Get source code of <command>.
            Shamelessly copy from R. Danny.
        '''
        base_url = "https://github.com/nguuuquaaa/Belphegor"
        if not name:
            return await ctx.send(f"<{base_url}>")
        cmd = self.bot.get_command(name)
        if cmd:
            src = cmd.callback.__code__
            rpath = src.co_filename
        else:
            obj = sys.modules["belphegor"]
            for n in name.split("."):
                obj = getattr(obj, n, None)
                if not obj:
                    return await ctx.send(f"Can't find {name}")
            else:
                try:
                    src = obj.__code__
                except AttributeError:
                    src = obj
                finally:
                    rpath = inspect.getfile(src)
        try:
            lines, firstlineno = inspect.getsourcelines(src)
        except:
            return await ctx.send(f"{name} is not a function or class name")
        location = os.path.relpath(rpath).replace('\\', '/')
        final_url = f"<{base_url}/tree/master/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>"
        await ctx.send(final_url)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Help(bot))
