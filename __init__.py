from typing import Dict, List

from BaseClasses import Item, ItemClassification, Location, Region, Tutorial
from worlds.AutoWorld import WebWorld, World

from . import data
from .options import KoopaOptions

D = data


class KoopaItem(Item):
    game = D.GAME_NAME


class KoopaLocation(Location):
    game = D.GAME_NAME


def _build_tables():
    items: List[str] = (
        list(D.WORLD_ITEMS) + D.BLOCK_ITEMS + D.POWERUP_ITEMS + D.CHEAT_ITEMS
        + [D.SILVER_COIN_ITEM, D.STAR_ITEM]
        + list(D.FILLER_ITEMS) + list(D.OPTIONAL_FILLER)
    )
    item_ids = {n: D.BASE_ID + i for i, n in enumerate(items)}

    locs: List[str] = []
    locs += [n for n, _, _ in D.level_locations()]
    locs += [n for n, _, _ in D.checkpoint_locations()]
    locs += [n for n, _, _ in D.baby_locations()]
    locs += [f"Koopaling Star: {k}" for k in D.KOOPALINGS]
    locs += list(D.PALACES)
    locs += list(D.CHEAT_CHECKS)
    locs += [f"Flower Face {i}" for i in range(1, D.FLOWER_FACE_MAX + 1)]
    loc_ids = {n: D.BASE_ID + i for i, n in enumerate(locs)}
    return item_ids, loc_ids


ITEM_IDS, LOC_IDS = _build_tables()


class KoopaWeb(WebWorld):
    theme = "grassFlowers"
    tutorials = [Tutorial(
        "Setup Guide", "How to play A Koopa's Revenge 2 with Archipelago.",
        "English", "setup_en.md", "setup/en", ["TBD"])]


class KoopaWorld(World):
    """A Koopa's Revenge 2: a Flash platformer where you play as a Koopa."""
    game = D.GAME_NAME
    web = KoopaWeb()
    options_dataclass = KoopaOptions
    options: KoopaOptions
    topology_present = False
    item_name_to_id = ITEM_IDS
    location_name_to_id = LOC_IDS

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _world_count(self, state) -> int:
        return sum(state.has(f"World {n} Unlock", self.player) for n in range(1, 6))

    def _eval(self, state, r) -> bool:
        """One requirement: a tuple is "any of these", a list is "all of these", "Flight" is the
        Flight Petal (or the Dragon Scale once the pink blocks are active), anything else is an item."""
        p = self.player
        if isinstance(r, tuple):
            return any(self._eval(state, x) for x in r)
        if isinstance(r, list):
            return all(self._eval(state, x) for x in r)
        if r == D.FLIGHT:
            return state.has("Flight Petal", p) or (
                state.has("Dragon Scale", p) and state.has(D.PINK_EVENT_ITEM, p))
        return state.has(r, p)

    def _has_all(self, state, reqs) -> bool:
        return all(self._eval(state, r) for r in reqs)

    def _rule(self, reqs, worlds=None):
        """Build an access rule from an item requirement list plus an optional
        'any of these worlds' condition."""
        worlds = worlds or []

        def rule(state):
            if worlds and not any(state.has(f"World {n} Unlock", self.player) for n in worlds):
                return False
            return self._has_all(state, reqs)
        return rule

    def _goal_item_requirements(self):
        """(Silver Coin items, Koopaling Star items) needed to finish. The 5-3 goal only needs them if
        the option is on; the 5-4 and boss rush goals always do."""
        o = self.options
        if o.goal.value == 0 and not o.castle_mario_goal_requires_items:
            return 0, 0
        return o.silver_coin_items.value, o.koopaling_star_items.value

    def create_item(self, name: str) -> KoopaItem:
        if name == D.SILVER_COIN_ITEM:       # many copies: don't let them dominate balancing
            cls = getattr(ItemClassification, "progression_skip_balancing", ItemClassification.progression)
        elif name in D.PROGRESSION_ITEMS:
            cls = ItemClassification.progression
        elif name in D.FILLER_ITEMS or name in D.OPTIONAL_FILLER:
            cls = ItemClassification.filler
        else:
            cls = ItemClassification.useful
        return KoopaItem(name, cls, self.item_name_to_id[name], self.player)

    def get_filler_item_name(self) -> str:
        pool = dict(D.FILLER_ITEMS)
        if self.options.power_star_filler:
            pool.update(D.OPTIONAL_FILLER)
        return self.random.choices(list(pool), weights=list(pool.values()))[0]

    # ------------------------------------------------------------------
    def create_regions(self) -> None:
        o = self.options
        mw, p = self.multiworld, self.player
        menu = Region("Menu", p, mw)
        mw.regions.append(menu)
        worlds: Dict[int, Region] = {}
        for n in range(0, 6):
            r = Region(f"World {n}", p, mw)
            worlds[n] = r
            mw.regions.append(r)
            if n == 0:
                # World 0-1 (tutorial) is only reachable once World 2 is unlocked.
                menu.connect(r, "To World 0", lambda s: s.has("World 2 Unlock", p))
            else:
                item = f"World {n} Unlock"
                menu.connect(r, f"To World {n}", lambda s, i=item: s.has(i, p))
        self.menu, self.world_regions = menu, worlds

        def add(region: Region, name: str):
            loc = KoopaLocation(p, name, self.location_name_to_id[name], region)
            region.locations.append(loc)
            return loc

        def event(region, pair):
            loc = KoopaLocation(p, pair[0], None, region)
            loc.place_locked_item(KoopaItem(pair[1], ItemClassification.progression, None, p))
            region.locations.append(loc)
            return loc

        for name, world, det in D.level_locations():
            if det[2] == 10 and not o.secret_exit_checks:
                continue
            if det[2] >= 1000 and not o.silver_coin_checks:
                continue
            loc = add(worlds[world], name)
            if det[2] == 10 and det[1] in D.SECRET_REQUIREMENTS:
                loc.access_rule = self._rule(D.SECRET_REQUIREMENTS[det[1]])
            elif det[2] >= 1000:
                coin_no = {100000: 1, 10000: 2, 1000: 3}[det[2]]
                reqs = D.COIN_REQUIREMENTS.get((det[1], coin_no))
                if reqs:
                    loc.access_rule = self._rule(reqs)

        if o.checkpoint_checks:
            for name, world, _ in D.checkpoint_locations():
                add(worlds[world], name)
        if o.baby_kill_checks:
            for name, world, _ in D.baby_locations():
                add(worlds[world], name)

        for k, (_, world, _, reqs) in D.KOOPALINGS.items():
            loc = add(worlds[world], f"Koopaling Star: {k}")
            loc.access_rule = self._rule(reqs)
            star = event(worlds[world], D.star_event(k))     # "star obtained" for the 5-4 requirement
            star.access_rule = self._rule(reqs)

        for name, (_, world) in D.PALACES.items():
            add(worlds[world], name)

        for name, (wl, reqs) in D.CHEAT_RULES.items():
            if len(wl) == 1:
                loc = add(worlds[wl[0]], name)
                loc.access_rule = self._rule(reqs)
            else:
                loc = add(menu, name)
                loc.access_rule = self._rule(reqs, wl)

        # Event: pink blocks become active once the Pink Switch is hit
        # (it can be found at any switch palace, so any of worlds 1-4).
        pink = KoopaLocation(p, D.PINK_EVENT_LOCATION, None, menu)
        pink.place_locked_item(KoopaItem(D.PINK_EVENT_ITEM, ItemClassification.progression, None, p))
        pink.access_rule = self._rule([], [1, 2, 3, 4])
        menu.locations.append(pink)

        for i in range(1, o.flower_face_checks.value + 1):
            add(menu, f"Flower Face {i}")

        event(worlds[5], D.EVENT_GIGA_MARIO)
        event(worlds[5], D.EVENT_5_3)
        for n in range(1, 6):                               # all 75 silver coins = every world 1-5
            coin_ev = event(worlds[n], D.coin_event(n))
            # every silver coin of the world must be reachable, including the ones that need items
            world_reqs = [r for (var, _), rs in D.COIN_REQUIREMENTS.items()
                          if D.LEVEL_BY_VAR[var][2] == n for r in rs]
            coin_ev.access_rule = self._rule(world_reqs)
        final = event(worlds[5], D.EVENT_5_4)
        needed = [D.EVENT_5_3[1]] + [D.star_event(k)[1] for k in D.KOOPALINGS] \
            + [D.coin_event(n)[1] for n in range(1, 6)]
        final.access_rule = lambda s, need=needed: all(s.has(i, p) for i in need)
        rush = event(worlds[1], D.EVENT_BOSS_RUSH)       # boss rush is in 1-0 (airship)
        rush.access_rule = lambda s: s.has(D.EVENT_5_4[1], p)

        goal_item = {0: D.EVENT_GIGA_MARIO, 1: D.EVENT_5_4, 2: D.EVENT_BOSS_RUSH}[o.goal.value]
        req_coins, req_stars = self._goal_item_requirements()

        def can_win(s, gi=goal_item[1], rc=req_coins, rs=req_stars):
            return (s.has(gi, p) and s.has(D.SILVER_COIN_ITEM, p, rc) and s.has(D.STAR_ITEM, p, rs))

        mw.completion_condition[p] = can_win

    def create_items(self) -> None:
        o = self.options
        start = f"World {o.starting_world.value} Unlock"
        self.multiworld.push_precollected(self.create_item(start))

        pool: List[KoopaItem] = []
        for n in D.WORLD_ITEMS:
            if n != start:
                pool.append(self.create_item(n))
        for n in D.BLOCK_ITEMS + D.POWERUP_ITEMS + D.CHEAT_ITEMS:
            pool.append(self.create_item(n))
        for _ in range(o.silver_coin_items.value):
            pool.append(self.create_item(D.SILVER_COIN_ITEM))
        for _ in range(o.koopaling_star_items.value):
            pool.append(self.create_item(D.STAR_ITEM))

        total = sum(1 for r in self.multiworld.regions if r.player == self.player
                    for l in r.locations if l.address is not None)
        n_fill = total - len(pool)
        if n_fill < 0:
            raise Exception(
                f"A Koopa's Revenge 2 ({self.player_name}): {len(pool)} items but only {total} locations. "
                "Turn more check types on or lower the Silver Coin / Koopaling Star item counts.")
        for _ in range(n_fill):
            pool.append(self.create_item(self.get_filler_item_name()))
        self.multiworld.itempool += pool

    def set_rules(self) -> None:
        p, mw, o = self.player, self.multiworld, self.options
        # Heuristic progression gating for the count based checks.
        for i in range(1, o.flower_face_checks.value + 1):
            need = min(5, 1 + (i - 1) // 9)
            mw.get_location(f"Flower Face {i}", p).access_rule = \
                lambda s, n=need: self._world_count(s) >= n

    def fill_slot_data(self) -> dict:
        o = self.options
        return {
            "goal": o.goal.value,
            "goal_silver_coins": self._goal_item_requirements()[0],
            "goal_koopaling_stars": self._goal_item_requirements()[1],
            "death_link": bool(o.death_link),
            "starting_world": o.starting_world.value,
            "silver_coin_checks": bool(o.silver_coin_checks),
            "secret_exit_checks": bool(o.secret_exit_checks),
            "checkpoint_checks": bool(o.checkpoint_checks),
            "baby_kill_checks": bool(o.baby_kill_checks),
            "flower_face_checks": o.flower_face_checks.value,
        }


# Launcher entry for the client (guarded so the module also imports in tests).
try:
    from worlds.LauncherComponents import Component, Type, components, launch_subprocess

    def _launch_client(*args):
        from .Client import launch
        launch_subprocess(launch, name="KoopaClient", args=args)

    components.append(Component("A Koopa's Revenge 2 Client", func=_launch_client,
                                component_type=Type.CLIENT))
except ImportError:
    pass
