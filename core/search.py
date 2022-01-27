import scrython
import time
import logging

from scrython.foundation import ScryfallError


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
