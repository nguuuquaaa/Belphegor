import discord
from discord.ext import commands
from . import board_game
import random
from .utils import config
import asyncio
import json

#==================================================================================================================================================

class GameBot:
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
        return game

    @commands.command()
    async def cangua(self, ctx, *members: discord.Member):
        if members:
            all_members = [ctx.author]
            all_members.extend(members)
            new_game = await board_game.CaNgua.new_game(ctx, all_members)
            self.games[new_game.game_id] = new_game
            await ctx.send("Co ca ngua starts now~")
            embed = discord.Embed()
            embed.add_field(name="This round players", value="\n".join((f"{i+1}. {p.member.display_name} ({p.color})" for i, p in enumerate(new_game.players))))
            await ctx.send(embed=embed)
            await ctx.send(f"{new_game.current_player.member.mention}'s turn ({new_game.current_player.color}):")
        else:
            await ctx.send("Simple Vietnamese board game, 2~4 players.")

    @commands.command()
    async def whatgame(self, ctx, member: discord.Member=None):
        if member:
            target = member
        else:
            target = ctx.author
        game = await self.get_game(target)
        if player is None:
            await ctx.send(f"{member.display_name} is not participating in any game.")
        else:
            await ctx.send("{member.display_name} is participating in {game.name} in {game.channel.guild.name}.")

    @commands.command()
    async def roll(self, ctx):
        current_game = await self.get_game(ctx.author)
        if ctx.author.id == current_game.current_player.member.id:
            await current_game.cmd_roll()

    @commands.command()
    async def abandon(self, ctx):
        sentences = {
            "initial":  "Abandon dis?",
            "yes":      "Done.",
            "no":       "Then you are still in.",
            "timeout":  "Timeout, cancelled abandoning."
        }
        check = await ctx.yes_no_prompt(sentences=sentences)
        if not check:
            return
        current_game = await self.get_game(ctx.author)
        player = current_game.get_player(member_id=ctx.author.id)
        if len(current_game.players) > 2:
            if player == current_game.current_player:
                await current_game.next_turn()
        await current_game.knock_out(player)

    @commands.command()
    async def gameover(self, ctx):
        current_game = await self.get_game(ctx.author)
        await current_game.cmd_game_over()

    @commands.command()
    async def skip(self, ctx):
        current_game = await self.get_game(ctx.author)
        player = current_game.get_player(member_id=ctx.author.id)
        if player == current_game.current_player:
            await current_game.cmd_skip()

    @commands.command(name="map")
    async def _map(self, ctx):
        async with ctx.message.channel.typing():
            current_game = await self.get_game(ctx.author)
            await current_game.cmd_map()

    @commands.command()
    async def move(self, ctx, number:int, step:int):
        current_game = await self.get_game(ctx.author)
        player = current_game.get_player(member_id=ctx.author.id)
        if player == current_game.current_player:
            await current_game.cmd_move(ctx, number, step)

    @commands.command()
    async def go(self, ctx):
        current_game = await self.get_game(ctx.author)
        player = current_game.get_player(member_id=ctx.author.id)
        if player == current_game.current_player:
            await current_game.cmd_go()

    @commands.command()
    async def climb(self, ctx, number:int, step:int):
        current_game = await self.get_game(ctx.author)
        player = current_game.get_player(member_id=ctx.author.id)
        if player == current_game.current_player:
            await current_game.cmd_climb(number, step)

    @commands.group()
    async def info(self, ctx):
        if ctx.invoked_subcommand is None:
            pass

    @info.command()
    async def turn(self, ctx):
        current_game = await self.get_game(ctx.author)
        await ctx.send(f"It's currently {current_game.current_player.member.mention} 's turn.")

    @commands.command()
    async def gamestate(self, ctx):
        current_game = await self.get_game(ctx.author)
        simple_player_data = await self.player_list.find_one({"member_id": ctx.author.id})
        game_data = await self.game_list.find_one({"game_id": simple_player_data["game_id"]})
        game_data.pop("_id")
        await ctx.send(file=discord.File(json.dumps(game_data, indent=4, ensure_ascii=False).encode("utf-8"), filename="gamedata.json"))

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(GameBot(bot))