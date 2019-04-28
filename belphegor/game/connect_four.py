import discord
import numpy as np
from . import error
import asyncio

#==================================================================================================================================================

class ConnectFourCore:
    def __init__(self, x=6, y=7):
        self.x = x
        self.y = y
        self.board = np.zeros((x, y), dtype=np.int8)
        self.win_conditions = [
            np.array(
                [
                    [1, 1, 1, 1]
                ],
                dtype=np.int8
            ),
            np.array(
                [
                    [1],
                    [1],
                    [1],
                    [1]
                ],
                dtype=np.int8
            ),
            np.array(
                [
                    [0, 0, 0, 1],
                    [0, 0, 1, 0],
                    [0, 1, 0, 0],
                    [1, 0, 0, 0]
                ],
                dtype=np.int8
            ),
            np.array(
                [
                    [1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]
                ],
                dtype=np.int8
            )
        ]
        self.fills = np.array([x-1 for i in range(y)], dtype=np.int8)
        self.win_player = 0
        self.current_player = 1

    def check_win_condition(self):
        board = self.board
        x = self.x
        y = self.y
        npsum = np.sum
        for win_cond in self.win_conditions:
            wx, wy = win_cond.shape
            for ix in range(0, x-wx+1):
                for iy in range(0, y-wy+1):
                    cut = board[ix:ix+wx, iy:iy+wy]
                    ret = npsum(cut * win_cond)
                    if ret == 4:
                        self.win_player = 1
                        return 1
                    elif ret == -4:
                        self.win_player = -1
                        return -1
        else:
            return 0

    def drop(self, column):
        if self.win_player != 0:
            raise error.GameError("This game is already ended.")
        if column > self.board.shape[1] or column < 0:
            raise error.IllegalMove("Input column out of range.")
        row = self.fills[column]
        if row < 0:
            raise error.IllegalMove("This column is already filled.")

        self.board[row, column] = self.current_player
        self.fills[column] -= 1
        self.current_player = -self.current_player

        return self.check_win_condition()

    def is_stalled(self):
        return np.all(self.fills==-1)

#==================================================================================================================================================

class ConnectFour:
    P1_ICON = "\U0001f534"
    P2_ICON = "\U0001f535"
    BLANK_ICON = "\u2b1b"

    def __init__(self, player1, player2):
        self.game = ConnectFourCore()
        self.player1 = player1
        self.player2 = player2

    def draw_board(self):
        all_lines = []
        for row in self.game.board:
            all_lines.append(" ".join((self.P1_ICON if v==1 else self.P2_ICON if v==-1 else self.BLANK_ICON for v in row)))
        all_lines.append(" ".join((f"{i+1}\u20e3" for i in range(self.game.y))))
        return "\n".join(all_lines)

    def embed_visualize(self):
        embed = discord.Embed(description=self.draw_board())
        embed.add_field(name="Players", value=f"{self.P1_ICON} {self.player1.mention}\n{self.P2_ICON} {self.player2.mention}", inline=False)
        embed.add_field(name="Status", value=f"Game started. {self.player1.mention}'s turn", inline=False)
        embed.set_footer(text="Game will end if no input in 5 minutes")
        return embed

    def generate_next_player(self):
        while True:
            yield self.player1
            yield self.player2

    async def play(self, ctx):
        game = self.game
        player_generate = self.generate_next_player()
        embed = self.embed_visualize()
        message = await ctx.send(embed=embed)
        emojis = {f"{i+1}\u20e3": i for i in range(7)}
        emojis["\u274c"] = None

        async def add_reactions():
            for e in emojis:
                await message.add_reaction(e)

        ctx.bot.loop.create_task(add_reactions())

        async def end_game():
            try:
                await message.clear_reactions()
            except discord.Forbidden:
                pass

        current_player = next(player_generate)
        while True:
            try:
                reaction, user = await ctx.bot.wait_for("reaction_add", check=lambda r, u: r.emoji in emojis and r.message.id==message.id and u.id==current_player.id, timeout=600)
            except asyncio.TimeoutError:
                await end_game()
                game.win_player = -game.current_player
                embed.set_field_at(1, name="Status", value=f"Game ended. Winner: {next(player_generate).mention}", inline=False)
                return await message.edit(embed=embed)

            try:
                await reaction.remove(user)
            except discord.Forbidden:
                pass

            index = emojis[reaction.emoji]
            if index is None:
                await end_game()
                embed.set_field_at(1, name="Status", value=f"{current_player.mention} abandoned the game.\n{next(player_generate).mention} won the game.", inline=False)
                await message.edit(embed=embed)
                return

            try:
                winner = game.drop(index)
            except error.GameError as e:
                embed.set_field_at(1, name="Status", value=e.message, inline=False)
                await message.edit(embed=embed)
                continue

            if winner == 0:
                if game.is_stalled():
                    await end_game()
                    embed.set_field_at(1, name="Status", value="Draw", inline=False)
                    await message.edit(embed=embed)
                    return
                else:
                    embed.description = self.draw_board()
                    embed.set_field_at(1, name="Status", value=f"{current_player.mention} dropped a disc on column {index+1}", inline=False)
                    await message.edit(embed=embed)
                    current_player = next(player_generate)
            else:
                await end_game()
                embed.description = self.draw_board()
                embed.set_field_at(1, name="Status", value=f"Game ended. Winner: {current_player.mention}", inline=False)
                await message.edit(embed=embed)
                return
