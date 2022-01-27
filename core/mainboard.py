import random
import logging

from core.tags import get_tags
from core.search import search

MAINBOARD_COUNT = 62


class CachedCards:
    # Stores cached in this structure:
    # {
    #   True: {
    #     "<=1": [],
    #     "=2": [],
    #     ...
    #   },
    #   False: ...
    # }
    # So cards can be retrieved like so:
    # ```
    # themed = True
    # cmc = "<=1"
    # self.cache[themed][cmc]
    # ```
    cache = {}

    # CMCs here are in the shape that they will appear in the final query
    allowed_cmcs = {'<=1', '=2', '=3', '=4', '=5', '=6', '>=7'}

    # The list of cards that have been picked already
    # Used to ensure we don't pick the same card twice
    seen_cards = set()

    keyword_amount = 1
    otag_amount = 1
    atag_amount = 1
    type_amount = 1

    def __calculate_theme(self, commander):
        # >> Keywords
        keywords = []
        if commander["keywords"]:
            keywords = random.sample(commander["keywords"],
                                     min(len(commander["keywords"]),
                                         self.keyword_amount))
        keywords = ["o:" + k for k in keywords]

        # >> Oracle text tags
        otags = random.sample(self.commander_tags["oracleText"],
                              min(len(self.commander_tags["oracleText"]),
                                  self.otag_amount))
        otags = ["otag:" + t for t in otags]

        # >> Art tags
        atags = random.sample(self.commander_tags["illustration"],
                              min(len(self.commander_tags["illustration"]),
                                  self.atag_amount))
        atags = ["atag:" + t for t in atags]

        # >> Types
        types = commander["type_line"].split(" — ")[-1]
        types = types.split()
        types = random.sample(types, min(len(types), self.type_amount))
        types = ["t:" + t for t in types]

        theme = keywords + otags + atags + types
        theme = "(" + " or ".join(theme) + ")"

        logging.info(theme)
        return theme

    def __init__(self, commander, theme_query):
        self.commander = commander
        self.query_identity = "".join(commander["color_identity"])
        self.commander_tags = get_tags(commander["set"],
                                       commander["collector_number"])
        if theme_query is not None:
            self.theme = theme_query
        else:
            self.theme = self.__calculate_theme(commander)

    def __build_themed_query(self, cmc):
        return ("f:edh sort:edhrec {theme_query}"
                + " -t:land -medallion id:{id} cmc{cmc}") \
            .format(id=self.query_identity, cmc=cmc, theme_query=self.theme)

    def __build_unthemed_query(self, cmc):
        return "f:edh sort:edhrec -t:land -medallion id:{id} cmc{cmc}" \
            .format(id=self.query_identity, cmc=cmc)

    def __build_query(self, cmc, themed):
        if themed:
            return self.__build_themed_query(cmc)
        else:
            return self.__build_unthemed_query(cmc)

    def __fill_cache(self, cmc, themed):
        query = self.__build_query(cmc, themed)

        try:
            cards = search(query)
            if logging.root.isEnabledFor(logging.DEBUG):
                filtered_cards = [c["name"] for c in cards
                                  if c["name"] in self.seen_cards]
                logging.debug("filtered cards: " + ", ".join(filtered_cards))
            # Filter out cards we've seen already
            cards = [c for c in cards if c["name"] not in self.seen_cards]
        except Exception:
            # TODO: Be less generic about error handling?
            cards = []

        # Add a dict here if nessacary
        if self.cache.get(themed) is None:
            self.cache[themed] = {}

        self.cache[themed][cmc] = cards

    def __should_cleanup_cache(self, cmc, themed):
        return self.cache.get(not themed) is not None \
            and self.cache[not themed].get(cmc) is not None

    def __cleanup_cache(self, cmc, themed, picked_card):
        "Removes the card from all loaded caches"

        # We know that the card was removed from self.cache[themed][cmc]
        # Because the CMC is bound, we know the only other cache it will appear
        # in is self.cache[not themed][cmc]
        if self.__should_cleanup_cache(cmc, themed):
            if logging.root.isEnabledFor(logging.DEBUG):
                card_names = [c["name"] for c in self.cache[not themed][cmc]]
                if picked_card["name"] in card_names:
                    logging.debug("cleaned up: " + picked_card["name"])
            cards = self.cache[not themed][cmc]
            cards = [c for c in cards
                     if c["name"] != picked_card["name"]]

            self.cache[not themed][cmc] = cards

    def __should_fill_cache(self, cmc, themed):
        return self.cache.get(themed) is None \
            or self.cache[themed].get(cmc) is None

    def get(self, cmc, themed=False):
        if cmc not in self.allowed_cmcs:
            raise Exception("Not a valid CMC value")

        if self.__should_fill_cache(cmc, themed):
            self.__fill_cache(cmc, themed)

        cards = self.cache[themed][cmc]

        if len(cards) == 0:
            raise Exception("Cache empty")

        idx = random.randint(0, len(cards)-1)
        card = cards[idx]
        cards.pop(idx)

        self.__cleanup_cache(cmc, themed, card)
        self.seen_cards.add(card["name"])

        return card


class Mainboard:
    """
    Used to get a random deck of 62 mainboard cards.
    The cards are selected to:
    - fit a decent, but random, mana curve
    - match the colour identity of the commander
    - not be medallions :P
    """

    def __init__(self, commander, theme_query=None):
        self.themed = theme_query is not None

        self.card_cache = CachedCards(commander, theme_query)

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
            picked = False
            while not picked:
                cmc = self.__random_cmc()
                # 50/50 chance for themed cards, False if disabled
                themed = self.themed and random.choice([True, False])

                try:
                    card = self.card_cache.get(cmc, themed)
                    picked = True
                except Exception:
                    # If we get an exception, try again
                    # TODO: Maybe blacklist cmc & themed combos once we get an
                    #       Exception?
                    continue

            deck.append(card)

        return deck
