from .dices import Dices
from .cangua import CaNgua

#==================================================================================================================================================

def new_game(name, *args, **kwargs):
    if name == "ca_ngua":
        return CaNgua.new_game(*args, **kwargs)
        
def load(name, *args, **kwargs):
    if name == "ca_ngua":
        return CaNgua.load(*args, **kwargs)
        