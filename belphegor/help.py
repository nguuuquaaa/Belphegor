import discord
from discord.ext import commands
from . import utils
from .utils import config
import json
import re
import datetime
import pytz
import inspect
import os
import sys

#==================================================================================================================================================

ISO_DATE = re.compile(r"([0-9]{4})\-([0-9]{2})\-([0-9]{2})T([0-9]{2})\:([0-9]{2})\:([0-9]{2})Z")

#==================================================================================================================================================

class Help:
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
        paging = utils.Paginator([])

        #base help
        base_embed = discord.Embed(title=f"{self.emojis['ranged']} {self.bot.user}", colour=discord.Colour.teal())
        base_embed.set_thumbnail(url=self.bot.user.avatar_url)
        base_embed.add_field(
            name="Categories",
            value=
                "`>>help` - Show this message\n"
                f"      {self.emojis['mochi']} Otogi: Spirit Agents stuff\n"
                f"      {self.emojis['hu']} PSO2 stuff\n"
                "      \U0001f3b2 Play board games\n"
                "      \U0001f5bc Image search/random\n"
                "      \U0001f3b5 Music\n"
                "      \U0001f4d4 Role/server-related stuff\n"
                "      \u23f0 Reminder\n"
                "      \U0001f3f7 Text shortcut\n"
                "      \U0001f389 Custom image reactions\n"
                "      \u2699 Miscellaneous commands\n\n"
                "You can also use `>>help <command name>` to get command usage",
            inline=False
        )
        base_embed.add_field(
            name="Other",
            value=
                "`>>invite` - Invite link\n"
                "`>>stats` - Bot info\n"
                "`>>feedback` - Feedback anything\n",
            inline=False
        )
        base_embed.add_field(
            name="None-commands",
            value=
                "`ping` - pong\n"
                "`\\o\\` `/o/` `/o\\` `\\o/` - `/o/` `\\o\\` `\\o/` `/o\\`\n",
            inline=False
        )
        base_embed.set_footer(text="Default prefix: >> or bot mention")
        paging.set_action("\u21a9", lambda: base_embed)

        #otogi
        otogi_embed = discord.Embed(title=f"{self.emojis['mochi']} Otogi Spirit Agents", colour=discord.Colour.teal())
        try:
            embed.set_thumbnail(url=self.otogi_guild.icon_url)
        except:
            pass
        otogi_embed.add_field(
            name="Database",
            value=
                "`>>d`, `>>daemon` - Check a daemon info\n"
                "      `filter` - Find daemons with given conditions\n"
                "Note: Data taken from [Otogi Wikia](http://otogi.wikia.com/)\n\n"
                "`>>update` - Update database\n\n"
                "`>>nuker(s)` - Nuker rank\n"
                "`>>auto` - Auto attack rank\n"
                "`>>buffer(s)`, `>>debuffer(s)` - List of supporters\n"
                "Note: Data taken from [Otogi Effective Stats Spreadsheet](https://docs.google.com/spreadsheets/d/1oJnQ5TYL5d9LJ04HMmsuXBvJSAxqhYqcggDZKOctK2k/edit#gid=0)\n"
                "`>>gcqstr` - Guild Conquest STR rank",
            inline=False
        )
        otogi_embed.add_field(
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
        paging.set_action(self.emojis["mochi"], lambda: otogi_embed)

        #pso2
        pso2_embed = discord.Embed(title=f"{self.emojis['hu']} PSO2", colour=discord.Colour.teal())
        pso2_embed.set_thumbnail(url="http://i.imgur.com/aNAG34t.jpg")
        pso2_embed.add_field(
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
                "`>>eq` - Display EQ schedule for the next 3 hours\n"
                "`>>daily` - Display daily orders/featured quests\n"
                "`>>boost` - Display current week's boost events",
            inline=False
        )
        pso2_embed.add_field(
            name="EQ Alert",
            value=
                "`>>set eq` - Set EQ alert channel\n"
                "`>>set eqmini` - EQ alert, but less spammy\n"
                "`>>unset eq` - Unset EQ alert channel\n"
                "Special thanks to ACF for letting me use his EQ API.",
            inline=False
        )
        paging.set_action(self.emojis["hu"], lambda: pso2_embed)


        #game
        game_embed = discord.Embed(
            title="\U0001f3b2 Board game",
            description=
                "Mostly under construction, but you can play games with your fellow server members.\n"
                "Each game has their own set of commands.",
            colour=discord.Colour.teal()
        )
        game_embed.add_field(
            name="Games",
            value=
                "`>>monopoly` - Play monopoly [Currently not available]\n"
                "`>>cangua` - Play co ca ngua",
            inline=False
        )
        game_embed.add_field(
            name="Universal commands",
            value=
                "`>>abandon` - Abandon current game\n"
                "`>>gameover` - Ask players to end current game\n\n"
                "`>>whatgame` - Check if a member is playing game",
            inline=False
        )
        paging.set_action("\U0001f3b2", lambda: game_embed)

        #image
        image_embed = discord.Embed(
            title="\U0001f5bc Image",
            description="Get random picture from an image board.\nOr get image sauce. Everyone loves sauce.",
            colour=discord.Colour.teal()
        )
        image_embed.add_field(
            name="Commands",
            value=
                "`>>r`, `>>random`\n"
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
        paging.set_action("\U0001f5bc", lambda: image_embed)

        #music
        music_embed = discord.Embed(title="\U0001f3b5 Music", description="So many music bots out there but I want to have my own, so here it is.", colour=discord.Colour.teal())
        music_embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
        music_embed.add_field(
            name="Commands",
            value=
                "`>>m`, `>>music`\n"
                f"      `j`, `join` - Have {self.bot.user.name} join the voice channel you are\n"
                "                         currently in and play everything in queue\n"
                f"      `l`, `leave` - Have {self.bot.user.name} leave the voice channel\n\n"
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
        paging.set_action("\U0001f3b5", lambda: music_embed)

        #guild
        guild_embed = discord.Embed(
            title="\U0001f4d4 Server",
            description=
                "Server-related commands.\n"
                "Cannot be used in DM, obviously.",
            colour=discord.Colour.teal()
        )
        guild_embed.add_field(
            name="Server management",
            value=
                "`>>set`\n"
                "`>>unset`\n"
                "These 2 commands are used to set up stuff. Server-manager only.\n"
                "More detail via `>>help set` and `>>help unset`.\n\n"
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
        guild_embed.add_field(
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
        guild_embed.add_field(
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
        paging.set_action("\U0001f4d4", lambda: guild_embed)

        #remind
        remind_embed = discord.Embed(title="\u23f0 Reminder", description="Schedule to ping you after a certain time.", colour=discord.Colour.teal())
        remind_embed.add_field(
            name="Commands",
            value=
                "`>>remind`\n"
                "      `me` - Set a reminder\n"
                "      `list` - Display all your reminders\n"
                "      `delete` - Delete a reminder",
            inline=False
        )
        paging.set_action("\u23f0", lambda: remind_embed)

        #tag
        tag_embed = discord.Embed(
            title="\U0001f3f7 Tag",
            description=
                "Shortcut text.\n"
                "Sometimes you want to copy-paste a goddamn long guide or so (it sucks), but you can just put into a tag with short name then call it later.\n"
                "Tags are server-specific.",
            colour=discord.Colour.teal()
        )
        tag_embed.add_field(
            name="Commands",
            value=
                "`>>tag` - Get tag with given name\n"
                "      `create` - Create a tag\n"
                "      `alias` - Create an alias to another tag\n"
                "      `edit` - Edit a tag\n"
                "      `delete` - Delete a tag\n\n"
                "      `info` - Tag info\n"
                "      `find` - Find tags\n"
                "      `list` - All tags by member\n"
                "      `all` - All tags of server\n",
            inline=False
        )
        paging.set_action("\U0001f3f7", lambda: tag_embed)

        #sticker
        sticker_cog = self.bot.get_cog("Sticker")
        sticker_embed = discord.Embed(
            title="\U0001f389 Sticker",
            description=
                "Send a reaction image.\n"
                "Use $stickername anywhere admidst message to trigger sticker send.\n"
                "Only one sticker shows up per message.\n"
                "Sticker is universal server-wise.",
            colour=discord.Colour.teal()
        )
        sticker_embed.add_field(
            name="Commands",
            value=
                "`>>sticker`\n"
                "      `add` - Add a sticker\n"
                "      `edit` - Edit a sticker\n"
                "      `delete` - Delete a sticker\n\n"
                "      `info` - Sticker info\n"
                "      `find` - Find stickers\n"
                "      `list` - All stickers by member\n\n"
                "      `prefix` - Set server custom sticker prefix\n"
                "      `ban` - Ban a sticker in current server\n"
                "      `unban` - Unban a sticker in current server",
            inline=False
        )
        paging.set_action("\U0001f389", lambda: sticker_embed)

        #misc
        misc_embed = discord.Embed(title="\u2699 Miscellaneous", description="Pretty much self-explanatory.", colour=discord.Colour.teal())
        misc_embed.add_field(
            name="Commands",
            value=
                f"`>>jkp`, `>>jankenpon` - Play jankenpon with {self.bot.user.name}\n"
                "`>>dice` - Roll dices\n"
                "`>>poll` - Make a poll\n\n"
                "`>>fancy` - Fancilize a sentence\n"
                "`>>glitch` - Z̜͍̊ă̤̥ḷ̐́ģͮ͛ò̡͞ ͥ̉͞ť͔͢e̸̷̅x̠ͯͧt̰̱̾\n"
                "      `m` - ĜþŞ¶ōÙđĔł ĝĖĘ Ùľ© ¼Ħâ Ŗėēů®³ĸ¤²\n\n"
                "`>>avatar` - Get your or a user avatar\n"
                "`>>g`, `>>google` - Google search\n"
                "`>>gtrans`, `>>translate` - Google, but translate\n\n"
                "`>>char` - Get unicode character info.\n"
                "`>>color`, `>>colour` - Visualize color's code\n"
                "`>>choose` - Choose random\n"
                "`>>calc` - Calculator\n"
                "`>>ascii` - Grayscale ASCII art\n"
                "      `biggur` - Biggur grayscale ASCII art\n"
                "      `block` - Block ASCII art\n"
                "      `edge` - Edge-detection ASCII art",
            inline=False
        )
        paging.set_action("\u2699", lambda: misc_embed)

        self.help_paging = paging

    @commands.command()
    async def help(self, ctx, *, command_name=None):
        '''
            `>>help <optional: command>`
            Display help.
            If <command> is provide, display its usage.
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
                    embed.add_field(
                        name="Restriction",
                        value=", ".join((f"`{c.__name__[6:].replace('guild', 'server')}`" for c in all_checks)) if all_checks else "None",
                        inline=False
                    )
                    if command.help:
                        usage = command.help.partition("\n")
                        things = usage[2].split("\n\n\n")
                        if len(things) > 1:
                            embed.add_field(name="Usage", value=f"``{usage[0]}``\n{things[0]}".format(ctx.me.display_name), inline=False)
                            for thing in things[1:]:
                                embed.add_field(name="\u200b", value=f"\u200b{thing}", inline=False)
                        else:
                            usage = f"``{usage[0]}``\n{usage[2]}".format(ctx.me.display_name)
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

    @commands.command(aliases=["stat", "about"])
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def stats(self, ctx):
        '''
            `>>stats`
            Bot stats.
        '''
        await ctx.trigger_typing()
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
        embed = discord.Embed(colour=discord.Colour.blue())
        embed.add_field(name="Lastest changes", value="\n".join(desc), inline=False)
        embed.add_field(name="Owner", value=owner.mention if owner in ctx.guild.members else str(owner))
        v = sys.version_info
        embed.add_field(name="Written in", value=f"{self.emojis['python']} {v.major}.{v.minor}.{v.micro}")
        embed.add_field(name="Library", value="[discord.py\\[rewrite\\]](https://github.com/Rapptz/discord.py/tree/rewrite)")
        embed.add_field(name="Created at", value=str(self.bot.user.created_at)[:10])
        process = self.bot.process
        with process.oneshot():
            cpu_percentage = process.cpu_percent(None)
            embed.add_field(name="Process", value=f"CPU: {(cpu_percentage/self.bot.cpu_count):.2f}%\nRAM: {(process.memory_full_info().uss/1024/1024):.2f} MBs")
        uptime = int((now_time - self.bot.start_time).total_seconds())
        d, h = divmod(uptime, 86400)
        h, m = divmod(h, 3600)
        m, s = divmod(m, 60)
        embed.add_field(name="Uptime", value=f"{d}d {h}h{m}m{s}s")

        embed.add_field(name="Servers", value=f"{len(self.bot.guilds)} servers")
        ch_count = 0
        txt_count = 0
        ctgr_count = 0
        voice_count = 0
        member_count = 0
        off_members = set()
        for g in self.bot.guilds:
            ch_count += len(g.channels)
            txt_count += len(g.text_channels)
            ctgr_count += len(g.categories)
            voice_count += len(g.voice_channels)
            member_count += g.member_count
            for m in g.members:
                if m.status is discord.Status.offline:
                    off_members.add(m.id)
        off_count = len(off_members)
        user_count = len(self.bot.users)
        embed.add_field(name="Members", value=f"{member_count} members\n{user_count} unique\n{user_count-off_count} online\n{off_count} offline")
        embed.add_field(name="Channels", value=f"{ch_count} total\n{ctgr_count} categories\n{txt_count} text channels\n{voice_count} voice channels")
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
        await ctx.send(f"<{discord.utils.oauth_url(ctx.me.id, perms)}>")

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
