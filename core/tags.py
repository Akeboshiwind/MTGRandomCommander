import json
import requests
import re
import itertools


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
