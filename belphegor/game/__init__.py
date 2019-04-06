import discord
from discord.ext import commands
from ..utils import modding, data_type
from .error import *
from .dices import *
from .connect_four import *
from .maze_runner import *
import asyncio

#==================================================================================================================================================

class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.playing = set()
        self.mazes = data_type.AutoCleanupDict(600, loop=bot.loop)

    def cog_unload(self):
        self.mazes.cleanup()

    @commands.command(aliases=["c4"])
    async def connectfour(self, ctx):
        '''
            `>>c4`
            Play Connect Four.
        '''
        if ctx.author in self.playing:
            return await ctx.send("You are already playing.")
        await ctx.send(f"Okay who want to play some Connect Four with {ctx.author.mention}? Say \"me\" to join.")
        while True:
            try:
                message = await self.bot.wait_for("message", check=lambda m: m.channel==ctx.channel and not m.author.bot and m!=ctx.author and m.content=="me", timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send("No one joined...")
            else:
                if message.author in self.playing:
                    await ctx.send("You are already playing.")
                else:
                    break

        game = ConnectFour(ctx, ctx.author, message.author)
        self.playing.add(ctx.author)
        self.playing.add(message.author)
        await game.play()

    @commands.group()
    async def maze(self, ctx):
        pass

    @maze.command()
    async def create(self, ctx, *, data: modding.KeyValue({("size", "s"): int, ("weave", "w"): bool, ("density", "d"): float})=modding.EMPTY):
        '''
            `>>maze create <keyword: mode> <keyword: size|s> <keyword: weave|w> <keyword: density|d>`
            Randomize a maze.
            Mode is either prim or kruskal. Default mode is prim.
            Default size is 20. Max size is 50.
            Weave is either true or false. Determine if the result is a weave maze and also kind of maze render. Only kruskal mode can produce weave mazes. Default to false.
            Density determines how many overlapping sections. Default to 0.05. Max density is 0.5.
        '''
        size = data.geteither("size", "s", default=20)
        if size > 50:
            return await ctx.send("Size too big.")
        elif size < 3:
            return await ctx.send("Size too small.")
        mode = data.get("mode", "prim")
        if mode not in ("kruskal", "prim"):
            return await ctx.send("Mode must be either kruskal or prim.")
        weave = data.geteither("weave", "w", default=False)
        density = data.geteither("density", "d", default=0.05)
        if density <= 0:
            return await ctx.send("Density must be positive.")
        if density > 0.5:
            return await ctx.send("Density to large.")

        game = await MazeRunner.new(ctx, size, mode=mode, weave=weave, density=density)
        self.mazes[ctx.author] = game
        bytes_ = await game.draw_maze()
        await ctx.send(file=discord.File(bytes_, "maze.png"))

    @maze.command()
    async def solve(self, ctx):
        '''
            `>>maze solve`
            Solve the last maze you created.
        '''
        game = self.mazes.pop(ctx.author, None)
        if game:
            bytes_ = await game.draw_solution()
            await ctx.send(file=discord.File(bytes_, "solution.png"))
        else:
            await ctx.send("You haven't created any maze in the last 10 minutes.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Game(bot))
