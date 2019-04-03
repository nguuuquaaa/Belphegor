import discord
from discord.ext import commands
from ..utils import modding
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

    @commands.command(aliases=[])
    async def maze(self, ctx, *, data: modding.KeyValue({("size", "s"): int})=modding.EMPTY):
        '''
            `>>maze <keyword: size|s>`
            Ramdomize a maze.
            Default size is 20. Max size is 50.
        '''
        size = data.geteither("size", "s", default=20)
        if size > 50:
            return await ctx.send("Size too big.")
        elif size < 3:
            return await ctx.send("Size too small.")
        game = MazeRunner(ctx, ctx.author, (size, size))
        bytes_ = await game.draw_maze()
        await ctx.send(file=discord.File(bytes_, "maze.png"))

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Game(bot))
