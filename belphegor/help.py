import discord
from discord.ext import commands
from .utils import config

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
        self.suggest_channel = self.bot.get_channel(config.SUGGEST_CHANNEL_ID)

    @commands.group()
    async def help(self, ctx):
        '''
            `>>help`
            Display general help.
        '''
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title=f"{self.emoji['ranged']} {self.bot.user.name}#{self.bot.user.discriminator}",
                description="[Invite link](https://discordapp.com/oauth2/authorize?client_id=306706699102715907&scope=bot&permissions=305523830)",
                colour=discord.Colour.teal()
            )
            embed.set_thumbnail(url=self.bot.user.avatar_url)
            embed.add_field(
                name="Categories",
                value=
                    "`>>help` - Show this message\n\n"
                    "`>>help otogi` - Otogi: Spirit Agents commands\n"
                    "`>>help pso2` - PSO2 commands\n"
                    "`>>help game` - Board game commands\n"
                    "`>>help music` - Music commands\n"
                    "`>>help random` - Random image commands\n"
                    "`>>help server` - Server related commands\n"
                    "`>>help remind` - Reminder commands\n"
                    "`>>help tag` - Text shortcut commands\n"
                    "`>>help sticker` - Custom image reactions\n"
                    "`>>help misc` - Miscellaneous commands\n\n"
                    "`>>detail` - Get detailed command info\n"
                    "Note: Pretty much `>>help` for command description and `>>detail` for detailed command usage.\n"
                    "Also this is not completed yet since I'm lazy.",
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
            embed.add_field(
                name="Feedback",
                value=
                    "`>>suggest` - Suggest anything\n",
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
                "`>>t`, `>>trivia` - Daemon trivia stuff\n"
                "`>>p`, `>>pic` - Illustrations\n"
                "Note: Data taken from [Otogi Wikia](http://otogi.wikia.com/)\n\n"
                "`>>ds`, `>>search` - Search for relevant daemons\n"
                "Command takes multiple lines with format `<attribute> <value>`\n"
                "Attributes include: name, alias, type, class, max_atk, max_hp, mlb_atk, mlb_hp, rarity, skill, ability, bond, faction, voice_actor, illustrator, how_to_acquire, notes_and_trivia and description\n\n"
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
                "Note: has 1 seconds cooldown to prevent spam\n"
                "`>>ls till <name>` - Estimate how many summons till you get a certain daemon\n"
                "Note: does not count to mybox feature\n"
                "`>>ls pool` - Display current summon pool\n\n"
                "`>>mybox` - Show your or a player's box\n"
                "`>>lb`, `>>limitbreak` - Limit break your daemons\n\n"
                "`>>mochi <name>` - Sell a certain daemon\n"
                "`>>mochi bulk <name>` - Sell all daemons with given name\n"
                "`>>mochi all <rarity>` - Sell all daemons with given rarity\n\n"
                "`>>gift <player> <name>` - Gift someone a daemon\n"
                "`>>gimme <player> <name> for <number> mochi` - Ask someone to trade you a daemon",
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
                "`>>c`, `>>chip` - Check a chip info, name given can be EN or JP\n"
                "Note: Data taken from [swiki](http://pso2es.swiki.jp/)\n\n"
                "`>>w`, `>>weapon` - Check a weapon info, name given can be EN or JP\n"
                "`>>u`, `>>unit` - Check a unit info, name given can be EN or JP\n"
                "Note: Data taken from [Arks-Visiphone](http://pso2.arks-visiphone.com/wiki/Main_Page)\n\n"
                "`>>i`, `>>item` - Search for items\n"
                "`>>price` - Check item price, may be outdated\n"
                "Note: Data taken from DB Kakia\n\n"
                "`>>eq` - Display EQ schedule for the next 3 hours",
            inline=False
        )
        embed.add_field(
            name="Manage server permission only",
            value=
                "`>>set eq` - Set EQ alert channel\n"
                "`>>unset eq` - Unset EQ alert channel\n"
                "Special thanks to ACF for letting me use his EQ API.",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command()
    async def game(self, ctx):
        '''
            `>>help game`
            Display board game related commands.
        '''
        embed = discord.Embed(title="\U0001f3b2 Board game", description="Mostly under construction, but you can play games with your fellow server members.", colour=discord.Colour.teal())
        embed.add_field(
            name="Commands",
            value=
                "`>>monopoly` - Play monopoly [Currently not available]\n"
                "`>>cangua` - Play co ca ngua\n\n"
                "`>>abandon` - Abandon current game\n"
                "`>>gameover` - Ask players to end current game\n\n"
                "`>>whatgame` - Check if a member is playing game or not",
            inline=False
        )
        embed.add_field(
            name="Notes",
            value=
                "Each game has their own set of commands, those above are just universal commands"
        )
        await ctx.send(embed=embed)

    @help.command()
    async def random(self, ctx):
        '''
            `>>help random`
            Dislay image board random commands.
        '''
        embed = discord.Embed(title="\U0001f5bc Random", description="Get a random picture from an image board", colour=discord.Colour.teal())
        embed.add_field(name="Command", value="`>>r`, `>>random` - Display this message")
        embed.add_field(
            name="Subcommands",
            value=
                "`d`, `danbooru` - [Danbooru](https://danbooru.donmai.us)\n"
                "`s`, `safebooru` - [Safebooru](https://safebooru.org)\n"
                "`k`, `konachan` - [Konachan](http://konachan.net)\n"
                "`y`, `yandere` - [Yandere](https://yande.re)\n\n"
                "These are usable in nsfw channels only\n"
                "`dh`, `danbooru_h` - [NSFW Danbooru](https://danbooru.donmai.us)\n"
                "`kh`, `konachan_h` - [NSFW Konachan](http://konachan.com)\n"
                "`sc`, `sancom` - [NSFW Sankaku Complex](https://chan.sankakucomplex.com)\n",
            inline=False
        )
        embed.add_field(
            name="Notes",
            value=
                "A subcommand is an extension of main command.\n"
                "For example, `>>r d touhou` is a valid command.\n\n"
                "Also Danbooru query is limited to 1 tag and SanCom is limited to 2 tags.",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command()
    async def music(self, ctx):
        '''
            `>>help music`
            Display music commands.
            The same as `>>music`
        '''
        embed = discord.Embed(title="\U0001f3b5 Music", description="So many music bots out there but I want to have my own, so here it is.", colour=discord.Colour.teal())
        embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
        embed.add_field(name="Command", value="`>>m`, `>>music` - Display this message")
        embed.add_field(
            name="Subcommands",
            value=
                f"`j`, `join` - Have {self.bot.user.display_name} join the voice channel you are currently in and play everything in queue\n"
                f"`l`, `leave` - Have {self.bot.user.display_name} leave the voice channel\n\n"
                "`q`, `queue` - Search Youtube and queue a song\n"
                "`p`, `playlist` - Search Youtube and queue a playlist\n"
                "Use `-r` or `-random` flag to shuffle imported playlist.\n\n"
                "`i`, `info` - Display video info, default current song (position 0)\n"
                "`t`, `toggle` - Toggle play/pause\n"
                "`v`, `volume` - Set volume, must be between 0 and 200\n"
                "`f`, `forward` - Fast forward, default 10 (seconds)\n"
                "`s`, `skip` - Skip current song\n"
                "`r`, `repeat` - Toggle repeat mode\n\n"
                "`d`, `delete` - Delete a song from queue with given position\n"
                "`purge` - Purge all songs from queue\n\n"
                "`setchannel` - Change notifying channel\n"
                "`export` - Export current queue to JSON file\n"
                "`import` - Import JSON playlist",
            inline=False
        )
        embed.add_field(
            name="Notes",
            value=
                "A subcommand is an extension of main command.\n"
                "For example, `>>m q fukkireta` is a valid command.\n\n"
                f"{self.bot.user.name} will leave voice channel after 2 minutes if queue is empty.",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command(aliases=["guild"])
    async def server(self, ctx):
        '''
            `>>help server`
            Display non-DM, server related commands.
        '''
        embed = discord.Embed(
            title="\U0001f4d4 Server",
            description=
                "Server specific commands.\n"
                "Cannot be used in DM.",
            colour=discord.Colour.teal()
        )
        embed.add_field(
            name="Manage server permission only",
            value=
                "`>>set`\n"
                "`>>unset`\n"
                "Note: these 2 commands are used to set up server prefixes (`prefix`), welcome channel (`welcome`), NSFW role (`nsfwrole`) and log channel (`log`)\n\n"
                "`>>mute` - Give a member \"Muted\" role if exists\n"
                "Can specify reason and temporary (24h or less) ban time\n"
                "`>>unmute` - Remove \"Muted\" role from a member\n\n"
                "`>>kick` - Kick member, with optional reason\n"
                "`>>ban` - Ban member, with optional reason\n"
                "`>>unban` - Unban member, with optional reason\n\n"
                "`>>purge` - Bulk delete messages, default 10 (most recent messages)\n"
                "`>>purgereact` - Remove reactions of messages with given ids\n\n"
                "`>>selfrole add <name>` - Add an existed role to selfrole pool\n"
                "`>>selfrole remove <name>` - Remove a role from selfrole pool",
            inline=False
        )
        embed.add_field(
            name="Public commands",
            value=
                "`>>selfrole <name>` - Set selfrole with given name, if applicable\n"
                "`>>selfrole empty` - Unset selfrole\n"
                "`>>selfrole list` - Display server selfrole pool\n"
                "`>>selfrole distribution` - Pie chart showing selfrole distribution\n\n"
                "`>>creampie` - Add NSFW role, if applicable\n"
                "`>>censored` - Remove NSFW role, if applicable",
            inline=False
        )
        await ctx.send(embed=embed)

    @help.command()
    async def remind(self, ctx):
        '''
            `>>help remind`
            Display remind commands.
        '''
        embed = discord.Embed(title="\u23f0 Reminder", description="Schedule to ping you after a certain time.", colour=discord.Colour.teal())
        embed.add_field(name="Command", value="`>>remind` - Display this message", inline=False)
        embed.add_field(
            name="Subcommands",
            value=
                "`me <reminder and time>` - Set a reminder\n"
                "`list` - Display all your reminders\n"
                "`delete <position>` - Delete a reminder",
            inline=False
        )
        embed.add_field(
            name="Notes",
            value=
                "A subcommand is an extension of main command.\n"
                "For example, `>>remind me do laundry in 1h30m` is a valid command.\n"
                "Note: time should be machine-readable, like \"5 weeks & 10 days, 20h and 10 min\" and such.",
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
                "Sometimes you want to copy-paste a goddamn long guide or so (it sucks), but you can just put into a tag with short name then call it later.",
            colour=discord.Colour.teal()
        )
        embed.add_field(name="Command", value="`>>tag <name>` - Get tag with given name", inline=False)
        embed.add_field(
            name="Subcommands",
            value=
                "`create <name> <content>` - Create a tag\n"
                "`alias <name> <alias>` - Create an alias to another tag\n\n"
                "`edit <name> <content>` - Edit a tag\n"
                "`delete <name>` - Delete a tag\n\n"
                "The following subcommand can only be used by server managers\n"
                "`ban <name>` - Ban a tag in current server",
            inline=False
        )
        embed.add_field(
            name="Notes",
            value=
                "A subcommand is an extension of main command.\n"
                "For example, `>>tag create belphybot The laziest bot ever.` is a valid command.\n\n"
                "For create, alias and edit, if tag name contains spaces then it should be enclosed in double quotation marks.",
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
                "`>>poll <question and choices>` - Make a poll\n"
                "Question and choices are separated by line break\n\n"
                "`>>fancy` - Fancilize a sentence\n"
                "`>>glitch` - Glitch a sentence\n"
                "`>>glitch m` - Generate a meaningless sentence\n\n"
                "`>>avatar` - Get your or a user avatar\n"
                "`>>g`, `>>google` - Google search\n"
                "`>>gtrans`, `>>translate` - Google, but translate\n"
                "`>>stats` - Bot info",
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
                "Note: can only send one sticker per message.",
            colour=discord.Colour.teal()
        )
        embed.add_field(
            name="Commands",
            value=
                "`>>sticker add` - Add a sticker\n"
                "`>>sticker edit` - Edit a sticker\n"
                "Add and edit follow format: `<sticker_name_no_space> <pic_url>`\n"
                "`>>sticker delete` - Delete a sticker\n\n"
                "`>>sticker find <name>` - Find a sticker with given name\n\n"
                "The following subcommand can only be used by server managers\n"
                "`ban <name>` - Ban a sticker in current server",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def detail(self, ctx, *args):
        '''
            `>>detail <command name>`
            Get the detail command usage.
            Command name, no prefix, obviously.
            Note: The symbol `<` and `>` are there to separate arguments, it's not included in the actual command.

            *Example:*
            `>>detail help pso2`
        '''
        if args:
            command = self.bot
            try:
                for cmd_name in args:
                    command = command.get_command(cmd_name)
            except:
                pass
            else:
                if command:
                    if not command.hidden:
                        embed = discord.Embed(colour=discord.Colour.teal())
                        embed.add_field(name="Parent command", value=command.full_parent_name or "None")
                        embed.add_field(name="Base command", value=f"`{command.name}`")
                        embed.add_field(name="Aliases", value=f"`{', '.join(command.aliases)}`" if command.aliases else "None")
                        embed.add_field(name="Usage", value=command.help or "Not yet documented.", inline=False)
                        return await ctx.send(embed=embed)
            await ctx.send(f"Command `{' '.join(args)}` doesn't exist.")
        else:
            cmd = self.bot.get_command("detail")
            await ctx.invoke(cmd, "detail")

    @commands.command()
    async def suggest(self, ctx, *, content):
        '''
            `>>suggest <anything goes here>`
            Pretty much self-explanatory.

            *Example:*
            `>>suggest moar loli content`
        '''
        embed = discord.Embed(description=content)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        await self.suggest_channel.send(embed=embed)
        await ctx.confirm()

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Help(bot))
