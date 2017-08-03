import discord
from discord.ext import commands
import random
from pathlib import Path
from belphegor.game import dices


class Land():
    def __init__(self, game_count, position, land_type, name, group = None, buy_price = None, rent_price = None):
        self.name = name
        self.group = group
        self.owner = None
        self.level = -2
        self.land_type = land_type
        self.buy_price = buy_price
        self.rent_price = rent_price
        self.game_count = game_count
        self.position = position

    def __call__(self):
        return self.name



class Player:
    def __init__(self, game_count, token, member, money=1500):
        self.token = token
        self.member = member
        self.money = money
        self.owned_properties = []
        self.number_of_jailcards = 0
        self.in_jail = False
        self.jail_time = 0
        self.current_position = 0
        self.game_count = game_count
        self.game = "Monopoly"

    def __call__(self):
        return self.member.display_name

    def is_hopeless(self):
        if not self.owned_properties:
            if self.number_of_jailcards > 0:
                return False
            else:
                return True
        else:
            for land in self.owned_properties:
                if land.level >= 0:
                    return False
            return True

    def total_assets(self):
        total = self.money
        for land in self.owned_properties:
            if land.land_type == 'Street':
                if land.level == -1:
                    total += land.buy_price[0] // 2
                else:
                    total += land.buy_price[0] + land.buy_price[1] * land.level
            elif land.land_type in ('Utility', 'Railroad'):
                if land.level == -1:
                    total += land.buy_price[0] // 2
                else:
                    total += land.buy_price[0]
        total += self.number_of_jailcards * 50
        return total



class Debt:
    def __init__(self, debtor, amount, creditor=None):
        self.debtor = debtor
        self.amount = amount
        self.creditor = creditor

    def __call__(self):
        return self.amount



class Monopoly:
    def __init__(self, bot, parent, game_count, players, auction=False, max_houses=32, max_hotels=12):
        self.bot = bot
        self.players = players
        self.lands = (Land(game_count,  0,  'Go',        'Go'),
                      Land(game_count,  1,  'Street',    'Pokemon',              'Green',    (60,50),    (2,10,30,90,180,270)),
                      Land(game_count,  2,  'Chest',     'Yandere',              'Card'),
                      Land(game_count,  3,  'Street',    'Digimon',              'Green',    (70,50),    (4,20,60,180,360,480)),
                      Land(game_count,  4,  'Tax',       'Trapped in a Pyramid Scheme'),
                      Land(game_count,  5,  'Railroad',  'Toei Animation',       'Studio',   (230,),     (25,50,100,200)),
                      Land(game_count,  6,  'Street',    'One Piece',            'Orange',   (100,50),   (6,30,90,270,420,550)),
                      Land(game_count,  7,  'Chance',    'Tsundere'),
                      Land(game_count,  8,  'Street',    'Naruto',               'Orange',   (100,50),   (6,30,90,270,420,550)),
                      Land(game_count,  9,  'Street',    'Dragon Ball Z',        'Orange',   (120,50),   (8,40,120,320,450,600)),
                      Land(game_count,  10, 'Jail',      'Lolicon jail'),
                      Land(game_count,  11, 'Street',    'Mushi-shi',            'Grey',     (140,100),  (10,50,150,450,600,750)),
                      Land(game_count,  12, 'Utility',   'Bishoujo Zone',        'Zone',     (170,),     (4, 10)),
                      Land(game_count,  13, 'Street',    'Fullmetal Alchemist',  'Grey',     (140,100),  (10,50,150,450,600,750)),
                      Land(game_count,  14, 'Street',    'Castle in the Sky',    'Grey',     (160,100),  (12,60,180,500,700,900)),
                      Land(game_count,  15, 'Railroad',  'Studio Ghibli',        'Studio',   (230,),     (25,50,100,200)),
                      Land(game_count,  16, 'Street',    'Texhnolyze',           'Black',    (180,100),  (14,70,210,600,750,950)),
                      Land(game_count,  17, 'Street',    'Metropolis',           'Black',    (180,100),  (14,70,210,600,750,950)),
                      Land(game_count,  18, 'Chest',     'Yandere'),
                      Land(game_count,  19, 'Street',    'Ghost in the Shell',   'Black',    (200,100),  (16,80,240,600,800,1050)),
                      Land(game_count,  20, 'Parking',   'Anime art'),
                      Land(game_count,  21, 'Street',    'Princess Mononoke',    'Yellow',   (220,150),  (18,90,270,710,930,1080)),
                      Land(game_count,  22, 'Chance',    'Tsundere'),
                      Land(game_count,  23, 'Street',    'Gurren Lagann',        'Yellow',   (220,150),  (18,90,270,710,930,1080)),
                      Land(game_count,  24, 'Street',    'Redline',              'Yellow',   (240,150),  (20,100,300,775,950,1150)),
                      Land(game_count,  25, 'Railroad',  'Madhouse',             'Studio',   (230,),     (25,50,100,200)),
                      Land(game_count,  26, 'Street',    'Trigun',               'Red',      (260,150),  (22,110,330,790,1000,1180)),
                      Land(game_count,  27, 'Street',    'Outlaw Star',          'Red',      (260,150),  (22,110,330,790,1000,1180)),
                      Land(game_count,  28, 'Utility',   'Bishounen Zone',       'Zone',     (170,),     (4, 10)),
                      Land(game_count,  29, 'Street',    'Cowboy Bebop',         'Red',      (280,150),  (24,120,360,820,1040,1250)),
                      Land(game_count,  30, 'Go jail',   'Go to jail'),
                      Land(game_count,  31, 'Street',    'Speed Grapher',        'Purple',   (300,200),  (26,130,390,890,1111,1300)),
                      Land(game_count,  32, 'Street',    'Code Geass',           'Purple',   (300,200),  (26,130,390,890,1111,1300)),
                      Land(game_count,  33, 'Chest',     'Yandere'),
                      Land(game_count,  34, 'Street',    'Darker Than Black',    'Purple',   (320,200),  (30,150,450,950,1250,1430)),
                      Land(game_count,  35, 'Railroad',  'BONES',                'Studio',   (230,),     (25,50,100,200)),
                      Land(game_count,  36, 'Chance',    'Tsundere'),
                      Land(game_count,  37, 'Street',    'Bandai',               'Brown',    (360,200),  (35,175,525,1150,1400,1600)),
                      Land(game_count,  38, 'Tax',       'Maintain your Persocom'),
                      Land(game_count,  39, 'Street',    'Funimation',           'Brown',    (420,200),  (45,200,600,1200,1500,1800)))
        self.current_player = self.players[0]
        self.phase = 0
        self.RNG = dices.Dices(6,2)
        self.game_count = game_count
        self.doubles = 0
        self.phase = 0
        self.available_houses = max_houses
        self.available_hotels = max_hotels
        self.parent = parent
        self.debts = []
        self.chest_jail = 1
        self.chance_jail = 1

    async def knock_out(self, player):
        for land in player.owned_properties:
            land.owner = None
            land.level = -2
        for debt in self.debts[:]:
            if debt.debtor is player:
                if debt.creditor is not None:
                    debt.creditor.money += debt.amount
                    await self.bot.say("{} received ${}.".format(debt.creditor.member.display_name, debt.amount))
                self.debts.remove(debt)
            elif debt.creditor is player:
                debt.creditor = None
        if player is self.current_player:
            await self.next_turn()
        self.players.remove(player)
        self.parent.players.remove(player)
        if len(self.players) == 1:
            await self.cmd_game_over()

    async def next_turn(self):
        if not self.debts:
            if self.current_player.in_jail:
                self.current_player.jail_time += 1
            self.doubles = 0
            index = (self.players.index(self.current_player) + 1) % len(self.players)
            self.current_player = self.players[index]
            self.phase = 0
            await self.bot.say("{}'s turn:".format(self.current_player.member.mention))
        else:
            await self.force_pay()

    async def move(self, step):
        new_position = self.current_player.current_position + step
        self.current_player.current_position = new_position % 40
        self.phase = 1
        await self.bot.say("You moved {} steps and landed on #{} {}.".format(step, self.current_player.current_position, self.lands[self.current_player.current_position].name))
        if new_position >= 40:
            self.current_player.money += 200
            await self.bot.say("You passed Go and got $200.")
        land = self.lands[self.current_player.current_position]
        if land.land_type in ("Street", "Utility", "Railroad"):
            if land.owner is not None:
                if land.owner is not self.current_player:
                    if land.level >= 0:
                        self.debts.append(Debt(self.current_player, self.rent_price(land), land.owner))
                        await self.force_pay()
        elif land.land_type == "Chance":
            return await self.chance()
        elif land.land_type == "Chest":
            return await self.chest()
        elif land.land_type == 'Tax':
            if land is self.lands[4]:
                self.debts.append(Debt(self.current_player, 200))
                await self.force_pay()
            else:
                self.debts.append(Debt(self.current_player, 75))
                await self.force_pay()
        elif land.land_type == 'Go jail':
            await self.go_to_jail()
            return True
        return False

    async def chance(self):
        card = random.randint(1, 16)
        if card == 1:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun01.png")
            await self.bot.upload(pic)
            other_players = self.players[:]
            other_players.remove(self.current_player)
            for player in other_players:
                self.debts.append(Debt(self.current_player, 40, player))
            if self.debts:
                await self.force_pay()
        elif card == 2:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun02.png")
            await self.bot.upload(pic)
            await self.bot.say("Where will you go to?\n"
                               "```\n1. Square 16 - Texhnolyze\n"
                               "2. Square 17 - Metropolis\n"
                               "3. Square 19 - Ghost in the Shell\n```")
            while True:
                msg = await self.bot.wait_for_message(author = self.current_player.member)
                if msg.content.strip() == '1':
                    await self.move((16 - self.current_player.current_position) % 40)
                    break
                elif msg.content.strip() == '2':
                    await self.move((17 - self.current_player.current_position) % 40)
                    break
                elif msg.content.strip() == '3':
                    await self.move((19 - self.current_player.current_position) % 40)
                    break
        elif card == 3:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun03.png")
            await self.bot.upload(pic)
            self.current_player.money += 100
            await self.bot.say("You got $100.")
        elif card == 4:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun04.png")
            await self.bot.upload(pic)
            await self.move(-3)
        elif card == 5:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun05.png")
            await self.bot.upload(pic)
            await self.move((39 - self.current_player.current_position) % 40)
        elif card == 6:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun06.png")
            await self.bot.upload(pic)
            unowned_lands = []
            for land in self.lands:
                if land.land_type in ("Street", "Railroad", "Utility"):
                    if land.owner is None:
                        unowned_lands.append(land)
            if not unowned_lands:
                self.move((5 - self.current_player.current_position) % 10)
            else:
                textout = ""
                for land_index in range(len(unowned_lands)):
                    textout = "{}\n{}. Square {} - {}".format(textout, land_index+1, unowned_lands[land_index].position, unowned_lands[land_index].name)
                await self.bot.say("Where will you go to?\n```{}\n```".format(textout))
                while True:
                    msg = await self.bot.wait_for_message(author = self.current_player.member)
                    try:
                        if int(msg.content.strip() - 1) in range(len(unowned_lands)):
                            await self.move((unowned_lands[int(msg.content.strip()) - 1].position - self.current_player.current_position) % 40)
                            break
                    except:
                        pass
        elif card == 7:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun07.png")
            await self.bot.upload(pic)
            await self.go_to_jail()
        elif card == 8:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun08.png")
            await self.bot.upload(pic)
            textout = ""
            other_players = self.players[:]
            other_players.remove(self.current_player)
            for player_index in range(len(other_players)):
                textout = "{}\n{}. {} - {}".format(textout, player_index+1, other_players[player_index].member.display_name, self.lands[other_players[player_index].current_position].name)
            await self.bot.say("Where would you go to?\n```{}\n```".format(textout))
            while True:
                msg = await self.bot.wait_for_message(author = self.current_player.member)
                try:
                    if (int(msg.content.strip())-1) in range(len(other_players)):
                        self.current_player.current_position = other_players[int(msg.content.strip())-1].current_position
                        await self.bot.say("You are now at {}.".format(self.lands[self.current_player.current_position].name))
                        break
                except:
                    pass
        elif card == 9:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun09.png")
            await self.bot.upload(pic)
            single_dice = random.randint(1, 6)
            await self.bot.say("You rolled {}.".format(single_dice))
            await self.move(single_dice)
        elif card == 10:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun10.png")
            await self.bot.upload(pic)
            await self.bot.say("Would you choose odd or even?")
            while True:
                msg = await self.bot.wait_for_message(author = self.current_player.member)
                if msg.content.strip().lower() == 'odd':
                    even = 1
                    break
                elif msg.content.strip().lower() == 'even':
                    even = 0
                    break
            single_dice = random.randint(1, 6)
            await self.bot.say("You rolled {}.".format(single_dice))
            if single_dice % 2 == even:
                self.current_player.money += 200
                await self.bot.say("You guessed right and gained $200.")
            else:
                self.debts.append(Debt(self.current_player, 150))
                await self.force_pay()
        elif card == 11:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun11.png")
            await self.bot.upload(pic)
            await self.bot.say("Type a square number to go to.")
            while True:
                msg = await self.bot.wait_for_message(author = self.current_player.member)
                try:
                    if int(msg.content.strip()) in range(40):
                        self.current_player.current_position = int(msg.content.strip())
                        await self.bot.say("You are now at {}.".format(self.lands[self.current_player.current_position].name))
                        break
                except:
                    pass
            self.debts.append(Debt(self.current_player, 30))
            await self.force_pay()
        elif card == 12:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun12.png")
            await self.bot.upload(pic)
            await self.next_turn()
        elif card == 13:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun13.png")
            await self.bot.upload(pic)
            await self.move(40 - self.current_player.current_position)
        elif card == 15:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun15.png")
            await self.bot.upload(pic)
            self.current_player.current_position = 35
            await self.bot.say("You are now at {}.".format(self.lands[35].name))
        elif card == 16:
            await self.bot.say("You drew a Tsundere card.")
            pic = Path("data\\monopoly\\ccc\\tsun16.png")
            await self.bot.upload(pic)
            total_pay = 0
            for land in self.current_player.owned_properties:
                if land.land_type == "Street":
                    if 0 < land.level < 5:
                        total_pay += 40 * land.level
                    elif land.level == 5:
                        total_pay += 115
            if total_pay > 0:
                self.debts.append(Debt(self.current_player, total_pay))
                await self.force_pay()
            else:
                await self.bot.say("You lucked out and didn't have to pay anything.")
        elif card == 17:
            if self.chance_jail == 1:
                await self.bot.say("You drew a Tsundere card.")
                pic = Path("data\\monopoly\\ccc\\tsun17.png")
                await self.bot.upload(pic)
                self.current_player.number_of_jailcards += 1
                self.chance_jail = 0
            else:
                await self.chance()
        else:
            await self.chance()

    async def chest(self):
        card = random.randint(1, 17)
        if card == 1:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan01.png")
            await self.bot.upload(pic)
            self.current_player.money += 100
            await self.bot.say("You gained $100.")
        elif card == 2:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan02.png")
            await self.bot.upload(pic)
            self.debts.append(Debt(self.current_player, 75))
            await self.force_pay()
        elif card == 3:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan03.png")
            await self.bot.upload(pic)
            self.debts.append(Debt(self.current_player, 50))
            await self.force_pay()
        elif card == 5:
            if self.chest_jail == 1:
                await self.bot.say("You drew a Yandere card.")
                pic = Path("data\\monopoly\\ccc\\yan05.png")
                await self.bot.upload(pic)
                self.current_player.number_of_jailcards += 1
                self.chest_jail = 0
            else:
                await self.chest()
        elif card == 6:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan06.png")
            await self.bot.upload(pic)
            self.current_player.money += 150
            await self.bot.say("You gained $150.")
        elif card == 7:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan07.png")
            await self.bot.upload(pic)
            self.current_player.money += 160
            await self.bot.say("You gained $160.")
        elif card == 8:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan08.png")
            await self.bot.upload(pic)
            self.debts.append(Debt(self.current_player, 120))
            await self.force_pay()
        elif card == 9:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan09.png")
            await self.bot.upload(pic)
            self.debts.append(Debt(self.current_player, 80))
            await self.force_pay()
        elif card == 10:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan10.png")
            await self.bot.upload(pic)
            self.current_player.money += 20 * len(self.current_player.owned_properties)
            await self.bot.say("You gained ${}.".format(20 * len(self.current_player.owned_properties)))
        elif card == 11:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan11.png")
            await self.bot.upload(pic)
            self.current_player.money += 180
            await self.bot.say("You gained $180.")
        elif card == 12:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan12.png")
            await self.bot.upload(pic)
            await self.go_to_jail()
        elif card == 13:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan13.png")
            await self.bot.upload(pic)
            self.debts.append(Debt(self.current_player, 200))
            await self.force_pay()
        elif card == 14:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan14.png")
            await self.bot.upload(pic)
            other_players = self.players[:]
            other_players.remove(self.current_player)
            for player in other_players:
                self.debts.append(Debt(player, 30, self.current_player))
            await self.force_pay()
        elif card == 15:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan15.png")
            await self.bot.upload(pic)
            self.current_player.money += 130
            await self.bot.say("You gained $130.")
        elif card == 16:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan16.png")
            await self.bot.upload(pic)
            self.current_player.money += 140
            await self.bot.say("You gained $140.")
        elif card == 17:
            await self.bot.say("You drew a Yandere card.")
            pic = Path("data\\monopoly\\ccc\\yan17.png")
            await self.bot.upload(pic)
            self.current_player.money += 100
            await self.bot.say("You gained $100.")
        else:
            await self.chest()

    async def force_pay(self):
        if self.debts:
            self.phase = -1
            for debt in self.debts[:]:
                if debt.debtor.money >= debt.amount:
                    debt.debtor.money -= debt.amount
                    await self.bot.say("{} paid ${}.".format(debt.debtor.member.display_name, debt.amount))
                    if debt.creditor is not None:
                        debt.creditor.money += debt.amount
                        await self.bot.say("{} received ${}.".format(debt.creditor.member.display_name, debt.amount))
                    self.debts.remove(debt)
                elif debt.debtor.is_hopeless():
                    if debt.debtor in self.players:
                        await self.bot.say("{} went bankrupt and dropped out off the game.".format(debt.debtor.member.display_name))
                        self.knock_out(player)
                    if debt.creditor is not None:
                        debt.creditor.money += debt.amount
                        await self.bot.say("{} received ${}.".format(debt.creditor.member.display_name, debt.amount))
                else:
                    debt.amount -= debt.debtor.money
                    if debt.creditor is not None:
                        debt.creditor.money += debt.debtor.money
                        await self.bot.say("{} received ${}.".format(debt.creditor.member.display_name, debt.debtor.money))
                    debt.debtor.money = 0
                    await self.bot.say("{} is broke and has a debt of ${}. Please sell you properties to pay the debt.".format(debt.debtor.member.display_name, debt.amount))
            if self.debts:
                return
            else:
                self.phase = 1

    def find_land(self, *args):
        for land in self.lands:
            result = land
            for arg in args:
                if arg.lower() not in land.name.lower():
                    result = None
                    break
            if result is not None:
                break
        return result

    async def sell_street(self, land, sell_all=False):
        if not sell_all:
            if land.level > 0:
                land.level -= 1
                land.owner.money += land.buy_price[1] // 2
                if land.level == 5:
                    await self.bot.say("You sold a hotel in {} for ${}".format(land.name, land.buy_price[1]//2))
                else:
                    await self.bot.say("You sold a house in {} for ${}".format(land.name, land.buy_price[1]//2))
            elif land.level == 0:
                land.level = -1
                land.owner.money += land.buy_price[0] // 2
                await self.bot.say("You mortgaged {} for ${}".format(land.name, land.buy_price[0]//2))
        else:
            if land.level == 5:
                land.level = 0
                land.owner.money += land.buy_price[1] * 5 // 2

    async def sell_railroad(self, land):
        for other in (self.lands[5], self.lands[15], self.lands[25], self.lands[35]):
            if other.owner is land.owner:
                other.level -= 1
        land.level = -1
        land.owner.money += land.buy_price[0] // 2
        await self.bot.say("You mortgaged {} for ${}".format(land.name, land.buy_price[0]//2))

    async def sell_utility(self, land):
        if land is self.lands[12]:
            if land.owner is self.lands[28].owner:
                self.lands[28].level = 0
        elif land is self.lands[28]:
            if land.owner is self.lands[12].owner:
                self.lands[12].level = 0
        land.level = -1
        land.owner.money += land.buy_price[0] // 2
        await self.bot.say("You mortgaged {} for ${}".format(land.name, land.buy_price[0]//2))

    def rent_price(self, land):
        if land.land_type in ("Street", "Railroad"):
            return land.rent_price[land.level]
        elif land.land_type == "Utility":
            return self.RNG.total()*land.rent_price[land.level]

    async def go_to_jail(self):
        self.current_player.current_position = 10
        self.current_player.in_jail = True
        self.current_player.jail_time = 0
        await self.bot.say("You got arrested.")
        await self.next_turn()

    async def cmd_game_over(self):
        if len(self.players) > 1:
            for player in self.players:
                await self.bot.say("Would {} want to end the game? y/n".format(player.member.mention))
                while True:
                    msg = await self.bot.wait_for_message(author = player.member)
                    if msg.content.strip().lower() == 'y':
                        break
                    elif msg.content.strip().lower() == 'n':
                        await self.bot.say("Then it won't end for now.")
                        return
                    else:
                        pass
        await self.bot.say("#{} Monopoly over.".format(self.game_count))
        richest = max([o.total_assets() for o in self.players])
        await self.bot.say("This round winner(s):")
        for player in self.players[:]:
            if player.total_assets() == richest:
                await self.bot.say(player.member.mention)
            self.parent.players.remove(player)
            self.players.remove(player)
        await self.bot.say("Gratz!")

    async def cmd_roll(self):
        if not self.debts:
            if self.phase == 0:
                self.RNG.roll()
                await self.bot.say("You rolled {} and {}.".format(self.RNG.rolls[0], self.RNG.rolls[1]))
                if not self.current_player.in_jail:
                    jail = await self.move(self.RNG.total())
                    if not jail:
                        if self.RNG.dupe():
                            self.doubles += 1
                            await self.bot.say("You got an additional turn for rolling double.")
                        else:
                            self.doubles = 0
                else:
                    if self.RNG.dupe():
                        self.current_player.in_jail = False
                        self.current_player.jail_time = 0
                        await self.bot.say("You got out of jail.")
                        await self.move(self.RNG.total())
                    elif self.current_player.jail_time >= 2:
                        self.current_player.in_jail = False
                        self.current_player.jail_time = 0
                        self.debts.append(Debt(self.current_player, 50, None))
                        await self.force_pay()
                    else:
                        await self.bot.say("You are still in jail.")
            elif self.phase == 1:
                if self.doubles == 1:
                    self.RNG.roll()
                    await self.bot.say("You rolled {} and {}.".format(self.RNG.rolls[0], self.RNG.rolls[1]))
                    jail = await self.move(self.RNG.total())
                    if not jail:
                        if self.RNG.dupe():
                            self.doubles += 1
                            await self.bot.say("You got yet another additional turn for rolling double.")
                        else:
                            self.doubles = 0
                elif self.doubles == 2:
                    self.RNG.roll()
                    await self.bot.say("You rolled {} and {}.".format(self.RNG.rolls[0], self.RNG.rolls[1]))
                    if self.RNG.dupe():
                        await self.bot.say("You rolled 3 doubles in a row. Suspicious...")
                        await self.go_to_jail()
                    else:
                        await self.move(self.RNG.total())
                    self.doubles = 0
            else:
                await self.force_pay()
        else:
            await self.force_pay()

    async def cmd_buy(self):
        if self.phase == 1:
            land = self.lands[self.current_player.current_position]
            if land.land_type in ('Street', 'Railroad', 'Utility'):
                if land.owner is None:
                    if self.current_player.money >= land.buy_price[0]:
                        land.owner = self.current_player
                        land.level = 0
                        self.current_player.owned_properties.append(land)
                        land.owner.money -= land.buy_price[0]
                        await self.bot.say("You bought {} for ${}.\nYou have ${} left.".format(land.name, land.buy_price[0], land.owner.money))
                        if land.land_type == 'Railroad':
                            other_railroads = [self.lands[5], self.lands[15], self.lands[25], self.lands[35]]
                            other_railroads.remove(land)
                            for other in other_railroads:
                                if other.owner is land.owner:
                                    other.level += 1
                                    land.level = other.level
                        elif land.land_type == 'Utility':
                            if self.lands[12].owner is self.lands[28].owner:
                                self.lands[12].level = 1
                                self.lands[28].level = 1
                    else:
                        await self.bot.say("You don't have enough money.")
                else:
                    await self.bot.say("You can't buy {}.".format(land.name))
            else:
                await self.bot.say("You can't buy {}.".format(land.name))

    async def cmd_buyback(self, player, *args):
        land = self.find_land(*args)
        if player is land.owner:
            if land.level == -1:
                price = land.buy_price[0] * 6 // 10
                if player.money >= price:
                    player.money -= price
                    land.level = 0
                    await self.bot.say("You bought back {} for ${}.".format(land.name, price))
                    if land.land_type == "Railroad":
                        land.level = sum(1 for l in [self.lands[5], self.lands[15], self.lands[25], self.lands[35]] if l.owner is land.owner) - 1
                    elif land.land_type == "Utility":
                        if self.lands[12].owner == self.lands[28].owner:
                            land.level = 1
                else:
                    await self.bot.say("You don't have enough money.")
            else:
                await self.bot.say("There's no reason to buy back.")
        else:
            await self.bot.say("{} is not your.".format(land.name))

    async def cmd_upgrade(self, player, land):
        if land.owner is player:
            if land.land_type == 'Street':
                if 0 <= land.level <= 3:
                    if player.money >= land.buy_price[1]:
                        land.level += 1
                        player.money -= land.buy_price[1]
                        await self.bot.say("You built a house in {} for ${}.".format(land.name, land.buy_price[1]))
                    else:
                        await self.bot.say("You don't have enough money.")
                elif land.level == 4:
                    if player.money >= land.buy_price[1]:
                        land.level += 1
                        player.money -= land.buy_price[1]
                        await self.bot.say("You built a hotel in {} for ${}.".format(land.name, land.buy_price[1]))
                    else:
                        await self.bot.say("You don't have enough money.")
            else:
                await self.bot.say("You can't build house/hotel on {}".format(land.name))
        else:
            await self.bot.say("You don't even own the property ¬_¬")

    async def cmd_info_turn(self):
        await self.bot.say("It's currently {}'s turn.".format(self.current_player.member.mention))

    async def cmd_info_land(self, land):
        if land is not None:
            try:
                owner = land.owner.member.display_name
            except AttributeError:
                owner = None
            if land.land_type == 'Street':
                if land.level == 5:
                    building = "<1 hotel>"
                elif 2 <= land.level <= 4:
                    building = "<" + str(land.level) + " houses>"
                elif land.level == 1:
                    building = "<1 house>"
                elif land.level in (0, -2):
                    building = "[Empty]"
                else:
                    building = "#Mortgaged"
                await self.bot.say("```pf\n#{} - {}\n"
                                   "Owner: {}\n"
                                   "Color: {}\n"
                                   "State: {}\n"
                                   "Buy price: ${}\n"
                                   "House cost: ${}\n"
                                   "Rent price: ${} with no house\n"
                                   " - ${} with 1 house\n"
                                   " - ${} with 2 houses\n"
                                   " - ${} with 3 houses\n"
                                   " - ${} with 4 houses\n"
                                   " - ${} with hotel\n```".format(self.lands.index(land), land.name, owner, land.group, building, land.buy_price[0], land.buy_price[1], land.rent_price[0], land.rent_price[1], land.rent_price[2], land.rent_price[3], land.rent_price[4], land.rent_price[5]))
            elif land.land_type == "Railroad":
                await self.bot.say("```pf\n#{} - {}\n"
                                   "Owner: {}\n"
                                   "State: {}\n"
                                   "Buy price: ${}\n"
                                   "Rent price:\n"
                                   " - ${} if 1 studio is owned\n"
                                   " - ${} if 2 studios are owned\n"
                                   " - ${} if 3 studios are owned\n"
                                   " - ${} if 4 studios are owned\n```".format(self.lands.index(land), land.name, owner, "Mortgaged" if land.level == -1 else "\"Good\"", land.buy_price[0], land.rent_price[0], land.rent_price[1], land.rent_price[2], land.rent_price[3]))
            elif land.land_type == "Utility":
                await self.bot.say("```pf\n#{} - {}\n"
                                   "Owner: {}\n"
                                   "State: {}\n"
                                   "Buy price: ${}\n"
                                   "Rent price:\n"
                                   " - 4 times the rolled amount if 1 zone is owned\n"
                                   " - 10 times the rolled amount if both zone is owned\n```".format(self.lands.index(land), land.name, owner, "Mortgaged" if land.level == -1 else "\"Good\"", land.buy_price[0]))
            elif land.land_type == "Chest":
                await self.bot.say("```pf\n#{} - {}\n"
                                   "If you land on this square, draw a yandere card.\n```".format(self.lands.index(land), land.name))
            elif land.land_type == "Chance":
                await self.bot.say("```pf\n#{} - {}\n"
                                   "If you land on this square, draw a tsundere card.\n```".format(self.lands.index(land), land.name))
            elif land.land_type == "Go":
                await self.bot.say("```pf\n#{} - {}\n"
                                   "The starting point. You gain $200 everytime you pass this.\n```".format(self.lands.index(land), land.name))
            elif land.land_type == "Parking":
                await self.bot.say("```pf\n#{} - {}\n"
                                   "There's nothing to do here.\n"
                                   "Take a break and admire this random illustration.\n```".format(self.lands.index(land), land.name))
            elif land.land_type == "Jail":
                await self.bot.say("```pf\n#{} - {}\n"
                                   "If you land on this square after rolling, it's treat as visiting.\n"
                                   "Otherwise, you will be sent here upon landing on \"Go to jail\" square or drawing \"Go to jail\" card.\n```".format(self.lands.index(land), land.name))
            elif land.land_type == "Go jail":
                await self.bot.say("```pf\n#{} - {}\n"
                                   "You directly go to jail upon landing on this square.\n```".format(self.lands.index(land), land.name))
            elif land.land_type == "Tax":
                await self.bot.say("```pf\n#{} - {}\n"
                                   "You have to pay a certain amount of money when landing on this square.\n```".format(self.lands.index(land), land.name))

    async def cmd_info_player(self, player):
        if player is not None:
            total_debt = 0
            for debt in self.debts:
                if debt.debtor is player:
                    total_debt += debt.amount
            await self.bot.say("```pf\nRound #{} - {}\n"
                               "Current position: #{} - {}\n"
                               "Money: ${}\n"
                               "Owned properties: {}\n"
                               "Total assets: ${}\n"
                               "Total debt: ${}\n```".format(player.game_count, player.member.display_name, player.current_position, self.lands[player.current_position].name, player.money, ', '.join([o.name if o.level==-1 else "\""+o.name+"\"" if o.land_type in ["Railroad", "Utility"] else "<"+o.name+">" for o in player.owned_properties]), player.total_assets(), total_debt))

    async def cmd_jail_card(self, player):
        if player.in_jail:
            if player.number_of_jailcards > 0:
                player.number_of_jailcards -= 1
                player.in_jail = False
                player.jail_time = 0
                if self.chance_jail == 0:
                    self.chance_jail = 1
                else:
                    self.chest_jail = 1
                await self.bot.say("You used a 'Get out of jail' card.")
            else:
                await self.bot.say("You don't have any 'Get out of jail' card.")

    async def cmd_jail_fine(self, player):
        if player.in_jail:
            if player.money >= 50:
                player.money -= 50
                player.in_jail = False
                player.jail_time = 0
                await self.bot.say("You paid $50 to get out of jail.")
            else:
                await self.bot.say("You don't have enough money.")

    async def cmd_skip(self):
        if self.phase >= 0:
            await self.next_turn()

    async def cmd_sabotage(self, player, *args):
        land = self.find_land(*args)
        if player is land.owner:
            if land.land_type == "Street":
                await self.sell_street(land)
            elif land.land_type == "Railroad":
                await self.sell_railroad(land)
            elif land.land_type == "Utility":
                await self.sell_utility(land)

    async def cmd_pay(self, player):
        await self.force_pay()

    async def cmd_sell_land(self, player, amount, target_player, *args):
        land = self.find_land(*args)
        if land.owner is player:
            if target_player.money >= amount:
                if land.level == 0:
                    await self.bot.say("Would {} buy {} for ${}?\nY/N".format(target_player.member.display_name, land.name, amount))
                    while True:
                        msg = await self.bot.wait_for_message(timeout=60, author = target_player.member)
                        if msg.content.strip().lower() == "y":
                            land.owner = target_player
                            player.money += amount
                            target_player.money -= amount
                            await self.bot.say("Trade succeeded.")
                            break
                        elif msg.content.strip().lower() == "n":
                            await self.bot.say("Trade failed.")
                            break
                else:
                    await self.bot.say("You must sell all houses and hotels before trading.")
            else:
                await self.bot.say("{} doesn't have enough money.".format(target_player.member.display_name))
        else:
            await self.bot.say("You don't even own the property ¬_¬")

    async def cmd_sell_card(self, player, amount, target_player):
        if target_player.money >= amount:
            if player.number_of_jailcards > 0:
                await self.bot.say("Would {} buy a 'Get out of jail' card for ${}?\nY/N".format(target_player.member.display_name, amount))
                while True:
                    msg = await self.bot.wait_for_message(timeout=60, author = target_player.member)
                    if msg.content.strip().lower() == "y":
                        player.number_of_jailcards -= 1
                        player.money += amount
                        target_player.number_of_jailcards -= 1
                        target_player.money -= amount
                        await self.bot.say("Trade succeeded.")
                        break
                    elif msg.content.strip().lower() == "n":
                        await self.bot.say("Trade failed.")
                        break
            else:
                await self.bot.say("You don't have any card.")
        else:
            await self.bot.say("{} doesn't have enough money.".format(target_player.member.display_name))
