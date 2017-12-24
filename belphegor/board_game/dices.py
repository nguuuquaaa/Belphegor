import random

#==================================================================================================================================================

class Dices:
    def __init__(self, max_side, number_of_dices):
        self.max_side = max_side
        self.number_of_dices = number_of_dices

    def roll(self):
        self._rolls = tuple(random.randrange(1, self.max_side+1) for i in range(self.number_of_dices))
        return list(self._rolls)

    @property
    def result(self):
        return list(self._rolls)

    @property
    def total(self):
        return sum(self._rolls)

    def is_dupe(self):
        number = self._rolls[0]
        for i in self._rolls:
            if i != number:
                return False
        return True
