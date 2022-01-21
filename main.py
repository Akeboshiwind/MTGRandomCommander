import json
import requests
import re

import logging
import sys
import random
import scrython
import itertools
import time

from scrython.foundation import ScryfallError

MAINBOARD_COUNT = 62
LAND_COUNT = 37

# >> Utils


class GetTags:
    endpoint = "https://tagger.scryfall.com/graphql"

    query = """
query FetchCard($set: String!, $number: String!, $back: Boolean = false) {
  card: cardBySet(set: $set, number: $number, back: $back) {
    ...CardAttrs
    backside
    layout
    scryfallUrl
    sideNames
    twoSided
    rotatedLayout
    taggings {
      ...TaggingAttrs
      tag {
        ...TagAttrs
        ancestorTags {
          ...TagAttrs
          __typename
        }
        __typename
      }
      __typename
    }
    relationships {
      ...RelationshipAttrs
      __typename
    }
    __typename
  }
}

fragment CardAttrs on Card {
  artImageUrl
  backside
  cardImageUrl
  collectorNumber
  id
  illustrationId
  name
  oracleId
  printingId
  set
  __typename
}

fragment RelationshipAttrs on Relationship {
  classifier
  classifierInverse
  annotation
  contentId
  contentName
  createdAt
  creatorId
  foreignKey
  id
  name
  relatedId
  relatedName
  status
  type
  __typename
}

fragment TagAttrs on Tag {
  category
  createdAt
  creatorId
  id
  name
  slug
  status
  type
  typeSlug
  __typename
}

fragment TaggingAttrs on Tagging {
  annotation
  contentId
  createdAt
  creatorId
  foreignKey
  id
  type
  status
  weight
  __typename
}
"""

    def __init__(self):

        # TODO: Does the page matter?
        r = requests.get("https://tagger.scryfall.com/card/mma/33")

        cookie = r.headers["Set-Cookie"]

        # TODO: Regex is brittle. Use beautifulsoup?
        match = re.search(
            r'<meta name="csrf-token" content="([^"]*)"', str(r.content))
        csrf_token = match.group(1)

        self.headers = {
            "Cookie": cookie,
            "X-CSRF-Token": csrf_token
        }

    def __call__(self, set, number):
        payload = {
            "operationName": "FetchCard",
            "variables": {
                "back": False,
                "set": set,
                "number": number
            },
            "query": self.query
        }

        r = requests.post(self.endpoint, json=payload, headers=self.headers)
        if r.status_code == 200:
            data = r.json()

            taggings = data["data"]["card"]["taggings"]

            tags = []
            for tagging in taggings:
                tags.append(tagging["tag"])
                for ancestorTag in tagging["tag"]["ancestorTags"]:
                    tags.append(ancestorTag)
            tags = sorted(tags, key=lambda t: t["type"])

            ret = {
                "illustration": [],
                "oracleText": [],
            }

            for type, tags in itertools.groupby(tags, key=lambda t: t["type"]):
                slugs = [t["slug"] for t in tags]
                if type == "ILLUSTRATION_TAG":
                    ret["illustration"] = slugs
                elif type == "ORACLE_CARD_TAG":
                    ret["oracleText"] = slugs

            return ret
        else:
            print(json.dumps(r.json(), indent=2))
            raise Exception(f"Query failed to run with a {r.status_code}.")


get_tags = GetTags()


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


def raw_search(query):
    time.sleep(0.1)
    logging.debug("Searching for: `" + query + "`")
    try:
        return scrython.cards.Search(q=query, unique="cards", dir="asc")
    except ScryfallError:
        return None


def search(query):
    "Performs a search to scryfall with some basic ratelimiting"
    resp = raw_search(query)

    if resp:
        return resp.data()
    else:
        return []


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
    commanders = search("is:commander f:edh c>1")
    return random.choice(commanders)


# >> Mainboard


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

    def __init__(self, commander):
        self.commander = commander
        self.query_identity = "".join(commander["color_identity"])

    def __build_themed_query(self, cmc):
        # >> Keywords
        keyword_query = ""
        if commander["keywords"]:
            logging.info("Detected keywords: " +
                         ", ".join(commander["keywords"]))
            keyword_query += "("
            keyword_query += " or ".join(
                ["o:" + keyword for keyword in commander["keywords"]])
            keyword_query += ")"

        # >> Type string
        # Split by any '—' that might be in the type line and get the last
        # thing
        types = commander["type_line"].split(" — ")[-1]
        types = types.split()

        type_query = "("
        type_query += " or ".join(["t:" + type for type in types])
        type_query += ")"

        theme_query = type_query
        if keyword_query != "":
            theme_query = "(" \
                + keyword_query \
                + " or " \
                + type_query \
                + ")"

        return ("f:edh sort:edhrec {theme_query}"
                + " -t:land -medallion id:{id} cmc{cmc}") \
            .format(id=self.query_identity, cmc=cmc, theme_query=theme_query)

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

        idx = random.randint(0, len(cards) - 1)
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

    def __init__(self, commander, themed=False):
        self.themed = themed

        self.card_cache = CachedCards(commander)

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
    results = search(fetchland_query)

    good = good + results

    # Shocklands
    results = search("is:Shockland id:" + query_identity)

    good = good + results

    # Random lands
    results = search(
        "f:edh sort:edhrec oracletag:utility-land id:" + query_identity,)

    for _ in range(0, 3):
        if len(results) != 0:
            idx = random.randint(0, len(results) - 1)
            card = results.pop(idx)
            good.append(card)

    # Checkland
    results = search("is:Checkland id:" + query_identity)

    good = good + results

    # Painland
    results = search("is:Painland id:" + query_identity)

    good = good + results

    # Scryland
    results = search("is:Scryland id:" + query_identity)

    good = good + results

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
