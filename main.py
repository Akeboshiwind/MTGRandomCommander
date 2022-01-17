import logging
import sys
import random
import scrython
import itertools
import time

MAINBOARD_COUNT = 62
LAND_COUNT = 37

# >> Utils


colours = {
    'w': "Plains",
    'b': "Swamp",
    'u': "Island",
    'r': "Mountain",
    'g': "Forest"
}


def id_to_colour(id):
    "Convert a colour identity to a mana colour"
    return colours[id.lower()]


def search(query):
    "Performs a search to scryfall with some basic ratelimiting"
    time.sleep(0.1)
    logging.debug("Searching for: `" + query + "`")
    return scrython.cards.Search(q=query, unique="cards", dir="asc")


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

# >> Select commander


def get_commander():
    "Get's a random commander in the top 175 commanders"
    commanders = search("is:commander f:edh c>1").data()
    return random.choice(commanders)


# >> Mainboard


class Mainboard:
    """
    Used to get a random deck of 62 mainboard cards.
    The cards are selected to:
    - fit a decent, but random, mana curve
    - match the colour identity of the commander
    - not be medallions :P
    """

    def __init__(self, commander, themed=False):
        self._query_identity = "".join(commander["color_identity"])

        self.cmc_cache = {
            '<=1': [],
            '=2': [],
            '=3': [],
            '=4': [],
            '=5': [],
            '=6': [],
            '>=7': [],
        }
        self.__fill_cmc_cache()

        self.themed = themed

        if self.themed:
            self.themed_cmc_cache = {
                '<=1': [],
                '=2': [],
                '=3': [],
                '=4': [],
                '=5': [],
                '=6': [],
                '>=7': [],
            }
            self.__fill_themed_cmc_cache(commander)

    def __fill_cmc_cache(self):
        for cmc in self.cmc_cache.keys():
            # The cmc here is a little weird
            # What I'm doing is using the key from the cmc_cache which includes
            # both the value and the comparitor. This makes the cmc_cache a bit
            # easier to read but makes this query a little strange.
            query = "f:edh sort:edhrec -t:land -medallion id:{id} cmc{cmc}" \
                .format(id=self._query_identity, cmc=cmc)

            result = search(query)
            self.cmc_cache[cmc] = result.data()

    def __build_themed_query(self, commander):
        """
        Build the query to add to the cmc query.
        Looks at the keywords and types on the card to try and find card that
        synergise with your commander.
        """
        extra_query = ""

        keyword_query = ""
        if commander["keywords"]:
            keyword_query += "("
            keyword_query += " or ".join(
                ["o:" + keyword for keyword in commander["keywords"]])
            keyword_query += ")"

        # Split by any '—' that might be in the type line and get the last
        # thing
        types = commander["type_line"].split(" — ")[-1]
        types = types.split()

        type_query = "("
        type_query += " or ".join(["t:" + type for type in types])
        type_query += ")"

        if keyword_query != "":
            extra_query = "({keyword_query} or {type_query})" \
                .format(keyword_query=keyword_query,
                        type_query=type_query)
        else:
            extra_query = type_query

        logging.debug("extra_query: " + extra_query)

        return extra_query

    def __fill_themed_cmc_cache(self, commander):
        extra_query = self.__build_themed_query(commander)

        for cmc in self.themed_cmc_cache.keys():
            query = "f:edh sort:edhrec {extra_query} -t:land -medallion id:{id} cmc{cmc}" \
                .format(id=self._query_identity, cmc=cmc,
                        extra_query=extra_query)

            result = search(query)
            self.themed_cmc_cache[cmc] = result.data()

            themed_cards = \
                set([card["name"] for card in self.themed_cmc_cache[cmc]])

            # Remove any duplicates
            logging.debug(len(self.cmc_cache[cmc]))
            self.cmc_cache[cmc] = \
                [card for card in self.cmc_cache[cmc]
                 if not card["name"] in themed_cards]
            logging.debug(len(self.cmc_cache[cmc]))
            assert(len(self.cmc_cache[cmc]) != 0)
        self.cmc_cache[cmc] = result.data()

    """
    Based off of a graph James gave me
    It's a little weighted towards the 2s, but that's alright
    """
    mana_curve = ['<=1'] * 8 \
        + ['=2'] * 14 \
        + ['=3'] * 12 \
        + ['=4'] * 10 \
        + ['=5'] * 8 \
        + ['=6'] * 6 \
        + ['>=7'] * 4

    def __random_cmc(self):
        "Returns a random cmc weighted by a mana curve"
        return random.choice(self.mana_curve)

    def __call__(self):
        """
        Returns a deck of 62 non-land cards in the colours of the commander
        used to construct this class
        """
        deck = []

        # Grab 62 cards for the deck
        for _ in range(0, MAINBOARD_COUNT):
            cmc = self.__random_cmc()
            # 50/50 chance for themed cards, if enabled
            if self.themed and random.choice([True, False]):
                card_list = self.themed_cmc_cache[cmc]
            else:
                card_list = self.cmc_cache[cmc]

            idx = random.randint(0, len(card_list)-1)
            card = card_list[idx]
            card_list.pop(idx)

            deck.append(card)

        return deck

# >> Add lands


def get_lands(commander):
    # >> Setup

    query_identity = "".join(commander["color_identity"])
    colours = [id_to_colour(id) for id in commander["color_identity"]]

    # >> Essential basic lands

    essentials = []
    essentials.append({
        "name": "Command Tower"
    })

    for colour in take(8, itertools.cycle(colours)):
        # Get from scryfall?
        essentials.append({
            'name': colour
        })

    # >> Good lands

    good = []

    # Fetchlands
    fetchland_query = "is:Fetchland (" \
        + " or ".join(["o:" + colour for colour in colours]) \
        + ")"
    result = search(fetchland_query)

    good = good + result.data()

    # Shocklands
    result = search("is:Shockland id:" + query_identity)

    good = good + result.data()

    # Random lands
    result = search(
        "f:edh sort:edhrec oracletag:utility-land id:" + query_identity,)

    for _ in range(0, 3):
        card = random.choice(result.data())
        good.append(card)

    # Checkland
    result = search("is:Checkland id:" + query_identity)

    good = good + result.data()

    # Painland
    result = search("is:Painland id:" + query_identity)

    good = good + result.data()

    # Scryland
    result = search("is:Scryland id:" + query_identity)

    good = good + result.data()

    # >> Cull extra lands

    # First remove duplicates from the essentials
    good = remove_duplicates(lambda c: c["name"], good)

    # Then remove any excess lands we may have
    lands = essentials + good
    lands = lands[:LAND_COUNT]

    # >> Fill out rest with basics
    fill_amount = max(0, LAND_COUNT - len(lands))
    for colour in take(fill_amount, itertools.cycle(colours)):
        # Get from scryfall?
        lands.append({
            'name': colour
        })

    return lands


# >> Build deck

if __name__ == "__main__":
    # Setup
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    # Get cards for deck
    commander = get_commander()

    get_mainboard = Mainboard(commander, themed=True)
    mainboard = get_mainboard()

    lands = get_lands(commander)

    # Print deck

    print("SB: 1 " + commander["name"])

    for card in mainboard:
        print("1 " + card["name"])

    land_names = [land["name"] for land in lands]
    land_names = sorted(land_names)
    for land_name, group in itertools.groupby(land_names):
        print(str(len(list(group))) + " " + land_name)
