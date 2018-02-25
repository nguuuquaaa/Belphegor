import discord
from discord.ext import commands
from . import board_game
from .utils import config, checks
import random
import asyncio
import json

#==================================================================================================================================================

class Game:
    '''
        Play board games with other users.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.games = {}
        self.game_list = bot.db.board_game_list
        self.player_list = bot.db.board_game_player_list

    async def get_game(self, member):
        game = None
        simple_player_data = await self.player_list.find_one({"member_id": member.id})
        if simple_player_data:
            game = self.games.get(simple_player_data["game_id"])
            if not game:
                game_data = await self.game_list.find_one({"game_id": simple_player_data["game_id"]})
                if game_data:
                    game = getattr(board_game, game_data["game_class"]).load(self.bot, game_data)
                    self.games[game_data["game_id"]] = game
        return game

    @commands.command()
    @checks.guild_only()
    async def cangua(self, ctx, *members: discord.Member):
        '''
            `>>cangua <optional: list of members>`
            Play ca ngua with the members in question.
            Each user can only play one board game across all servers at a time.
            Bots and those who are already playing are excluded.
            If command is invoked without argument then the rules is displayed instead.
        '''
        if members:
            all_members = set([ctx.author])
            all_members.update((m for m in members if not m.bot))
            new_game = await board_game.CaNgua.new_game(ctx, all_members)
            self.games[new_game.game_id] = new_game
            await ctx.send("Co ca ngua starts now~\nGame ID: {new_game.game_id}")
            embed = discord.Embed()
            embed.add_field(name="This round players", value="\n".join((f"{i+1}. {p.member.display_name} ({p.color})" for i, p in enumerate(new_game.players))))
            await ctx.send(embed=embed)
            await ctx.send(f"{new_game.current_player.member.mention}'s turn ({new_game.current_player.color}):")
        else:
            embed = discord.Embed(
                title="Co Ca Ngua",
                description=
                    "Simple Vietnamese board game, 2~4 players.\n"
                    "Each player is affiliated with a color, and possesses 4 horses.\n"
                    "Horses start at the big bold spot of their color, and move counter-clockwise.\n"
                    "You can't pass other horses, and horses can't be in the same spot, but your can kick other players' horses back to their stable.\n"
                    "The goal is to have all the horses climb to the highest possible spot on your tower.\n"
                    "The winner is the first one to do so.",
                colour=discord.Colour.purple()
            )
            embed.add_field(
                name="How to play",
                value=
                    "1. Players take turn roll the dices.\n"
                    "2. If the roll results are 6 and 1 or two same side then you get another roll.\n"
                    "3. If the roll results are 6 and 1 or two same side then you can let one of your horse out. Letting horse out consumes both roll results.\n"
                    "4. The number of steps your horses can move is either roll result or both.\n"
                    "5. If you are at the base of the tower then you can climb to any floor, but if you are in the middle then you can only climb one at a time."
            )
            embed.add_field(
                name="Commands",
                value=
                    "`>>roll` - Roll dices\n"
                    "`>>go` - Let your horse out\n"
                    "`>>move` - Move horse(s)\n"
                    "`>>climb` - Have your horse climb"
            )
            await ctx.send(embed=embed)

    @commands.command()
    @checks.guild_only()
    async def whatgame(self, ctx, member: discord.Member=None):
        '''
            `>>whatgame <optional: member mention>`
            Check if target is playing a game or not.
            If you invoke command without member mention then the target is yourself.
            Just don't try to add @everyone or @here since it's not a member mention at all.
        '''
        target = member or ctx.author
        current_game = await self.get_game(target)
        if current_game:
            await ctx.send(f"{member.display_name} is participating in {game.name} in {game.channel.guild.name}.")
        else:
            await ctx.send(f"{member.display_name} is not participating in any game.")

    @commands.command()
    @checks.guild_only()
    async def roll(self, ctx):
        '''
            `>>roll`
            Roll dices.
            Part of board game commands.
        '''
        current_game = await self.get_game(ctx.author)
        if current_game:
            if ctx.author.id == current_game.current_player.member.id:
                await current_game.cmd_roll()

    @commands.command()
    @checks.guild_only()
    async def abandon(self, ctx):
        '''
            `>>abandon`
            Abandon current game.
            Part of board game commands.
        '''
        current_game = await self.get_game(ctx.author)
        if current_game:
            sentences = {
                "initial":  "Abandon dis?",
                "yes":      "Done.",
                "no":       "Then you are still in.",
                "timeout":  "Timeout, cancelled abandoning."
            }
            check = await ctx.yes_no_prompt(sentences)
            if not check:
                return
            await current_game.cmd_abandon(ctx.author.id)

    @commands.command()
    @checks.guild_only()
    async def gameover(self, ctx):
        '''
            `>>gameover`
            Make a poll about ending the current game.
            Part of board game commands.
        '''
        current_game = await self.get_game(ctx.author)
        if current_game:
            await current_game.cmd_game_over()
            self.games.pop(current_game.game_id)

    @commands.command()
    @checks.guild_only()
    async def skip(self, ctx):
        '''
            `>>skip`
            Skip/pass your turn.
            Part of board game commands.
        '''
        current_game = await self.get_game(ctx.author)
        if current_game:
            player = current_game.get_player(member_id=ctx.author.id)
            if player == current_game.current_player:
                await current_game.cmd_skip()

    @commands.command(name="map")
    @checks.guild_only()
    async def _map(self, ctx):
        '''
            `>>map`
            Display current game map.
            Part of board game commands.
        '''
        current_game = await self.get_game(ctx.author)
        if current_game:
            async with ctx.message.channel.typing():
                await current_game.cmd_map()

    @commands.command()
    @checks.guild_only()
    async def move(self, ctx, number: int, step: int):
        '''
            `>>move <number> <step>`
            Move horse number <number> by <step> steps.
            Part of cangua commands.
        '''
        current_game = await self.get_game(ctx.author)
        if current_game:
            player = current_game.get_player(member_id=ctx.author.id)
            if player == current_game.current_player:
                await current_game.cmd_move(ctx, number, step)

    @commands.command()
    @checks.guild_only()
    async def go(self, ctx):
        '''
            `>>go <number>`
            Put horse number <number> at the start point.
            Part of cangua commands.
        '''
        current_game = await self.get_game(ctx.author)
        if current_game:
            player = current_game.get_player(member_id=ctx.author.id)
            if player == current_game.current_player:
                await current_game.cmd_go()

    @commands.command()
    @checks.guild_only()
    async def climb(self, ctx, number: int, step: int):
        '''
            `>>climb <number> <floor>`
            Have horse number <number> climb the tower to floor <floor>.
            Part of cangua commands.
        '''
        current_game = await self.get_game(ctx.author)
        if current_game:
            player = current_game.get_player(member_id=ctx.author.id)
            if player == current_game.current_player:
                await current_game.cmd_climb(number, step)

    @commands.group(invoke_without_command=True)
    @checks.guild_only()
    async def info(self, ctx, member: discord.Member=None):
        '''
            `>>info <optional: member mention>`
            Check for info on a player.
            Member should be playing the same game as you.
            If you invoke command without member mention then the target is yourself.
            Part of board game commands.
        '''
        if ctx.invoked_subcommand is None:
            pass

    @info.command()
    async def turn(self, ctx):
        '''
            `>>info turn`
            Check for whose turn is currently.
            Part of board game commands.
        '''
        current_game = await self.get_game(ctx.author)
        if current_game:
            await ctx.send(f"It's currently {current_game.current_player.member.mention} 's turn.")
        else:
            await ctx.send("You are not participating in any game.")

    @commands.command()
    @checks.guild_only()
    async def gamestate(self, ctx):
        '''
            `>>gamestate`
            Send current game state as JSON file.
            For people who's interested in game internal state.
            Part of board game commands.
        '''
        simple_player_data = await self.player_list.find_one({"member_id": ctx.author.id})
        game_data = await self.game_list.find_one({"game_id": simple_player_data["game_id"]})
        game_data.pop("_id")
        await ctx.send(file=discord.File(json.dumps(game_data, indent=4, ensure_ascii=False).encode("utf-8"), filename="gamedata.json"))

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Game(bot))
