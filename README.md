# Random Commander

This project uses scryfall to randomly generate a valid commander deck.

> Note: When this tool "randomly" selects a card, it does so by querying
>       scryfall for the top 150 (ish) cards, sorting using EDHREC.
>       It then randomly selects from that list.
>       This way while the deck is random, it should still pick somewhat
>       good cards.

Here's how we build the deck:
1. Randomly select a theme
   There are a number of pre-selected themes to pick from
2. Randomly pick a commander in the theme
3. Pick 62 mainboard cards
   50% of them fit the theme 50% are random top EDHREC cards
   We also pick them to randomly fit a reasonable mana curve, note that it only
   fits that mana curve _on average_.
4. Pick 37 land cards
   We always pick in this order, only randomly where specified:
   - 1 Command Tower
   - 8 Basics, split among the colour identity of the commander
   - As many fetchlands as are available
   - As many shocklands as are available
   - 3 random utility lands (for variety)
   - As many checklands as are available
   - As many painlands as are available
   - As many scrylands as are available
   - Any remaining spaces are filled with basics split amoung the commander's
     colour identity

The output is something that Cockatrice would recognise, with the commander in
the sideboard.

## Running:

```bash
$ poetry run python rand_commander.py
SB: 1 Leinore, Autumn Sovereign
1 Sanctum Prelate
1 Bassara Tower Archer
1 Soul's Majesty
1 Benalish Commander
1 Sword of the Paruns
1 Coat of Arms
1 Hornbash Mentor
1 Sylvan Scrying
1 Eldrazi Displacer
1 Budoka Gardener // Dokai, Weaver of Life
1 Stuffy Doll
1 Eladamri's Call
1 Guan Yu, Sainted Warrior
1 Nissa, Vastwood Seer // Nissa, Sage Animist
1 Venerable Knight
1 Lightning Greaves
1 Scuttling Doom Engine
1 Herald of War
1 Exploration
1 Whisperer of the Wilds
1 Ichor Wellspring
1 Monk Realist
1 Unruly Mob
1 Paladin of Prahv
1 Mind Stone
1 Thundering Spineback
1 Elder of Laurels
1 Icatian Phalanx
1 Lyra Dawnbringer
1 Ghirapur Orrery
1 Silent Arbiter
1 Kessig Cagebreakers
1 Tamiyo's Journal
1 Mesa Enchantress
1 Creeping Renaissance
1 Lotus-Eye Mystics
1 Crusading Knight
1 Abzan Kin-Guard
1 Scalebane's Elite
1 Ornithopter of Paradise
1 Dromoka, the Eternal
1 Emrakul, the Promised End
1 Shieldmage Elder
1 Grim Monolith
1 Martyrs of Korlis
1 Captain of the Watch
1 Sylvan Library
1 Generous Gift
1 Kozilek, the Great Distortion
1 Veteran Armorer
1 Wirewood Channeler
1 Field Marshal
1 Throne Warden
1 Kamahl, Heart of Krosa
1 Priest of the Blessed Graf
1 Icon of Ancestry
1 Mind's Eye
1 Mistcutter Hydra
1 Veteran Adventurer
1 Daunting Defender
1 Selfless Savior
1 Cursed Totem
1 Arid Mesa
1 Brushland
1 Command Tower
1 Flooded Strand
11 Forest
1 Grasping Dunes
1 Marsh Flats
1 Misty Rainforest
11 Plains
1 Spawning Bed
1 Sunpetal Grove
1 Temple Garden
1 Temple of Plenty
1 Urza's Factory
1 Verdant Catacombs
1 Windswept Heath
1 Wooded Foothills
```
