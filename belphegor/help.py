import discord
from discord.ext import commands
from .utils import config

#==================================================================================================================================================

class HelpBot:
    '''
    Display help.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.bot.remove_command("help")
        test_guild = self.bot.get_guild(config.test_guild_id)
        self.otogi_guild = self.bot.get_guild(config.otogi_guild_id)
        self.emoji = {}
        for emoji_name in ("mochi", "hu", "ranged"):
            self.emoji[emoji_name] = discord.utils.find(lambda e:e.name==emoji_name, test_guild.emojis)

    @commands.group()
    async def help(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(title=f"{self.emoji['ranged']} {self.bot.user.name}#{self.bot.user.discriminator}", description="[Invite link](https://discordapp.com/oauth2/authorize?client_id=306706699102715907&scope=bot&permissions=0x1235CC50)", colour=discord.Colour.teal())
            embed.set_thumbnail(url=self.bot.user.avatar_url)
            embed.add_field(name="Categories", value=
                            "`>>help` - Show this message\n\n"
                            "`>>help otogi` - Otogi commands\n"
                            "`>>help pso2es` - PSO2es commands\n"
                            "`>>help game` - Board game commands\n"
                            "`>>help music` - Music commands\n"
                            "`>>help react` - Reactions\n"
                            "`>>help random` - Random image commands\n"
                            "`>>help server` - Server related commands\n"
                            "`>>help tag` - Tag commands\n"
                            "`>>help misc` - Miscellaneous commands", inline=False)
            embed.add_field(name="None-commands", value=
                            "`ping` - pong\n"
                            "`\o\` - /o/\n"
                            "`/o/` - \\o\\\n")
            embed.set_footer(text="Prefix: >>, !! or bot mention")
            await ctx.send(embed=embed)

    @help.command()
    async def otogi(self, ctx):
        embed = discord.Embed(title=f"{self.emoji['mochi']} Otogi Spirit Agents", colour = discord.Colour.teal())
        try:
            embed.set_thumbnail(url=self.otogi_guild.icon_url)
        except:
            pass
        embed.add_field(name="Database", value=
                        "`>>d`, `>>daemon` - Check a daemon info\n"
                        "`>>t`, `>>trivia` - Daemon trivia stuff\n"
                        "`>>p`, `>>pic` - Illustrations\n"
                        "`>>ds`, `>>search` - Search for relevant daemons\n"
                        "Command takes multiple lines with format `<attribute> <value>`\n"
                        "Attributes include: name, alias, type, class, max_atk, max_hp, mlb_atk, mlb_hp, rarity, faction, voice_actor, illustrator, how_to_acquire, notes_and_trivia and description\n\n"
                        "`>>update` - Update database", inline=False)
        embed.add_field(name="Simulation", value=
                        "`>>ls` - ~~salt~~ Lunchtime summon simulation\n"
                        "Note: has 1 seconds cooldown to prevent spam\n"
                        "`>>ls till <name>` - Estimate how many summons till you get a certain daemon\n"
                        "Note: does not count to mybox feature\n"
                        "`>>ls pool` - Display current summon pool\n\n"
                        "`>>mybox` - Show your or a player's box\n"
                        "`>>limitbreak` - Limit break your daemons\n\n"
                        "`>>mochi <name>` - Sell a certain daemon\n"
                        "`>>mochibulk <name>` - Sell all daemons with given name\n"
                        "`>>mochiall <rarity>` - Sell all daemons with given rarity\n\n"
                        "`>>gift <player> <name>` - Gift someone a daemon\n"
                        "`>>gimme <player> <price> <name>` - Ask someone to trade you a daemon", inline=False)
        await ctx.send(embed=embed)

    @help.command()
    async def pso2es(self, ctx):
        embed = discord.Embed(title=f"{self.emoji['hu']} PSO2es", colour = discord.Colour.teal())
        embed.set_thumbnail(url="http://i.imgur.com/aNAG34t.jpg")
        embed.add_field(name="Database", value=
                        "`>>c` - Check a chip info, name given can be EN or JP\n"
                        "Note: current library has weaponoid up to Lutyrus\n"
                        "I quit PSO2 and PSO2es (fuck TE nerf) so I won't update this anymore\n\n"
                        "`>>team` - Simulate a load, chips are separated by `-`", inline=False)
        await ctx.send(embed=embed)

    @help.command()
    async def game(self, ctx):
        embed = discord.Embed(colour = discord.Colour.teal())
        embed.add_field(name="Board game [Currently not available]", value=
                        "`>>monopoly` - Play monopoly\n"
                        "`>>cangua` - Play co ca ngua", inline=False)
        await ctx.send(embed=embed)

    @help.command()
    async def react(self, ctx):
        embed = discord.Embed(title="Reactions", colour = discord.Colour.teal())
        embed.add_field(name="Anime gif", value=
                        "`>>wut`, `>>huh` - Nani the fuck?\n\n"
                        f"`>>shock`, `>>shocked` - Even {self.bot.user.name} is shocked!\n\n"
                        "`>>fliptable`, `>>tableflip` - (╯°□°）╯︵ ┻━┻\n\n"
                        "`>>lmao`, `>>lol` - Bwhahahaha!!\n\n"
                        "`>>gotohell`, `>>damnyou` - I heard you rolled 5 SSRs in one 10x pull?\n\n"
                        "`>>uwa`, `>>waa` - What a beautiful duwang!\n\n"
                        "`>>yay`, `>>yes` - Will you \"Oraoraora\" with both hand?\n\n"
                        "`>>goodnight`, `>>g9` - Oyasunight\n\n"
                        "`>>morepls`, `>>lewdpls` - ( ͡° ͜ʖ ͡°)\n\n"
                        "`>>cry` - I'm just sweating through my eyes\n\n"
                        "`>>loli` - I swear she's hundreds years old!\n\n", inline=False)
        await ctx.send(embed=embed)

    @help.command()
    async def random(self, ctx):
        embed = discord.Embed(title=":frame_photo: Random", colour = discord.Colour.teal())
        embed.add_field(name="Command", value="`>>r`, `>>random` - Get a random picture from an image board")
        embed.add_field(name="Subcommands", value=
                        "`d`, `danbooru` - [Danbooru](https://danbooru.donmai.us)\n"
                        "`s`, `safebooru` - [Safebooru](https://safebooru.org)\n"
                        "`k`, `konachan` - [Konachan](http://konachan.net)\n"
                        "`y`, `yandere` - [Yandere](https://yande.re)\n\n"
                        "These are usable in channels with nsfw prefix only\n"
                        "`h`, `hentai` - [NSFW Danbooru](https://danbooru.donmai.us)\n"
                        "`sc`, `sancom` - [NSFW Sankaku Complex](https://chan.sankakucomplex.com)\n")
        embed.add_field(name="Notes", value=
                        "A subcommand is meant to be used with main command.\n"
                        "For example, `>>r d touhou` is a valid command.\n\n"
                        "Also Danbooru query is limited to 1 tag and SanCom is limited to 2 tags.")
        await ctx.send(embed=embed)

    @help.command()
    async def music(self, ctx):
        embed = discord.Embed(title="\U0001f3b5 Music", colour = discord.Colour.teal())
        embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
        embed.add_field(name="Command", value="`>>m`, `>>music` - Please don't stop the music~")
        embed.add_field(name="Subcommands", value=
                        f"`j`, `join` - Have {self.bot.user.display_name} join the voice channel you are currently in and play everything in queue\n"
                        f"`l`, `leave` - Have {self.bot.user.display_name} leave the voice channel\n\n"
                        "`q`, `queue` - Search Youtube and queue a song\n"
                        "`p`, `playlist` - Search Youtube and queue a playlist\n\n"
                        "`t`, `toggle` - Toggle play/pause\n"
                        "`f`, `forward` - Fast forward, default 10 (seconds)\n"
                        "`i`, `info` - Display video info, default current song (position 0)\n"
                        "`s`, `skip` - Skip current song\n"
                        "`v`, `volume` - Set volume, must be between 0 and 200\n"
                        "`r`, `repeat` - Toggle repeat mode\n"
                        "`d`, `delete` - Delete a song from queue with given position\n"
                        "`purge` - Purge all songs from queue\n\n"
                        "`export` - Export current queue to JSON file\n"
                        "`import` - Import JSON playlist", inline=False)
        embed.add_field(name="Notes", value=
                        "A subcommand is meant to be used with main command.\n"
                        "For example, `>>m q fukkireta` is a valid command.\n\n"
                        f"{self.bot.user.name} will leave voice channel after 2 minutes if queue is empty.", inline=False)
        await ctx.send(embed=embed)

    @help.command()
    async def server(self, ctx):
        embed = discord.Embed(title="Server", colour = discord.Colour.teal())
        embed.add_field(name="Manage server only", value=
                            "`>>welcome` - Set welcome message on the channel invoked\n"
                            "`>>mute` - Give a member \"Muted\" role if exists\n"
                            "Can specify reason and temporary (24h or less) ban time\n"
                            "`>>unmute` - Remove \"Muted\" role from a member\n\n"
                            "`>>kick` - Kick member, with optional reason\n"
                            "`>>ban` - Ban member, with optional reason\n"
                            "`>>unban` - Unban member, with optional reason\n\n"
                            "`>>purge` - Bulk delete messages, default 100 (most recent messages)\n"
                            "`>>purgereact` - Remove reactions of messages with given ids\n\n"
                            "`>>selfrole add` - Add an existed role to selfrole pool\n"
                            "`>>selfrole remove` - Remove a role from selfrole pool\n", inline=False)
        embed.add_field(name="Public commands", value=
                            "`>>selfrole` - Set selfrole with given name\n"
                            "`>>selfrole empty` - Set no selfrole\n"
                            "`>>selfrole list` - Display server selfrole pool", inline=False)
        await ctx.send(embed=embed)

    @help.command()
    async def tag(self, ctx):
        embed = discord.Embed(title="Tag", colour = discord.Colour.teal())
        embed.add_field(name="Command", value="`>>tag` - Get tag with given name")
        embed.add_field(name="Subcommands", value=
                            "`>>create` - Create a tag\n"
                            "`>>alias` - Create an alias to another tag\n\n"
                            "`>>edit` - Edit a tag\n"
                            "`>>append` - Edit by appending to the end of a tag\n"
                            "`>>delete` - Delete a tag", inline=False)
        embed.add_field(name="Notes", value=
                        "A subcommand is meant to be used with main command.\n"
                        "For example, `>>tag create belphybot The laziest bot ever.` is a valid command.\n\n"
                        "A tag name cannot contains spaces.\n"
                        "Tag create/edit follows the format `<name> <content>`.", inline=False)
        await ctx.send(embed=embed)

    @help.command()
    async def misc(self, ctx):
        embed = discord.Embed(title="Miscellaneous", colour = discord.Colour.teal())
        embed.add_field(name="Commands", value=
                            f"`>>jkp`, `>>jankenpon` - Play jankenpon with {self.bot.user.name}\n"
                            "`>>dice <maxside> <amount>` - Roll dices\n"
                            "`>>poll <question and choices>` - Make a poll\n"
                            "Question and choices are separated by line break\n"
                            "`>>fancy` - Fancilize a sentence\n\n"
                            "`>>avatar` - Get your or a user avatar\n"
                            "`>>r`, `>>random` - Random image\n"
                            "`>>g>`, `>>google` - Google search\n"
                            "`>>stats` - Bot info", inline=False)
        await ctx.send(embed=embed)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(HelpBot(bot))
