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
            embed = discord.Embed(title="Invite link", url="https://discordapp.com/oauth2/authorize?client_id=306706699102715907&scope=bot&permissions=0x1235CC50", colour = discord.Colour.teal())
            embed.set_author(name="{}#{}".format(self.bot.user.name, self.bot.user.discriminator), icon_url="http://i.imgur.com/WZ5nDdA.png")
            embed.set_thumbnail(url=self.bot.user.avatar_url)
            embed.add_field(name="Categories", value=
                            "`>>help` - Show this message\n\n"
                            "`>>help otogi` - Otogi commands\n"
                            "`>>help pso2es` - PSO2es commands\n"
                            "`>>help game` - Board game commands\n"
                            "`>>help music` - Music commands\n"
                            "`>>help react` - Reactions")
            embed.add_field(name="Misc.", value=
                            f"`>>jkp`, `>>jankenpon` - Play jankenpon with {self.bot.user.name}\n"
                            "`>>r`, `>>random` - Random image\n"
                            "`>>g>`, `>>google` - Google search\n"
                            "`>>poll <question and choices>` - Make a poll\n"
                            "Question and choices are separated by line break\n"
                            "`>>dice <maxside> <amount>` - Roll dices\n"
                            "`>>avatar` - Get your or a user avatar\n"
                            "`>>fancy` - Fancilize a sentence\n"
                            "`>>welcome` - Set welcome message on the channel invoked\n"
                            "Notes: Manage server permission only\n"
                            "`>>stats` - Bot info")
            embed.set_footer(text="Prefix: >>, !! or bot mention")
            await ctx.send(embed=embed)

    @help.command()
    async def otogi(self, ctx):
        embed = discord.Embed(title="{} Otogi Spirit Agents".format(self.emoji["mochi"]), colour = discord.Colour.teal())
        try:
            embed.set_thumbnail(url=self.otogi_guild.icon_url)
        except:
            pass
        embed.add_field(name="Database", value=
                        "`>>d`, `>>daemon` - Check a daemon info\n"
                        "`>>t`, `>>trivia` - Daemon trivia stuff\n"
                        "`>>p`, `>>pic` - Illustrations\n"
                        "`>>ds`, `>>search` - Search for relevant daemons\n"
                        "Command takes <attribute> <value> as arguments\n"
                        "Attributes include... ugh I'm too lazy to list all of them...\n\n"
                        "`>>update` - Update database")
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
                        "`>>gimme <player> <price> <name>` - Ask someone to trade you a daemon")
        await ctx.send(embed=embed)

    @help.command()
    async def pso2es(self, ctx):
        embed = discord.Embed(title="{} PSO2es".format(self.emoji["hu"]), colour = discord.Colour.teal())
        embed.set_thumbnail(url="http://i.imgur.com/aNAG34t.jpg")
        embed.add_field(name="Database", value=
                        "`>>c` - Check a chip info, name given can be EN or JP\n"
                        "Note: current library has weaponoid up to Lutyrus\n"
                        "I quit PSO2 and PSO2es (fuck TE nerf) so I won't update this anymore\n\n"
                        "`>>team` - Simulate a load, chips are separated by `-`")
        await ctx.send(embed=embed)

    @help.command()
    async def game(self, ctx):
        embed = discord.Embed(colour = discord.Colour.teal())
        embed.add_field(name="Board game [Currently not available]", value=
                        "`>>monopoly` - Play monopoly\n"
                        "`>>cangua` - Play co ca ngua")
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
                        "`>>loli` - I swear she's hundreds years old!\n\n")
        await ctx.send(embed=embed)

    @help.command()
    async def music(self, ctx):
        embed = discord.Embed(title="\U0001f3b5 Music", colour = discord.Colour.teal())
        embed.set_thumbnail(url="http://i.imgur.com/HKIOv84.png")
        embed.add_field(name="Command", value="`>>music`, `>>m` - We will, we will rock you~")
        embed.add_field(name="Subcommands", value=
                        f"`join`, `j` - Have {self.bot.user.display_name} join the voice channel you are currently in and play everything in queue\n"
                        f"`leave`, `l` - Have {self.bot.user.display_name} leave the voice channel\n\n"
                        "`queue`, `q` - Search Youtube and queue a song\n"
                        "`playlist`, `p` - Search Youtube and queue a playlist\n\n"
                        "`toggle`, `t` - Toggle play/pause\n"
                        "`info`, `i` - Display Youtube video info\n"
                        "`skip`, `s` - Skip current song\n"
                        "`volume`, `v` - Set volume, must be between 0 and 200\n"
                        "`repeat`, `r` - Toggle repeat mode\n"
                        "`delete`, `d` - Delete a song from queue with given position\n"
                        "`purge` - Purge all songs from queue\n\n"
                        "`export` - Export current queue to JSON file\n"
                        "`import` - Import JSON playlist")
        embed.add_field(name="Notes", value=
                        "A subcommand is meant to be used with main command.\n"
                        "For example, `>>m q fukkireta` is a valid command.\n\n"
                        f"{self.bot.user.name} will leave voice channel after 2 minutes if queue is empty.")
        await ctx.send(embed=embed)

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(HelpBot(bot))
