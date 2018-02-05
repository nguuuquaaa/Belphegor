
class BaseObject:
    def __init__(self, data):
        for key, value in data.items():
            if key[0] != "_":
                setattr(self, key, value)

#==================================================================================================================================================

def to_int(any_obj, *, default=None):
    try:
        return int(any_obj)
    except:
        return default

def get_element(container, predicate, *, default=None):
    result = default
    if isinstance(predicate, int):
        try:
            result = container[predicate]
        except IndexError:
            pass
    elif callable(predicate):
        for item in container:
            try:
                if predicate(item):
                    result = item
                    break
            except:
                pass
    else:
        raise TypeError("Predicate is an int or a callable.")
    return result
