"""Static game data for A Koopa's Revenge 2 (SWF: Flash 8 / ActionScript 2).

Everything here was derived from the decompiled scripts. Items marked ASSUMED
or TODO are guesses that should be confirmed against the game.
"""

GAME_NAME = "A Koopa's Revenge 2"
BASE_ID = 8_200_000

# --------------------------------------------------------------------------
# Levels: (variable, display name, world, has_secret_exit, has_silver_coins)
# Level state is a 7 digit number stored in _root.<variable>:
#   ones digit    = main exit cleared
#   tens digit    = secret exit cleared
#   1000 / 10000 / 100000 digits = silver coin 3 / 2 / 1
# "Has secret exit" comes from the all-complete save (1111011 vs 1111001).
# w0l1 has no silver coins (1000011) but does have a secret exit (confirmed).
# --------------------------------------------------------------------------
LEVELS = [
    ("w0l1", "World 0-1", 0, True, False),
    ("w1l1", "World 1-1", 1, True, True),
    ("w1l2", "World 1-2", 1, True, True),
    ("w1l3", "World 1-3", 1, False, True),
    ("w1l4", "World 1-4", 1, True, True),
    ("w1l5", "World 1-5", 1, True, True),
    ("w1l6", "World 1-6", 1, False, True),
    ("w1l7", "World 1-7", 1, True, True),
    ("w2l1", "World 2-1", 2, True, True),
    ("w2la", "World 2-A", 2, True, True),
    ("w2l2", "World 2-2", 2, True, True),
    ("w2l3", "World 2-3", 2, True, True),
    ("w2l4", "World 2-4", 2, True, True),
    ("w2l5", "World 2-5", 2, False, True),
    ("w3l1", "World 3-1", 3, True, True),
    ("w3l2", "World 3-2", 3, True, True),
    ("w3l3", "World 3-3", 3, False, True),
    ("w3l4", "World 3-4", 3, False, True),
    ("w4l1", "World 4-1", 4, True, True),
    ("w4l2", "World 4-2", 4, True, True),
    ("w4l3", "World 4-3", 4, True, True),
    ("w4l4", "World 4-4", 4, False, True),
    ("w4l5", "World 4-5", 4, False, True),
    ("w5l1", "World 5-1", 5, False, True),
    ("w5l2", "World 5-2", 5, False, True),
    ("w5l3", "World 5-3 (Castle Mario)", 5, True, True),
]
LEVEL_BY_VAR = {l[0]: l for l in LEVELS}

# Silver coin digit weights inside the level number.
COIN_PLACES = {1: 100000, 2: 10000, 3: 1000}

# Special requirement token: "Flight" = Flight Petal, or Dragon Scale once the
# pink blocks are active (the Pink Switch has been hit).
FLIGHT = "Flight"

# Koopaling stars: _root.<name> booleans, set by the star pickup (kid == name).
# name -> (variable, world, level label, required items)   (all from the user)
KOOPALINGS = {
    "Larry": ("larry", 1, "1-0 (Airship)", []),
    # Requirement syntax: a tuple is "any of these", a list is "all of these".
    # Morton (1-7): either cheat is enough on its own, otherwise the Flight Petal or Dragon Scale
    # plus the Yellow Blocks. The Green Blocks are not needed at all.
    "Morton": ("morton", 1, "1-7", [("Space Jump",
                                     [("Flight Petal", "Dragon Scale"), "Yellow Blocks"])]),
    "Wendy": ("wendy", 2, "2-4", ["Spiny Flower"]),
    "Iggy": ("iggy", 3, "3-2", ["Water Flower"]),
    "Roy": ("roy", 4, "4-1", ["Thunder Flower"]),
    "Lemmy": ("lemmy", 4, "4-4", ["Dragon Scale"]),
    "Ludwig": ("ludwig", 5, "5-1", []),
}

# Secret exits that need an item (complete list, confirmed by the user).
# Silver coins that need an item: (level var, coin number as in "Silver Coin N") -> items.
COIN_REQUIREMENTS = {
    ("w4l1", 1): ["Thunder Flower"],
    ("w2l1", 1): ["Spiny Flower"],
    ("w2l1", 2): ["Spiny Flower"],
    ("w3l2", 2): ["Green Blocks"],     # any of these
}

SECRET_REQUIREMENTS = {
    "w1l7": [FLIGHT],
    "w2l3": [FLIGHT],
    "w2l2": ["Spiny Flower"],
}

# Switch palaces, one per world 1-4 (Yellow, Green, Red, Blue in that order).
# In the unmodified game completing a palace sets _root.<colour>block, which is
# also what makes the blocks appear in levels. The patch must split these:
# palace -> _root.ap_palace_<colour> (the check), item -> _root.<colour>block.
# name -> (colour, world)
PALACES = {
    "Yellow Switch Palace": ("yellow", 1),
    "Green Switch Palace": ("green", 2),
    "Red Switch Palace": ("red", 3),
    "Blue Switch Palace": ("blue", 4),
}

# Cheat checks: name -> (detect kind, variable).
# They fire on the game's own unlock flags, so no SWF patch is needed. The flag
# is set by the in-game unlock, the options-menu code, OR by the bridge when the
# matching item is received, and in every case the check is sent too (see
# ITEM_AUTO_CHECKS), so receiving a cheat item never "locks" its check.
CHEAT_CHECKS = {
    "Cheat: Space Jump": ("flag", "cheatpwing"),
    "Cheat: Screw Jump": ("flag", "cheatscrew"),
    "Cheat: Rush Coil": ("flag", "cheatrush"),     # TODO: the game may use `rush` instead; both are watched
    "Cheat: Bloodshed": ("flag", "cheatblood"),
    "Cheat: Infinity Pretzel": ("lives_ge", 10000),   # lives >= 10000 = infinite
    "Cheat: 100 Lives (X+Y)": ("lives_ge", 100),     # same idea as the Infinity Pretzel, lower threshold
    "Cheat: Pink Switch": ("flag", "pinkblock"),
}

# Where each cheat check lives: name -> (worlds, required items).
# worlds = [] means no world gate; several worlds means ANY of them works.
CHEAT_RULES = {
    "Cheat: Space Jump": ([1, 3], []),               # 1-6, or 3-4
    "Cheat: Screw Jump": ([2], ["Space Jump"]),      # 2-A
    "Cheat: Rush Coil": ([2], []),                   # 2-3
    "Cheat: Bloodshed": ([], []),                    # instant, any time
    "Cheat: Infinity Pretzel": ([5], ["Bone/Boo Flower"]),   # 5-3, secret path
    "Cheat: 100 Lives (X+Y)": ([], []),
    "Cheat: Pink Switch": ([1, 2, 3, 4], []),        # found at any switch palace
}

# 5-4 is unlocked after 5-3 and needs all 7 koopaling stars and all 75 silver coins.
def star_event(name):
    return (f"Star Obtained: {name}", f"Koopaling Star: {name}")


def coin_event(world):
    return (f"Silver Coins Collected: World {world}", f"Silver Coins: World {world}")


# Extra game flag that also counts as "done" for a check (set by the game itself or
# by the bridge when the matching item arrives).
CHEAT_ALT_FLAGS = {
    "Cheat: Rush Coil": "rush",
    "Yellow Switch Palace": "yellowblock",
    "Green Switch Palace": "greenblock",
    "Red Switch Palace": "redblock",
    "Blue Switch Palace": "blueblock",
}

# Receiving one of these items also sends the matching check, so getting the item
# never locks the check. (cheat items -> cheat checks, block items -> switch palaces)
ITEM_AUTO_CHECKS = {
    "Space Jump": "Cheat: Space Jump",
    "Screw Jump": "Cheat: Screw Jump",
    "Rush Coil": "Cheat: Rush Coil",
    "Bloodshed": "Cheat: Bloodshed",
    "Yellow Blocks": "Yellow Switch Palace",
    "Green Blocks": "Green Switch Palace",
    "Red Blocks": "Red Switch Palace",
    "Blue Blocks": "Blue Switch Palace",
}

PINK_EVENT_LOCATION = "Pink Blocks Active"
PINK_EVENT_ITEM = "Pink Blocks"

# Boss levels that have a second checkpoint ("<var>b", the boss room).
BOSS_CHECKPOINT_LEVELS = ["w1l6", "w2l5", "w3l4", "w4l5", "w5l2", "w5l3"]
BABIES_PER_LEVEL = 4          # baby1..baby4 in each of the 25 main levels (the tutorial has none)

FLOWER_FACE_MAX = 41          # face N unlocks at coinscollected >= 500 * N

# Goal events (locked event items, no address). All three are always created;
# the Goal option picks which one completes the game.
EVENT_GIGA_MARIO = ("Defeat Mario and Giga Mario", "Giga Mario Defeated")   # World 5-3 boss
EVENT_5_3 = ("World 5-3 Cleared", "5-3 Cleared")                               # unlocks 5-4
EVENT_5_4 = ("Beat 5-4", "5-4 Cleared")                                       # final boss
EVENT_BOSS_RUSH = ("Beat the Boss Rush", "Boss Rush Cleared")                 # 1-0, unlocked after 5-4

def checkpoint_locations():
    """Every level has one checkpoint (_root.cancelhalf = level id); boss levels also have a
    boss room checkpoint (_root.cancelend = level id + "b"). 25 + 6 = 31. The tutorial has none."""
    for var, name, world, secret, coins in LEVELS:
        if var == "w0l1":
            continue
        yield f"{name} - Checkpoint", world, ("checkpoint", var)
        if var in BOSS_CHECKPOINT_LEVELS:
            yield f"{name} - Boss Room Checkpoint", world, ("checkpoint", var + "b")


def baby_locations():
    """4 baby kills in each of the 25 main levels = 100. id is "<level id>:<baby number>"."""
    for var, name, world, secret, coins in LEVELS:
        if var == "w0l1":
            continue
        for n in range(1, BABIES_PER_LEVEL + 1):
            yield f"{name} - Baby {n}", world, ("baby", f"{var}:{n}")


# --------------------------------------------------------------------------
# Items
# --------------------------------------------------------------------------
WORLD_ITEMS = {f"World {n} Unlock": n for n in range(1, 6)}
BLOCK_ITEMS = ["Yellow Blocks", "Green Blocks", "Red Blocks", "Blue Blocks"]
# Not randomized: Mushroom (stacks twice) and Power Star (optional filler).
POWERUP_ITEMS = [
    "Fire Flower", "Flight Petal", "Spiny Flower", "Water Flower",
    "Thunder Flower", "Hammer Flower", "Bone/Boo Flower", "Dragon Scale",
]
CHEAT_ITEMS = ["Space Jump", "Screw Jump", "Rush Coil", "Bloodshed"]

# Goal gating items: they have no effect in the game. Both must be collected (in full) before
# the goal counts as complete, which stops a player from "winning" their game automatically.
SILVER_COIN_ITEM = "Silver Coin"       # up to 75, one per silver coin
STAR_ITEM = "Koopaling Star"           # up to 7, one per koopaling
SILVER_COIN_ITEM_MAX = 75
STAR_ITEM_MAX = 7

PROGRESSION_ITEMS = set(WORLD_ITEMS) | {STAR_ITEM,
    "Yellow Blocks", "Green Blocks", "Flight Petal", "Spiny Flower",
    "Water Flower", "Thunder Flower", "Bone/Boo Flower", "Dragon Scale",
    "Space Jump", "Screw Jump",
}

FILLER_ITEMS = {"Extra Life": 5}
OPTIONAL_FILLER = {"Power Star": 2}     # only when the Power Star Filler option is on


def level_locations():
    """Yield (location name, world, detect dict) for all level based checks."""
    for var, name, world, secret, coins in LEVELS:
        yield f"{name} - Clear", world, ("level_digit", var, 1)
        if secret:
            yield f"{name} - Secret Exit", world, ("level_digit", var, 10)
        if coins:
            for n, place in COIN_PLACES.items():
                yield f"{name} - Silver Coin {n}", world, ("level_digit", var, place)


# --------------------------------------------------------------------------
# Bridge support (single source of truth for the client)
# --------------------------------------------------------------------------
# Items that simply set a game flag (idempotent, re-sent on every connect).
FLAG_ITEMS = {
    "Yellow Blocks": "yellowblock",
    "Green Blocks": "greenblock",
    "Red Blocks": "redblock",
    "Blue Blocks": "blueblock",
    "Space Jump": "cheatpwing",
    "Screw Jump": "cheatscrew",
    "Rush Coil": "rush",           # TODO: verify (the game also has cheatrush)
    "Bloodshed": "cheatblood",
}

# Items that are applied once each (deltas), never re-applied on reconnect.
# item name -> (message kind, key, amount)
DELTA_ITEMS = {
    "Extra Life": ("G", "coins", 100),      # +100 coins = one 1-Up; NOT coinscollected (flower faces)
    "Power Star": ("G", "powerstar", 1),
}


def detection_table():
    """location name -> detection dict, consumed by the bridge client."""
    t = {}
    for n, w, d in level_locations():
        t[n] = {"kind": "level_digit", "var": d[1], "weight": d[2]}
    for n, w, d in checkpoint_locations():
        t[n] = {"kind": "checkpoint", "id": d[1]}
    for n, w, d in baby_locations():
        t[n] = {"kind": "baby", "id": d[1]}
    for k, (v, w, lvl, req) in KOOPALINGS.items():
        t[f"Koopaling Star: {k}"] = {"kind": "flag", "var": v}
    for n, (c, w) in PALACES.items():
        t[n] = {"kind": "flag", "var": f"ap_palace_{c}"}
    for n, (k, v) in CHEAT_CHECKS.items():
        t[n] = {"kind": "flag", "var": v} if k == "flag" else {"kind": "lives_ge", "value": v}
    for n, var in CHEAT_ALT_FLAGS.items():
        t[n].update(alt_var=var)
    for i in range(1, FLOWER_FACE_MAX + 1):
        t[f"Flower Face {i}"] = {"kind": "coinscollected_ge", "value": 500 * i}
    return t


# goal option value -> detection dict
GOAL_DETECTION = {
    0: {"kind": "level_digit", "var": "w5l3", "weight": 1},   # ASSUMED: 5-3 clear = Mario/Giga Mario
    1: {"kind": "flag", "var": "ap_final_boss"},
    2: {"kind": "flag", "var": "ap_boss_rush"},
}


# --------------------------------------------------------------------------
# /warp targets: main timeline frame labels (same ids the map uses) -> (display name, world)
# --------------------------------------------------------------------------
WARP_EXTRA = {
    "w1l0": ("1-0 (Airship)", 1),
    "w5l4": ("5-4 (Final Level)", 5),
    "w1sp": ("Yellow Switch Palace", 1),
    "w2sp": ("Green Switch Palace", 2),
    "w3sp": ("Red Switch Palace", 3),
    "w4sp": ("Blue Switch Palace", 4),
}
WARP_ALIASES = {"airship": "w1l0", "yellow": "w1sp", "green": "w2sp", "red": "w3sp", "blue": "w4sp"}


def warp_targets():
    t = {var: (name, world) for var, name, world, _, _ in LEVELS}
    t.update(WARP_EXTRA)
    return t


# --------------------------------------------------------------------------
# /powerup: item name -> the game's _root.colour value (see PATCHING.md)
# --------------------------------------------------------------------------
POWERUP_COLOURS = {
    "Fire Flower": 2, "Flight Petal": 3, "Dragon Scale": 4, "Spiny Flower": 5,
    "Thunder Flower": 6, "Bone/Boo Flower": 7, "Water Flower": 8, "Hammer Flower": 10,
}
POWERUP_ALIASES = {
    "fire": "Fire Flower", "flight": "Flight Petal", "petal": "Flight Petal", "dragon": "Dragon Scale",
    "scale": "Dragon Scale", "spiny": "Spiny Flower", "thunder": "Thunder Flower", "bone": "Bone/Boo Flower",
    "boo": "Bone/Boo Flower", "water": "Water Flower", "hammer": "Hammer Flower",
}

# Short names shown by /powerup (in the order they are listed to the player).
POWERUP_SHORT = {
    "Fire Flower": "fire", "Flight Petal": "flight", "Dragon Scale": "dragon", "Spiny Flower": "spiny",
    "Thunder Flower": "thunder", "Bone/Boo Flower": "bone", "Water Flower": "water", "Hammer Flower": "hammer",
}

GOAL_TEXT = {
    0: "beat Mario and Giga Mario in 5-3",
    1: "beat 5-4",
    2: "beat the boss rush in 1-0",
}
