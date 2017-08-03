import discord
from discord.ext import commands
from . import dices
import random
from PIL import Image
import os
from io import BytesIO
from belphegor.utils import config
import json
import asyncio


class Horse:
    def __init__(self, game_id, color, number):
        self.color = color
        self.number = number
        self.current_position = -1
        self.game_id = game_id



class Player:
    def __init__(self, game_id, member, color):
        self.game_id = game_id
        self.member = member
        self.color = color
        self.horses = [Horse(self.game_id, self.color, 1),
                       Horse(self.game_id, self.color, 2),
                       Horse(self.game_id, self.color, 3),
                       Horse(self.game_id, self.color, 4)]
        self.game = "Co Ca Ngua"

    def __eq__(self, other):
        return self.member.id == other.member.id

    def save(self):
        jsonable = {"module": "cangua",
                    "game": "CoCaNgua",
                    "game_id": self.game_id,
                    "member_id": self.member.id,
                    "color": self.color,
                    "horses": [h.__dict__ for h in self.horses]}
        with open(config.data_path+"game\\player\\"+str(self.member.id)+".json", "w+") as file:
            json.dump(jsonable, file)

    @classmethod
    def load(cls, bot, data):
        member = bot.get_user(data["member_id"])
        player = cls(data["game_id"], member, data["color"])
        horses = []
        for horse_data in data["horses"]:
            horse = Horse(horse_data["game_id"], horse_data["color"], horse_data["number"])
            horse.current_position = horse_data["current_position"]
            horses.append(horse)
        player.horses = horses
        return player

class CoCaNgua:
    def __init__(self, bot, channel, game_id, players):
        self.bot = bot
        self.start_point = {'green':1, 'red':13, 'blue':25, 'yellow':37}
        self.tower_point = {'green':101, 'red':111, 'blue':121, 'yellow':131}
        self.players = players
        self.RNG = dices.Dices(6,2)
        self.current_player = self.players[0]
        self.move = 0
        self.game_id = game_id
        self.steps = []
        self.channel = channel
        self.winner = None

    def save(self):
        try:
            winner_id = self.winner.member.id
        except:
            winner_id = None
        jsonable = {"module": "cangua",
                    "game": "CoCaNgua",
                    "game_id": self.game_id,
                    "players": [p.member.id for p in self.players],
                    "current_player_id": self.current_player.member.id,
                    "move": self.move,
                    "steps": self.steps,
                    "channel_id": self.channel.id,
                    "winner_id": winner_id,
                    "rolls": self.RNG.rolls}
        with open(config.data_path+"game\\savedata\\"+str(self.game_id)+".json", "w+") as file:
            json.dump(jsonable, file)
        for p in self.players:
            p.save()

    @classmethod
    def load(cls, bot, data):
        players = []
        for p_id in data["players"]:
            with open(config.data_path+"game\\player\\"+str(p_id)+".json") as file:
                d = json.load(file)
                player = Player.load(bot, d)
                players.append(player)
        channel = bot.get_channel(data["channel_id"])
        game = cls(bot, channel, data["game_id"], players)
        for p in players:
            if p.member.id == data["current_player_id"]:
                game.current_player = p
                break
        game.move = data["move"]
        game.steps = data["steps"]
        game.RNG.rolls = data["rolls"]
        for p in players:
            if p.member.id == data["winner_id"]:
                game.winner = p
                break
        return game

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
        else:
            return self.winner

    async def knock_out(self, player):
        self.players.remove(player)
        os.remove(config.data_path+"game\\player\\"+str(player.member.id)+".json")
        if len(self.players)== 1:
            await self.cmd_game_over()

    async def next_turn(self):
        index = (self.players.index(self.current_player) + 1) % len(self.players)
        self.current_player = self.players[index]
        self.move = 0
        self.steps[:] = []
        await self.channel.send("{}'s turn ({}):".format(self.current_player.member.mention, self.current_player.color))

    async def kick(self, horse):
        horse.current_position = -1
        owner = {}
        for player in self.players:
            owner[player.color] = player
        await self.channel.send("{}'s horse #{} was kicked.".format(owner[horse.color].member.display_name, horse.number))

    async def cmd_roll(self):
        if self.move >= 0:
            self.RNG.roll()
            self.steps = self.RNG.rolls[:]
            if self.steps in [[1,1],[2,2],[3,3],[4,4],[5,5],[6,6],[6,1],[1,6]]:
                self.move = 1
            else:
                self.move = -1
            await self.channel.send("You rolled {0.steps[0]} and {0.steps[1]}.".format(self))
        else:
            await self.channel.send("You can't roll anymore.")

    async def cmd_move(self, number, step):
        if self.steps:
            if 0 <= self.current_player.horses[number-1].current_position < 48:
                other_players = self.players[:]
                other_players.remove(self.current_player)
                if step in self.steps:
                    for player in self.players:
                        for horse in player.horses:
                            if 0 <= horse.current_position <= 47:
                                if 0 < (horse.current_position - self.current_player.horses[number-1].current_position) % 48 < step:
                                    await self.channel.send("Something blocks the road.")
                                    return
                    self.current_player.horses[number-1].current_position = (self.current_player.horses[number-1].current_position + step) % 48
                    self.steps.remove(step)
                    await self.channel.send("Horse #{} moved {} step(s) forward.".format(number, step))
                    for player in other_players:
                        for horse in player.horses:
                            if horse.current_position == self.current_player.horses[number-1].current_position:
                                await self.kick(horse)
                                break
                elif step == self.steps[0] + self.steps[1]:
                    for player in self.players:
                        for horse in player.horses:
                            if 0 <= horse.current_position <= 47:
                                if 0 < (horse.current_position - self.current_player.horses[number-1].current_position) % 48 < step:
                                    await self.channel.send("Something blocks the road.")
                                    return
                    self.current_player.horses[number-1].current_position = (self.current_player.horses[number-1].current_position + step) % 48
                    self.steps[:] = []
                    await self.channel.send("Horse #{} moved {} step(s) forward.".format(number, step))
                    for player in other_players:
                        for horse in player.horses:
                            if horse.current_position == self.current_player.horses[number-1].current_position:
                                await self.kick(horse)
                                break
                else:
                    await self.channel.send("You can't only move {} step(s).".format(' or '.join([str(self.steps[0]), str(self.steps[1]), str(self.step[0] + self.step[1])])))
            else:
                await self.channel.send("You can't move horse #{}.".format(number))
        else:
            await self.channel.send("You can't move #{} at the moment.".format(number))

    async def cmd_skip(self):
        await self.next_turn()

    async def cmd_go(self):
        go = 0
        for horse in self.current_player.horses:
            if horse.current_position == -1:
                go = horse.number
                break
        if go > 0:
            if self.move > 0 and len(self.steps)==2:
                for player in self.players:
                    for horse in player.horses:
                        if horse.current_position == self.start_point[self.current_player.color]:
                            if horse.color == self.current_player.color:
                                await self.channel.send("Another horse of you is on the starting point.")
                                return
                            else:
                                await self.kick(horse)
                                break
                self.current_player.horses[go-1].current_position = self.start_point[self.current_player.color]
                self.steps[:] = []
                self.move = 0
                await self.channel.send("Horse #{} go!".format(go))
            else:
                await self.channel.send("You can't let horse out.")
        else:
            await self.channel.send("All your horses are out.")

    async def cmd_game_over(self):
        if self.check_winner() is None:
            if len(self.players) > 1:
                for player in self.players:
                    await self.channel.send("Would {} want to end the game? y/n".format(player.member.mention))
                    while True:
                        msg = await self.bot.wait_for_message(author = player.member)
                        if msg.content.strip().lower() == 'y':
                            break
                        elif msg.content.strip().lower() == 'n':
                            await self.channel.send("Then it won't end for now.")
                            return
                        else:
                            pass
        else:
            await self.channel.send(embed=discord.Embed(title="Winner: {}".format(self.winner.member.display_name)))
        for player in self.players[:]:
            self.players.remove(player)
            os.remove(config.data_path+"game\\player\\"+str(player.member.id)+".json")
        await self.channel.send("#{} Co ca ngua over.".format(self.game_id))

    async def cmd_climb(self, number, step):
        if step in self.steps:
            current_horse = self.current_player.horses[number-1]
            if current_horse.current_position == self.start_point[self.current_player.color] - 1:
                for horse in self.current_player.horses:
                    if 0<horse.current_position - current_horse.current_position - self.tower_point[current_horse.color] + self.start_point[current_horse.color]<=step:
                        await self.channel.send("Something blocks the way up.")
                        return
                current_horse.current_position = self.tower_point[current_horse.color] + step - 1
                self.steps.remove(step)
                await self.channel.send("Horse #{} climbed to {}.".format(current_horse.number, step))
            elif self.tower_point[current_horse.color] + 5 > current_horse.current_position >= self.tower_point[current_horse.color]:
                if current_horse.current_position + 2 == self.tower_point[current_horse.color] + step:
                    for horse in self.current_player.horses:
                        if horse.current_position - current_horse.current_position == 1:
                            await self.channel.send("Something blocks the way up.")
                            return
                    current_horse.current_position += 1
                    self.steps.remove(step)
                    await self.channel.send("Horse #{} climbed to {}.".format(current_horse.number, step))
                else:
                    await self.channel.send("You must climb step by step.")
            elif current_horse.current_position == self.tower_point[current_horse.color]+5:
                await self.channel.send("It cannot climb anymore.")
            else:
                await self.channel.send("It's not at the base of the tower.")
        else:
            await self.channel.send("You can't move #{}.".format(number))


    def location(self, horse):
        if horse.current_position == 0:
            return [184, 348]
        elif 1 <= horse.current_position <= 6:
            return [225, 375-25*horse.current_position]
        elif 6 < horse.current_position <= 11:
            return [75+25*horse.current_position, 225]
        elif horse.current_position == 12:
            return [350, 180]
        elif 13 <= horse.current_position <= 18:
            return [675-25*horse.current_position, 133]
        elif 18 < horse.current_position <= 23:
            return [225, 584-25*horse.current_position]
        elif horse.current_position == 24:
            return [178, 9]
        elif 25 <= horse.current_position <= 30:
            return [133, -616+25*horse.current_position]
        elif 30 < horse.current_position <= 35:
            return [884-25*horse.current_position, 133]
        elif horse.current_position == 36:
            return [9, 182]
        elif 37 <= horse.current_position <= 42:
            return [-916+25*horse.current_position, 225]
        elif 42 < horse.current_position <= 47:
            return [133, -826+25*horse.current_position]
        elif 100 < horse.current_position < 107:
            return [165 + (horse.current_position % 2) * 28, 322 - (horse.current_position - 101) * 21]
        elif 110 < horse.current_position < 117:
            return [322 - (horse.current_position - 111) * 21, 179]
        elif 120 < horse.current_position < 127:
            return [165 + (horse.current_position % 2) * 28, 38 + (horse.current_position - 121) * 21]
        elif 130 < horse.current_position < 137:
            return [38 + (horse.current_position - 131) * 21, 179]
        else:
            if horse.color == "green":
                return [292+30*((horse.number-1)//2), 290+30*((horse.number-1)%2)]
            elif horse.color == "red":
                return [292+30*((horse.number-1)//2), 35+30*((horse.number-1)%2)]
            elif horse.color == "blue":
                return [38+30*((horse.number-1)//2), 35+30*((horse.number-1)%2)]
            elif horse.color == "yellow":
                return [38+30*((horse.number-1)//2), 290+30*((horse.number-1)%2)]

    async def cmd_map(self):
        current_map = Image.open("data\\game\\cangua\\map.png")
        def image_process():
            for player in self.players:
                for horse in player.horses:
                    horse_pic = Image.open("data\\game\\cangua\\{}{}.png".format(horse.color, horse.number))
                    try:
                        current_map.paste(horse_pic, self.location(horse), mask=horse_pic)
                    except:
                        pass
        await self.bot.loop.run_in_executor(None, image_process)
        pic = BytesIO()
        current_map.save(pic, format = "png")
        pic.seek(0)
        await self.channel.send(file=discord.File(pic, filename="current_map.png"))

    async def cmd_info_turn(self):
        await self.channel.send("It's currently {}'s turn.".format(self.current_player.member.mention))
