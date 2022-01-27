
import logging
import sys
import random
import itertools

from core.utils import id_to_colour, take, remove_duplicates
from core.search import search
from core.mainboard import Mainboard

LAND_COUNT = 37

# >> Select theme


class ThemeSelector:
    themes = [
        "(otag:synergy-sorcery or t:sorcery)",
        "(otag:synergy-artifact or t:artifact)",
        "(otag:synergy-attacker or otag:synergy-attack-self or o:attack)",
        "(otag:synergy-enchantment or t:enchantment)",
        "(otag:synergy-equipment or t:equipment)",
        "(otag:synergy-sacrifice or o:dies)",
        "(otag:pp-counters-matter or (o:+1 and o:counter))",
        "(otag:tribal-dragon or t:dragon)",
        "(otag:tribal-zombie or t:zombie)",
        "(otag:tribal-vampire or t:vampire)",
        "(otag:tribal-rogue or t:rogue)",
        "(otag:tribal-human or t:human)",
    ]

    def __init__(self, themes=None):
        if themes:
            self.themes = themes

    def __call__(self):
        return random.choice(self.themes)


get_theme = ThemeSelector()

# >> Select commander


def get_commander(extra_query=""):
    "Get's a random commander in the top 175 commanders"
    commanders = search("is:commander f:edh c>1 " + extra_query)
    return random.choice(commanders)


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
            idx = random.randint(0, len(results))
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
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    # Get cards for deck
    theme_query = get_theme()
    commander = get_commander(theme_query)

    get_mainboard = Mainboard(commander, theme_query=theme_query)
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
