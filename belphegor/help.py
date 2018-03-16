import discord
from discord.ext import commands
from . import utils
from .utils import config
import json
import re
import datetime
import pytz

#==================================================================================================================================================

ISO_DATE = re.compile(r"([0-9]{4})\-([0-9]{2})\-([0-9]{2})T([0-9]{2})\:([0-9]{2})\:([0-9]{2})Z")

#==================================================================================================================================================

class Help:
    '''
    Display help.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")
        test_guild = self.bot.get_guild(config.TEST_GUILD_ID)
        self.otogi_guild = self.bot.get_guild(config.OTOGI_GUILD_ID)
        creampie_guild = self.bot.get_guild(config.CREAMPIE_GUILD_ID)
        self.emoji = {}
        for emoji_name in ("mochi", "ranged"):
            self.emoji[emoji_name] = discord.utils.find(lambda e: e.name==emoji_name, creampie_guild.emojis)
        self.emoji["hu"] = discord.utils.find(lambda e:e.name=="hu", test_guild.emojis)
        bot.loop.create_task(self.get_webhook())

    @commands.group()
    async def help(self, ctx):
        '''
            `>>help`
            Display general help.
        '''
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(title=f"{self.emoji['ranged']} {self.bot.user}", colour=discord.Colour.teal())
            embed.set_thumbnail(url=self.bot.user.avatar_url)
            embed.add_field(
                name="Categories",
                value=
                    "`>>help` - Show this message\n"
                    "      `otogi` - Otogi: Spirit Agents stuff\n"
                    "      `pso2` - PSO2 stuff\n"
                    "      `game` - Play board games\n"
                    "      `music` - Music\n"
                    "      `image` - Image search/random\n"
                    "      `server` - Role/server-specific stuff\n"
                    "      `remind` - Reminder\n"
                    "      `tag` - Text shortcut\n"
                    "      `sticker` - Custom image reactions\n"
                    "      `misc` - Miscellaneous commands\n\n",
                inline=False
            )
            embed.add_field(
                name="Other",
                value=
                    "`>>detail` - Get detailed command info\n\n"
                    "`>>invite` - Invite link\n"
                    "`>>stats` - Bot info\n"
                    "`>>feedback` - Feedback anything\n",
                inline=False
            )
            embed.add_field(
                name="None-commands",
                value=
                    "`ping` - pong\n"
                    "`\o\` - /o/\n"
                    "`/o/` - \\o\\\n",
                inline=False
            )
            embed.set_footer(text="Default prefix: >> or bot mention")
            await ctx.send(embed=embed)

    @help.command()
    async def otogi(self, ctx):
        '''
            `>>help otogi`
            Display Otogi: Secret Agents related commands.
        '''
        embed = discord.Embed(title=f"{self.emoji['mochi']} Otogi Spirit Agents", colour=discord.Colour.teal())
        try:
            embed.set_thumbnail(url=self.otogi_guild.icon_url)
        except:
            pass
        embed.add_field(
            name="Database",
            value=
                "`>>d`, `>>daemon` - Check a daemon info\n"
                "      `filter` - Find daemons with given conditions\n"
                "`>>t`, `>>trivia` - Daemon trivia stuff\n"
                "`>>p`, `>>pic` - Illustrations\n"
                "Note: Data taken from [Otogi Wikia](http://otogi.wikia.com/)\n\n"
                "`>>update` - Update database\n\n"
                "`>>nuker(s)` - Nuker rank\n"
                "`>>auto` - Auto attack rank\n"
                "`>>buffer(s)`, `>>debuffer(s)` - List of supporters\n"
                "Note: Data taken from [Otogi Effective Stats Spreadsheet](https://docs.google.com/spreadsheets/d/1oJnQ5TYL5d9LJ04HMmsuXBvJSAxqhYqcggDZKOctK2k/edit#gid=0)\n"
                "`>>gcqstr` - Guild Conquest STR rank",
            inline=False
        )
        embed.add_field(
            name="Simulation",
            value=
                "`>>ls` - ~~salt~~ Lunchtime summon simulation\n"
                "      `till` - Estimate how many summons a certain daemon\n"
                "      `pool` - Display current summon pool\n\n"
                "`>>mybox` - Show your or a player's box\n"
                "`>>lb`, `>>limitbreak` - Limit break your daemons\n\n"
                "`>>mochi` - Sell a certain daemon\n"
                "      `bulk` - Sell all daemons with given name\n"
                "      `all` - Sell all daemons with given rarity\n\n"
                "`>>gift` - Gift someone a daemon\n"
                "`>>gimme` - Ask someone to trade you a daemon",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command()
    async def pso2(self, ctx):
        '''
            `>>help pso2`
            Display PSO2 related commands.
        '''
        embed = discord.Embed(title=f"{self.emoji['hu']} PSO2", colour=discord.Colour.teal())
        embed.set_thumbnail(url="http://i.imgur.com/aNAG34t.jpg")
        embed.add_field(
            name="Database",
            value=
                "`>>c`, `>>chip` - Check a chip info\n"
                "Note: Data taken from [swiki](http://pso2es.swiki.jp/)\n\n"
                "`>>w`, `>>weapon` - Check a weapon info\n"
                "      `filter` - Find weapons with given conditions\n"
                "`>>u`, `>>unit` - Check a unit info\n"
                "Note: Data taken from [Arks-Visiphone](http://pso2.arks-visiphone.com/wiki/Main_Page)\n\n"
                "`>>i`, `>>item` - Search for items\n"
                "`>>price` - Check item price, quite outdated\n"
                "Note: Data taken from DB Kakia\n\n"
                "`>>eq` - Display EQ schedule for the next 3 hours",
            inline=False
        )
        embed.add_field(
            name="EQ Alert",
            value=
                "`>>set eq` - Set EQ alert channel\n"
                "`>>set eqmini` - EQ alert, but less spammy\n"
                "`>>unset eq` - Unset EQ alert channel\n"
                "Special thanks to ACF for letting me use his EQ API.",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command()
    async def game(self, ctx):
        '''
            `>>help game`
            Display board game commands.
        '''
        embed = discord.Embed(
            title="\U0001f3b2 Board game",
            description=
                "Mostly under construction, but you can play games with your fellow server members.\n"
                "Each game has their own set of commands.",
            colour=discord.Colour.teal()
        )
        embed.add_field(
            name="Games",
            value=
                "`>>monopoly` - Play monopoly [Currently not available]\n"
                "`>>cangua` - Play co ca ngua",
            inline=False
        )
        embed.add_field(
            name="Universal commands",
            value=
                "`>>abandon` - Abandon current game\n"
                "`>>gameover` - Ask players to end current game\n\n"
                "`>>whatgame` - Check if a member is playing game",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command()
    async def image(self, ctx):
        '''
            `>>help image`
            Dislay image commands.
        '''
        embed = discord.Embed(
            title="\U0001f5bc Random",
            description="Get random picture from an image board.\nOr get image sauce. Everyone loves sauce.",
            colour=discord.Colour.teal()
        )
        embed.add_field(
            name="Commands",
            value=
                "`>>r`, `>>random` - Base command, do nothing\n"
                "      `d`, `danbooru` - [Danbooru](https://danbooru.donmai.us)\n"
                "      `s`, `safebooru` - [Safebooru](https://safebooru.org)\n"
                "      `k`, `konachan` - [Konachan](http://konachan.net)\n"
                "      `y`, `yandere` - [Yandere](https://yande.re)\n\n"
                "      `dh`, `danbooru_h` - [NSFW Danbooru](https://danbooru.donmai.us)\n"
                "      `kh`, `konachan_h` - [NSFW Konachan](http://konachan.com)\n"
                "      `sc`, `sancom` - [NSFW Sankaku Complex](https://chan.sankakucomplex.com)\n\n"
                "`>>saucenao` - Find the sauce of an uploaded pic or url",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command()
    async def music(self, ctx):
        '''
            `>>help music`
            Display music commands.
        '''
        embed = discord.Embed(title="\U0001f3b5 Music", description="So many music bots out there but I want to have my own, so here it is.", colour=discord.Colour.teal())
        embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
        embed.add_field(
            name="Commands",
            value=
                "`>>m`, `>>music` - Base command, do nothing\n"
                f"      `j`, `join` - Have {ctx.me.display_name} join the voice channel you are\n"
                "                         currently in and play everything in queue\n"
                f"      `l`, `leave` - Have {ctx.me.display_name} leave the voice channel\n\n"
                "      `q`, `queue` - Search Youtube and queue a song\n"
                "      `p`, `playlist` - Search Youtube and queue a playlist\n\n"
                "      `i`, `info` - Display video info, default current song (position 0)\n"
                "      `ai`, `autoinfo` - Auto info display mode\n"
                "      `mi`, `manualinfo` - Manual info display mode\n\n"
                "      `t`, `toggle` - Toggle play/pause\n"
                "      `v`, `volume` - Set volume, must be between 0 and 200\n"
                "      `f`, `forward` - Fast forward, default 10 (seconds)\n"
                "      `s`, `skip` - Skip current song\n"
                "      `r`, `repeat` - Toggle repeat mode\n\n"
                "      `d`, `delete` - Delete a song from queue with given position\n"
                "      `purge` - Purge all songs from queue\n\n"
                "      `setchannel` - Change notifying channel\n"
                "      `export` - Export current queue to JSON file\n"
                "      `import` - Import JSON playlist",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command(aliases=["guild"])
    async def server(self, ctx):
        '''
            `>>help server`
            Display non-DM, server-specific commands.
        '''
        embed = discord.Embed(
            title="\U0001f4d4 Server",
            description=
                "Server specific commands.\n"
                "Cannot be used in DM, obviously.",
            colour=discord.Colour.teal()
        )
        embed.add_field(
            name="Server management",
            value=
                "`>>set`\n"
                "`>>unset`\n"
                "These 2 commands are used to set up stuff. More details in `>>detail`.\n\n"
                "`>>channelmute` - Mute a member in current channel\n"
                "`>>channelban` - Ban a member from current channel\n"
                "`>>mute` - Give a member \"Muted\" role if exists\n"
                "`>>unmute` - Remove \"Muted\" role from a member\n\n"
                "`>>kick` - Kick member\n"
                "`>>ban` - Ban member\n"
                "`>>hackban` - Ban user not in server\n"
                "`>>unban` - Unban member\n\n"
                "`>>purge` - Bulk delete messages\n"
                "`>>purgereact` - Clear reactions of messages",
            inline=False
        )
        embed.add_field(
            name="Role",
            value=
                "`>>selfrole` - Get selfrole with given name, if applicable\n"
                "      `empty` - Remove all selfroles\n"
                "      `list` - Display server selfrole pool\n"
                "      `distribution` - Pie chart showing selfrole distribution\n"
                "      `add` - Add an existed role to selfrole pool\n"
                "      `remove` - Remove a role from selfrole pool\n\n"
                "`>>creampie` - Get NSFW role, if applicable\n"
                "`>>censored` - Remove NSFW role, if applicable",
            inline=False
        )
        embed.add_field(
            name="Info",
            value=
                "`>>server`\n"
                "      `info` - Display server info\n"
                "      `prefix` - Display server (custom) prefixes\n"
                "      `icon` - Server icon\n"
                "`>>role`\n"
                "      `info` - Display role info",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command()
    async def remind(self, ctx):
        '''
            `>>help remind`
            Display reminder commands.
        '''
        embed = discord.Embed(title="\u23f0 Reminder", description="Schedule to ping you after a certain time.", colour=discord.Colour.teal())
        embed.add_field(
            name="Commands",
            value=
                "`>>remind` - Base command, do nothing\n"
                "      `me` - Set a reminder\n"
                "      `list` - Display all your reminders\n"
                "      `delete` - Delete a reminder",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command()
    async def tag(self, ctx):
        '''
            `>>help tag`
            Display tag commands.
        '''
        embed = discord.Embed(
            title="\U0001f3f7 Tag",
            description=
                "Shortcut text.\n"
                "Sometimes you want to copy-paste a goddamn long guide or so (it sucks), but you can just put into a tag with short name then call it later.\n"
                "Tag is server-specific.",
            colour=discord.Colour.teal()
        )
        embed.add_field(
            name="Commands",
            value=
                "`>>tag` - Get tag with given name\n"
                "      `create` - Create a tag\n"
                "      `alias` - Create an alias to another tag\n"
                "      `edit` - Edit a tag\n"
                "      `delete` - Delete a tag\n"
                "      `find` - Find tags\n"
                "      `list` - All tags",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command()
    async def misc(self, ctx):
        '''
            `>>help misc`
            Display miscellaneous commands.
        '''
        embed = discord.Embed(title="\u2699 Miscellaneous", description="Pretty much self-explanatory.", colour=discord.Colour.teal())
        embed.add_field(
            name="Commands",
            value=
                f"`>>jkp`, `>>jankenpon` - Play jankenpon with {self.bot.user.name}\n"
                "`>>dice <maxside> <amount>` - Roll dices\n"
                "`>>poll <question and choices>` - Make a poll\n\n"
                "`>>fancy` - Fancilize a sentence\n"
                "`>>glitch` - Z̜͍̊ă̤̥ḷ̐́ģͮ͛ò̡͞ ͥ̉͞ť͔͢e̸̷̅x̠ͯͧt̰̱̾\n"
                "      `m` - ĜþŞ¶ōÙđĔł ĝĖĘ Ùľ© ¼Ħâ Ŗėēů®³ĸ¤²\n\n"
                "`>>avatar` - Get your or a user avatar\n"
                "`>>g`, `>>google` - Google search\n"
                "`>>gtrans`, `>>translate` - Google, but translate\n\n"
                "`>>char` - Get unicode character info.\n"
                "`>>color`, `>>colour` - Visualize color's code",
            inline=False
         )
        await ctx.send(embed=embed)

    @help.command()
    async def sticker(self, ctx):
        '''
            `>>help sticker`
            Display sticker commands.
        '''
        embed = discord.Embed(
            title="\U0001f389 Sticker",
            description=
                "Send a reaction image.\n"
                "Use $stickername anywhere admidst message to trigger sticker send.\n"
                "Only one sticker shows up per message tho.\n"
                "Sticker is universal guild-wise.",
            colour=discord.Colour.teal()
        )
        embed.add_field(
            name="Commands",
            value=
                "`>>sticker` - Base command, do nothing\n"
                "      `add` - Add a sticker\n"
                "      `edit` - Edit a sticker\n"
                "      `delete` - Delete a sticker\n"
                "      `find` - Find stickers\n\n"
                "      `ban` - Ban a sticker in current server\n"
                "      `unban` - Unban a sticker in current server",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def detail(self, ctx, *, name=None):
        '''
            `>>detail <command name>`
            Get detailed command usage.
            Full command name, no prefix, obviously.
            The symbol `<` and `>` are there to separate arguments, it's not included in the actual command.

            __Example:__
            `>>detail help pso2`
        '''
        if name:

            command = self.bot.get_command(name)
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
                    embed.add_field(
                        name="Restriction",
                        value=", ".join((f"`{c.__name__[6:].replace('guild', 'server')}`" for c in all_checks)) if all_checks else "None",
                        inline=False
                    )
                    embed.add_field(name="Usage", value=(command.help or "Not yet documented.").format(ctx.me.display_name), inline=False)
                    return await ctx.send(embed=embed)
            await ctx.send(f"Command `{name}` doesn't exist.")
        else:
            cmd = self.bot.get_command("detail")
            await ctx.invoke(cmd, name="detail")

    async def get_webhook(self):
        feedback_channel = self.bot.get_channel(config.FEEDBACK_CHANNEL_ID)
        all_webhooks = await feedback_channel.webhooks()
        self.feedback_wh = all_webhooks[0]

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

    @commands.command(aliases=["stat"])
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def stats(self, ctx):
        '''
            `>>stats`
            Bot stats.
        '''
        async with ctx.typing():
            owner = self.bot.get_user(config.OWNER_ID)
            bytes_ = await utils.fetch(
                self.bot.session,
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
            process = self.bot.process
            embed = discord.Embed(colour=discord.Colour.blue())
            embed.add_field(name="Lastest changes", value="\n".join(desc), inline=False)
            embed.add_field(name="Owner", value=f"{owner.name}#{owner.discriminator}")
            embed.add_field(name="Library", value="[discord.py\\[rewrite\\]](https://github.com/Rapptz/discord.py/tree/rewrite)")
            embed.add_field(name="Created at", value=str(self.bot.user.created_at)[:10])
            embed.add_field(name="Guilds", value=f"{len(self.bot.guilds)} guilds")
            cpu_percentage = process.cpu_percent(None)
            embed.add_field(name="Process", value=f"CPU: {(cpu_percentage/self.bot.cpu_count):.2f}%\nRAM: {(process.memory_info().rss/1024/1024):.2f} MBs")
            uptime = int((now_time - self.bot.start_time).total_seconds())
            d = uptime // 86400
            h = (uptime % 86400) // 3600
            m = (uptime % 3600) // 60
            s = uptime % 60
            embed.add_field(name="Uptime", value=f"{d}d {h}h{m}m{s}s")
            embed.set_footer(text=utils.format_time(now_time.astimezone()))
            await ctx.send(embed=embed)

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
        await ctx.send(discord.utils.oauth_url(ctx.me.id, perms))

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Help(bot))
