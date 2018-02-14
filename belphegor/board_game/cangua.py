import discord
from belphegor.utils import config
from . import dices
import random
from PIL import Image
from io import BytesIO
from pymongo import ReturnDocument
import asyncio

#==================================================================================================================================================

START_POINT = {"green": 1, "red": 13, "blue": 25, "yellow": 37}
TOWER_POINT = {"green": 101, "red": 111, "blue": 121, "yellow": 131}
HORSE_IMAGE = {color: {number: Image.open(f"{config.DATA_PATH}/game/cangua/{color}{number}.png") for number in (1, 2, 3, 4)} for color in START_POINT.keys()}

MAP_LOCATION = {}
for i in range(140):
    if i == 0:
        MAP_LOCATION[i] = (184, 348)
    elif 1 <= i <= 6:
        MAP_LOCATION[i] = (225, 375-25*i)
    elif 6 < i <= 11:
        MAP_LOCATION[i] = (75+25*i, 225)
    elif i == 12:
        MAP_LOCATION[i] = (350, 180)
    elif 13 <= i <= 18:
        MAP_LOCATION[i] = (675-25*i, 133)
    elif 18 < i <= 23:
        MAP_LOCATION[i] = (225, 584-25*i)
    elif i == 24:
        MAP_LOCATION[i] = (178, 9)
    elif 25 <= i <= 30:
        MAP_LOCATION[i] = (133, -616+25*i)
    elif 30 < i <= 35:
        MAP_LOCATION[i] = (884-25*i, 133)
    elif i == 36:
        MAP_LOCATION[i] = (9, 182)
    elif 37 <= i <= 42:
        MAP_LOCATION[i] = (-916+25*i, 225)
    elif 42 < i <= 47:
        MAP_LOCATION[i] = (133, -826+25*i)
    elif 100 < i < 107:
        MAP_LOCATION[i] = (165 + (i % 2) * 28, 322 - (i - 101) * 21)
    elif 110 < i < 117:
        MAP_LOCATION[i] = (322 - (i - 111) * 21, 179)
    elif 120 < i < 127:
        MAP_LOCATION[i] = (165 + (i % 2) * 28, 38 + (i - 121) * 21)
    elif 130 < i < 137:
        MAP_LOCATION[i] = (38 + (i - 131) * 21, 179)

DEFAULT_LOCATION = {
    "green": (292, 290),
    "red": (292, 35),
    "blue": (38, 35),
    "yellow": (38, 290)
}

#==================================================================================================================================================

class Horse:
    def __init__(self, *, color, number, current_position=-1):
        self.game = None
        self.color = color
        self.number = number
        self.current_position = current_position
        self.image_data = HORSE_IMAGE[color][number]

    def location(self):
        return MAP_LOCATION.get(
            self.current_position,
            (
                DEFAULT_LOCATION[self.color][0]+30*((self.number-1)//2),
                DEFAULT_LOCATION[self.color][1]+30*((self.number-1)%2)
            )
        )

#==================================================================================================================================================

class CaNguaPlayer:
    def __init__(self, *, member, color, horses):
        self.game = None
        self.member = member
        self.color = color
        self.horses = horses

    def __eq__(self, other):
        return self.member.id == other.member.id

    def to_dict(self):
        jsonable = {
            "member_id": self.member.id,
            "color": self.color,
            "horses": [{"number": h.number, "current_position": h.current_position} for h in self.horses]
        }
        return jsonable

#==================================================================================================================================================

class CaNgua:
    name = "co ca ngua"

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.rng = dices.Dices(6, 2)
        self.player_list = self.bot.db.board_game_player_list
        self.game_list = self.bot.db.board_game_list
        self.lock = asyncio.Lock()

    @classmethod
    async def new_game(cls, ctx, members):
        player_list = ctx.bot.db.board_game_player_list
        if len(members) > 4:
            await ctx.send("Too many players.")
            return None
        already_playing = [p["member_id"] async for p in player_list.find({"member_id": {"$in": [m.id for m in members]}})]
        if already_playing:
            await ctx.send(f"{' '.join((str(ctx.guild.get_member(m_id)) for m_id in already_playing))} already participated in another game.")
        colors = ['green', 'red', 'blue', 'yellow']
        players = []
        for member in members:
            if member.id not in already_playing:
                color = colors.pop(random.randrange(len(colors)))
                new_player = CaNguaPlayer(
                    member=member,
                    color=color,
                    horses=[
                        Horse(
                            color=color,
                            number=i
                        ) for i in (1, 2, 3, 4)
                    ]
                )
                players.append(new_player)
        if len(players) < 2:
            await ctx.send("Not enough players.")
            return None
        random.shuffle(players)
        new_game = cls(
            bot=ctx.bot, channel=ctx.channel, game_id=ctx.message.id, players=players,
            current_player=players[0], one_more=True, step=[], winner=None
        )
        for p in players:
            p.game = new_game
        await ctx.bot.db.board_game_list.insert_one({
            "game_class": "CaNgua",
            "game_id": new_game.game_id,
            "channel_id": new_game.channel.id,
            "players": [p.to_dict() for p in players],
            "current_player_id": players[0].member.id,
            "one_more": True,
            "steps": [],
            "winner_id": None
        })
        await ctx.bot.db.board_game_player_list.insert_many([{"member_id": p.member.id, "game_id": new_game.game_id} for p in players])
        return new_game

    @classmethod
    def load(cls, bot, game_data):
        guild = bot.get_channel(game_data["channel_id"]).guild
        players = []
        for player_data in game_data["players"]:
            member = guild.get_member(player_data["member_id"])
            players.append(
                CaNguaPlayer(
                    member=member,
                    color=player_data["color"],
                    horses=[
                        Horse(
                            color=player_data["color"],
                            number=horse_data["number"],
                            current_position=horse_data["current_position"]
                        ) for horse_data in player_data["horses"]
                    ]
                )
            )
        channel = bot.get_channel(game_data["channel_id"])
        current_player = None
        winner = None
        for p in players:
            if p.member.id == game_data["current_player_id"]:
                current_player = p
            if p.member.id == game_data["winner_id"]:
                winner = p
        game = cls(
            bot=bot, channel=channel, game_id=game_data["game_id"], players=players,
            current_player=current_player, one_more=game_data["one_more"], steps=game_data["steps"], winner=winner
        )
        for p in players:
            p.game = game
        return game

    def get_player(self, *, color=None, member_id=None):
        if color:
            for player in self.players:
                if player.color == color:
                    return player
        elif member_id:
            for player in self.players:
                if player.member.id == member_id:
                    return player

    def check_winner(self):
        if self.winner is None:
            for player in self.players:
                total = 0
                for horse in player.horses:
                    if horse.current_position > 100:
                        total += horse.current_position % 10
                if total == 18:
                    self.winner = player
                    return self.winner
            return None
        else:
            return self.winner

    async def knock_out(self, player):
        self.players.remove(player)
        await self.player_list.delete_one({"member_id": player.member.id})
        await self.game_list.update_one(
            {
                "game_id": self.game_id
            },
            {
                "$pull": {
                    "players": {
                        "$elemMatch": {
                            "member_id": player.member.id
                        }
                    }
                }
            }
        )
        await self.channel.send(f"{player.member.mention} left the game.")
        if len(self.players)== 1:
            await self.cmd_game_over()

    async def next_turn(self):
        index = (self.players.index(self.current_player) + 1) % len(self.players)
        self.current_player = self.players[index]
        self.one_more = True
        self.steps = []
        await self.game_list.update_one(
            {
                "game_id": self.game_id
            },
            {
                "$set": {
                    "current_player_id": self.current_player.member.id,
                    "one_more": True,
                    "steps": []
                }
            }
        )
        await self.channel.send(f"{self.current_player.member.mention}'s turn ({self.current_player.color}):")

    async def kick(self, horse):
        horse.current_position = -1
        player = self.get_player(color=horse.color)
        await self.game_list.update_one(
            {
                "game_id": self.game_id,
                "players": {
                    "$elemMatch": {
                        "member_id": player.member.id
                    }
                }
            },
            {
                "$set": {
                    "players.$": player.to_dict()
                }
            }
        )
        await self.channel.send(f"{self.get_player(color=horse.color).member.display_name}'s horse #{horse.number} was kicked.")

    async def cmd_roll(self):
        if self.one_more:
            self.steps = self.rng.roll()
            if self.steps[0] == self.steps[1] or (1 in self.steps and 6 in self.steps):
                self.one_more = True
            else:
                self.one_more = False
            await self.game_list.update_one(
                {
                    "game_id": self.game_id
                },
                {
                    "$set": {
                        "one_more": self.one_more,
                        "steps": self.steps
                    }
                }
            )
            await self.channel.send(f"You rolled {self.steps[0]} and {self.steps[1]}.")
        else:
            await self.channel.send("You can't roll at the moment.")

    async def cmd_move(self, ctx, number, step):
        if self.steps:
            current_horse = self.current_player.horses[number-1]
            if 0 <= current_horse.current_position < 48:
                other_players = [p for p in self.players if p.member.id!=self.current_player.member.id]
                if step in self.steps:
                    new_steps = [s for s in self.steps if s!=step]
                elif step == sum(self.steps):
                    new_steps = []
                else:
                    return await self.channel.send(f"You can't only move {' or '.join([str(s) for s in set(self.steps)|set([sum(self.steps)])])} step(s).")
                for player in self.players:
                    for horse in player.horses:
                        if 0 <= horse.current_position < 48:
                            if 0 < (horse.current_position - current_horse.current_position) % 48 < step:
                                return await self.channel.send("Something blocks the road.")
                if (START_POINT[current_horse.color] - 1 - current_horse.current_position) % 48 < 12:
                    if (current_horse.current_position + step - START_POINT[current_horse.color]) % 48 < 12:
                        sentences = {
                            "initial":  "You are about to overstep starting point. Process?"
                        }
                        check = await ctx.yes_no_prompt(sentences=sentences, delete_mode=True)
                        if not check:
                            return
                current_horse.current_position = (current_horse.current_position + step) % 48
                self.steps = new_steps
                await self.game_list.update_one(
                    {
                        "game_id": self.game_id,
                        "players": {
                            "$elemMatch": {
                                "member_id": self.current_player.member.id
                            }
                        }
                    },
                    {
                        "$set": {
                            "steps": self.steps,
                            "players.$": self.current_player.to_dict()
                        }
                    }
                )
                await self.channel.send(f"{self.current_player.member.display_name}'s horse #{number} moved {step} step(s) forward.")
                for player in other_players:
                    for horse in player.horses:
                        if horse.current_position == self.current_player.horses[number-1].current_position:
                            await self.kick(horse)
                            break
            else:
                await self.channel.send(f"You can't move horse #{number}.")
        else:
            await self.channel.send("You are out of move.")

    async def cmd_skip(self):
        await self.next_turn()

    async def cmd_go(self):
        go = 0
        for horse in self.current_player.horses:
            if horse.current_position == -1:
                go = horse.number
                break
        if go > 0:
            current_horse = self.current_player.horses[go-1]
            if self.one_more and len(self.steps)==2:
                for player in self.players:
                    for horse in player.horses:
                        if horse.current_position == START_POINT[current_horse.color]:
                            if horse.color == current_horse.color:
                                await self.channel.send("Another horse of you is on the starting point.")
                                return
                            else:
                                await self.kick(horse)
                                break
                current_horse.current_position = START_POINT[current_horse.color]
                self.steps = []
                await self.game_list.update_one(
                    {
                        "game_id": self.game_id,
                        "players": {
                            "$elemMatch": {
                                "member_id": self.current_player.member.id
                            }
                        }
                    },
                    {
                        "$set": {
                            "steps": self.steps,
                            "players.$": self.current_player.to_dict()
                        }
                    }
                )
                await self.channel.send(f"Horse #{go} go!")
            else:
                await self.channel.send("You are out of go.")
        else:
            await self.channel.send("All your horses are out.")

    async def cmd_game_over(self):
        if self.check_winner() is None:
            if len(self.players) > 1:
                possible_reactions = ("\u2705", "\u274c")
                all_member_ids = [p.member.id for p in self.players]
                msg = await self.channel.send(f"Do you want to end the game?\n{' '.join([p.member.mention for p in self.players])}")
                for r in possible_reactions:
                    self.bot.loop.create_task(msg.add_reaction(r))
                await asyncio.sleep(30)
                msg = await self.bot.get_message(msg.id)
                yay = 0
                nay = 0
                for r in msg.reactions:
                    if r.emoji == "\u2705":
                        yay = r.count
                    elif r.emoji == "\u274c":
                        nay = r.count
                if yay <= nay:
                    await self.channel.send("Poll ended.\nThe game won't end for now.")
        else:
            await self.channel.send(embed=discord.Embed(title=f"Winner: {self.winner.member.display_name}"))
        self.players.clear()
        await self.player_list.delete_many({"game_id": self.game_id})
        await self.game_list.update_one({"game_id": self.game_id}, {"$set": {"players": []}})
        await self.channel.send(f"This round of co ca ngua is over.")

    async def cmd_climb(self, number, step):
        if step in self.steps:
            current_horse = self.current_player.horses[number-1]
            if current_horse.current_position == START_POINT[self.current_player.color] - 1:
                pass
            elif TOWER_POINT[current_horse.color] + 5 > current_horse.current_position >= TOWER_POINT[current_horse.color]:
                if current_horse.current_position != TOWER_POINT[current_horse.color] + step - 2:
                    return await self.channel.send("You must climb step by step.")
            elif current_horse.current_position == TOWER_POINT[current_horse.color] + 5:
                return await self.channel.send(f"Horse #{number} cannot climb anymore.")
            else:
                return await self.channel.send(f"Horse #{number} is not at the base of the tower.")
            for horse in self.current_player.horses:
                if horse.current_position - current_horse.current_position == 1:
                    return await self.channel.send("One of your horses blocks the way up.")
            current_horse.current_position = TOWER_POINT[current_horse.color] + step - 1
            self.steps.remove(step)
            await self.game_list.update_one(
                {
                    "game_id": self.game_id,
                    "players": {
                        "$elemMatch": {
                            "member_id": self.current_player.member.id
                        }
                    }
                },
                {
                    "$set": {
                        "steps": self.steps,
                        "players.$": self.current_player.to_dict()
                    }
                }
            )
            await self.channel.send(f"Horse #{current_horse.number} climbed to {step}.")
        else:
            await self.channel.send(f"Horse #{number} can't climb to {step}.")

    async def cmd_map(self):
        def image_process():
            new_map = Image.open(f"{config.DATA_PATH}/game/cangua/map.png")
            for player in self.players:
                for horse in player.horses:
                    new_map.paste(horse.image_data, horse.location(), mask=horse.image_data)
            pic = BytesIO()
            new_map.save(pic, format="png")
            return pic

        current_map = await self.bot.run_in_lock(self.lock, image_process)
        await self.channel.send(file=discord.File(current_map.getvalue(), filename="current_map.png"))

    async def cmd_info_turn(self):
        await self.channel.send(f"It's currently {self.current_player.member.mention}'s turn.")

    async def cmd_abandon(self, author_id):
        player = self.get_player(member_id=author_id)
        if len(self.players) > 2:
            if player == self.current_player:
                await self.next_turn()
        await self.knock_out(player)
