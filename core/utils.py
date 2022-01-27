import itertools


class ColourConverter:
    colours = {
        'w': "Plains",
        'b': "Swamp",
        'u': "Island",
        'r': "Mountain",
        'g': "Forest"
    }

    def __init__(self, colours=None):
        if colours:
            self.colours = colours

    def __call__(self, id):
        "Convert a colour identity to a mana colour"
        return self.colours[id.lower()]


id_to_colour = ColourConverter()


def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(itertools.islice(iterable, n))


def remove_duplicates(f, lst):
    "Remove duplicates from an iterable using f to get the key"
    seen = set()
    ret = []

    for item in lst:
        key = f(item)
        if key not in seen:
            ret.append(item)
            seen.add(key)

    return ret
