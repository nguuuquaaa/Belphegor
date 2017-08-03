import random


class Dices:
    def __init__(self, max_side, number_of_dices):
        self.max_side = max_side
        self.number_of_dices = number_of_dices
        self.rolls=[]
        self.roll()

    def roll(self):
        self.rolls.clear()
        for i in range(self.number_of_dices):
            self.rolls.append(random.randint(1, self.max_side))
        return self.rolls

    def total(self):
        number = 0
        for i in self.rolls:
            number += i
        return number

    def dupe(self):
        number = self.rolls[0]
        for i in self.rolls:
            if i != number:
                return False
        return True

    def __call__(self):
        return self.total()
