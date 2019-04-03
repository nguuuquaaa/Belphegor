
class GameError(Exception):
    def __init__(self, message):
        self.message = message

    def __format__(self):
        return self.message

    def __repr__(self):
        return f"{self.__class__.__name__}: {self.message}"

class IllegalMove(GameError):
    pass
