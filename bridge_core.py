"""Archipelago-independent core of the A Koopa's Revenge 2 bridge.

The patched SWF talks to this over a local XMLSocket (TCP, messages end with a
NUL byte). The text protocol is deliberately trivial so the ActionScript 2 side
stays small. Fields are separated by "|".

Game -> bridge
  H|<version>                       hello, sent on connect
  S|var=value|var=value|...|cp=a,b|bk=a:1,b:2   snapshot of the watched _root variables
                                    (cp = checkpoint ids reached, bk = babies killed as level:number)

Bridge -> game
  F|<var>|0/1                       set a game flag
  W|1,2,3                           world unlock items received
  P|Fire Flower,Dragon Scale        power-up items received
  G|coins|100                       one-shot grant (never re-sent)
  D|<cause>                         DeathLink: kill the player (game must not echo it back)
  C|cheatsoff                       turn off the active cheat toggles (not Rush Coil)
  M|<level id>                      warp to a level from the map (w1l4, w2la, w1sp, ...)
  U|<colour number>                 give a power-up (map screen only; the game answers with an A| note)
Game -> bridge (extra)
  A|<text>                          a short note the client prints to the player
"""
import asyncio
import json
import os
import re
from collections import Counter
from typing import Callable, Dict, Iterable, List, Optional, Set

try:                                    # package import (inside Archipelago)
    from . import data as D
except ImportError:                     # plain import (tests)
    import data as D

POWERUPS = set(D.POWERUP_ITEMS)


# ----------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------
def parse_game_message(raw: str) -> dict:
    parts = raw.strip("\x00\r\n ").split("|")
    kind = parts[0]
    if kind == "H":
        return {"kind": "H", "version": parts[1] if len(parts) > 1 else "0"}
    if kind == "A":
        return {"kind": "A", "text": "|".join(parts[1:])}
    if kind == "S":
        vars_: Dict[str, int] = {}
        lists: Dict[str, Set[str]] = {"cp": set(), "bk": set()}
        for field in parts[1:]:
            k, _, v = field.partition("=")
            if not k:
                continue
            if k in lists:
                lists[k] = {c for c in v.split(",") if c}
                continue
            try:
                vars_[k] = int(float(v))
            except ValueError:
                vars_[k] = 1 if v.lower() == "true" else 0
        return {"kind": "S", "vars": vars_, "lists": lists}
    return {"kind": "?", "raw": raw}


# ----------------------------------------------------------------------
# Detection
# ----------------------------------------------------------------------
def satisfied(det: dict, vars_: Dict[str, int],
              lists: Optional[Dict[str, Set[str]]] = None) -> bool:
    kind = det["kind"]
    if kind == "checkpoint":
        return det["id"] in (lists or {}).get("cp", set())
    if kind == "baby":
        return det["id"] in (lists or {}).get("bk", set())
    if kind == "flag" and det.get("alt_var") and vars_.get(det["alt_var"], 0):
        return True
    if kind == "level_digit":
        value = vars_.get(det["var"])
        return value is not None and (value // det["weight"]) % 10 == 1
    if kind == "flag":
        return bool(vars_.get(det["var"], 0))
    if kind == "lives_ge":
        return vars_.get("lives", 0) >= det["value"]
    if kind == "coinscollected_ge":
        return vars_.get("coinscollected", 0) >= det["value"]
    raise ValueError(f"unknown detection kind {kind}")


class Detector:
    def __init__(self, table: Dict[str, dict]):
        self.table = table

    def evaluate(self, vars_: Dict[str, int], only: Optional[Iterable[str]] = None,
                 lists: Optional[Dict[str, Set[str]]] = None) -> Set[str]:
        names = self.table if only is None else only
        return {n for n in names if n in self.table and satisfied(self.table[n], vars_, lists)}


def goal_reached(goal: int, vars_: Dict[str, int]) -> bool:
    return satisfied(D.GOAL_DETECTION[goal], vars_)


# ----------------------------------------------------------------------
# Items
# ----------------------------------------------------------------------
def encode_state(item_names: List[str]) -> List[str]:
    """Idempotent messages describing everything currently received."""
    counts = Counter(item_names)
    lines = []
    for item, var in D.FLAG_ITEMS.items():
        lines.append(f"F|{var}|{1 if counts[item] else 0}")
    worlds = sorted(n for item, n in D.WORLD_ITEMS.items() if counts[item])
    lines.append("W|" + ",".join(str(n) for n in worlds))
    lines.append("P|" + ",".join(p for p in D.POWERUP_ITEMS if counts[p]))
    return lines


def encode_delta(item_name: str) -> Optional[str]:
    eff = D.DELTA_ITEMS.get(item_name)
    if not eff:
        return None
    kind, key, amount = eff
    return f"G|{key}|{amount}"


class DeltaStore:
    """Remembers how many received items already had their one-shot effect
    applied, per seed + slot, so reconnecting never re-grants coins or other one-shot items."""

    def __init__(self, path: Optional[str]):
        self.path = path
        self.data: Dict[str, int] = {}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.data = json.load(f)
            except (OSError, ValueError):
                self.data = {}

    def get(self, key: str) -> int:
        return int(self.data.get(key, 0))

    def set(self, key: str, value: int) -> None:
        self.data[key] = value
        if self.path:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.data, f)
            os.replace(tmp, self.path)


# ----------------------------------------------------------------------
# /warp helpers
# ----------------------------------------------------------------------
def parse_warp_target(text: str) -> Optional[str]:
    """'1-4', 'w1l4', '2-A', 'airship', 'yellow palace' -> a level id, or None."""
    t = text.strip().lower().replace(" ", "")
    t = t.replace("switchpalace", "").replace("palace", "").replace("switch", "")
    if t in D.WARP_ALIASES:
        target = D.WARP_ALIASES[t]
    else:
        m = re.fullmatch(r"w?(\d)[-l](\d|a)", t)
        target = f"w{m.group(1)}l{m.group(2)}" if m else t
    return target if target in D.warp_targets() else None


def final_level_open(vars_: Dict[str, int]) -> bool:
    """5-4 needs 5-3 cleared, all 7 koopaling stars and all 75 silver coins (the game's own rule)."""
    if (vars_.get("w5l3", 0) % 10) != 1:
        return False
    if not all(vars_.get(v, 0) for v, *_ in D.KOOPALINGS.values()):
        return False
    coins = 0
    for var, _name, _world, _secret, has_coins in D.LEVELS:
        if has_coins:
            value = vars_.get(var, 0)
            coins += sum(1 for w in D.COIN_PLACES.values() if (value // w) % 10 == 1)
    return coins >= 75


# ----------------------------------------------------------------------
# The bridge
# ----------------------------------------------------------------------
class Bridge:
    def __init__(self, loc_name_to_id: Dict[str, int], goal: int, store: DeltaStore,
                 store_key: str, enabled_locations: Optional[Set[str]] = None,
                 goal_items: Optional[Dict[str, int]] = None):
        self.detector = Detector(D.detection_table())
        self.loc_ids = loc_name_to_id
        self.goal = goal
        self.store, self.key = store, store_key
        self.enabled = enabled_locations      # None = all
        self.items: List[str] = []
        self.items_synced = False             # true after the first item list arrives
        self.sent: Set[str] = set()           # locations already reported
        self.goal_sent = False
        self.goal_items = {k: v for k, v in (goal_items or {}).items() if v > 0}   # item name -> count needed
        self.game_up = False
        self.note: Callable[[str], None] = lambda text: None     # where game notes are printed
        self.last_vars: Dict[str, int] = {}
        self._deaths_last: Optional[int] = None
        self._death_events = 0
        self.out: Callable[[List[str]], None] = lambda lines: None

    # --- game side -------------------------------------------------------
    def on_game_connected(self) -> None:
        self.game_up = True
        self._push_items()

    def on_game_disconnected(self) -> None:
        self.game_up = False

    def on_game_message(self, raw: str):
        """Returns (new location ids, goal reached)."""
        msg = parse_game_message(raw)
        if msg["kind"] == "H":
            self.on_game_connected()
            return [], False
        if msg["kind"] == "A":
            self.note(msg["text"])
            return [], False
        if msg["kind"] != "S":
            return [], False
        self.last_vars = msg["vars"]
        names = self.detector.evaluate(msg["vars"], self.enabled, msg["lists"])
        if not self.items_synced:
            # flags left over in an old save must not send cheat/palace checks before the
            # client knows which items this slot has received
            names -= set(D.CHEAT_CHECKS) | set(D.PALACES)
        deaths = msg["vars"].get("ap_deaths")
        if deaths is not None:
            if self._deaths_last is not None and deaths > self._deaths_last:
                self._death_events += deaths - self._deaths_last
            self._deaths_last = deaths
        fresh = [n for n in names if n not in self.sent and n in self.loc_ids]
        self.sent.update(fresh)
        goal = False
        if goal_reached(self.goal, msg["vars"]) and not self.store.get(self.key + ":goal_seen"):
            self.store.set(self.key + ":goal_seen", 1)       # remembered across restarts
        if not self.goal_sent and self.store.get(self.key + ":goal_seen") and self.goal_items_ok():
            self.goal_sent = goal = True
        return sorted(self.loc_ids[n] for n in fresh), goal

    # --- Archipelago side --------------------------------------------------
    def on_items(self, item_names: List[str]) -> List[int]:
        """Returns location ids to report: receiving a cheat item also sends its check."""
        self.items = list(item_names)
        self.items_synced = True
        ids = []
        for item in set(self.items):
            name = D.ITEM_AUTO_CHECKS.get(item)
            if (name and name in self.loc_ids and name not in self.sent
                    and (self.enabled is None or name in self.enabled)):
                self.sent.add(name)
                ids.append(self.loc_ids[name])
        self._push_items()
        return sorted(ids)

    # --- client commands ----------------------------------------------------
    def resync(self) -> bool:
        """Re-send the full item state (flags, worlds, power-ups). One-shot grants are not repeated."""
        if not self.game_up:
            return False
        self.out(encode_state(self.items))
        return True

    def kill(self) -> bool:
        """Kill the player (e.g. when stuck). Not counted as a death, so no DeathLink is sent."""
        if not self.game_up:
            return False
        self.incoming_death("client command")
        return True

    def cheats_off(self) -> bool:
        """Turn off the active cheat toggles (Space Jump, Screw Jump, Bloodshed, debug). Rush Coil stays."""
        if not self.game_up:
            return False
        self.out(["C|cheatsoff"])
        return True

    # --- /powerup ----------------------------------------------------------
    def powerup_list(self) -> List[str]:
        return [n for n in D.POWERUP_COLOURS if n in self.items]

    def powerup(self, text: str):
        """Returns (ok, message). Only power-ups you have received; the game applies it on the map."""
        if not self.game_up:
            return False, "The game is not connected - start the patched SWF."
        t = text.strip().lower().replace(" ", "").replace("flower", "")
        name = "Mushroom" if t == "mushroom" else D.POWERUP_ALIASES.get(t)
        if name is None:
            return False, f"Unknown power-up '{text}'. Try: fire, flight, dragon, spiny, thunder, bone, water, hammer, mushroom."
        if name != "Mushroom" and name not in self.items:
            return False, f"You have not received the {name} yet."
        colour = 1 if name == "Mushroom" else D.POWERUP_COLOURS[name]
        self.out([f"U|{colour}"])
        return True, f"Asked the game to give you the {name} (it only works on the map screen)."

    def _world_open(self, world: int) -> bool:
        need = "World 2 Unlock" if world == 0 else f"World {world} Unlock"
        return need in self.items

    def warp_list(self) -> List[str]:
        return [f"{tid} = {name}" for tid, (name, world) in D.warp_targets().items()
                if self._world_open(world)]

    def warp(self, text: str):
        """Returns (ok, message). The game must be on the map; the move happens as soon as it is."""
        if not self.game_up:
            return False, "The game is not connected - start the patched SWF."
        target = parse_warp_target(text)
        if target is None:
            return False, f"Unknown level '{text}'. Examples: 1-4, 2-A, 0-1, airship, yellow."
        name, world = D.warp_targets()[target]
        if not self._world_open(world):
            need = "World 2" if world == 0 else f"World {world}"
            return False, f"{name} is locked: you have not received the {need} unlock yet."
        if target == "w5l4" and not final_level_open(self.last_vars):
            return False, "5-4 needs 5-3 cleared, all 7 koopaling stars and all 75 silver coins first."
        self.out(["M|" + target])
        return True, f"Warping to {name} (it happens once you are on the map)."

    def goal_items_ok(self) -> bool:
        counts = Counter(self.items)
        return all(counts[name] >= need for name, need in self.goal_items.items())

    def goal_after_items(self) -> bool:
        """True once (and only once) when the game goal was already reached and the last required
        Silver Coin / Koopaling Star item has now arrived."""
        if not self.goal_sent and self.store.get(self.key + ":goal_seen") and self.goal_items_ok():
            self.goal_sent = True
            return True
        return False

    def take_deaths(self) -> int:
        """Number of player deaths seen since the last call (for DeathLink)."""
        n, self._death_events = self._death_events, 0
        return n

    def incoming_death(self, cause: str = "") -> None:
        if not self.game_up:
            return
        clean = "".join(c for c in cause if c not in "|\x00\r\n")[:80]
        self.out(["D|" + clean])

    def mark_checked(self, names: Iterable[str]) -> None:
        """Locations the server already knows about (e.g. after reconnect)."""
        self.sent.update(names)

    def _push_items(self) -> None:
        if not self.game_up:
            return
        lines = encode_state(self.items)
        done = self.store.get(self.key)
        for name in self.items[done:]:
            line = encode_delta(name)
            if line:
                lines.append(line)
        self.store.set(self.key, len(self.items))
        self.out(lines)


# ----------------------------------------------------------------------
# TCP server for the game (XMLSocket framing: messages end with NUL)
# ----------------------------------------------------------------------
class GameServer:
    def __init__(self, bridge: Bridge, on_result: Callable[[List[int], bool], "asyncio.Future"],
                 host: str = "127.0.0.1", port: int = 21221,
                 on_death: Optional[Callable[[int], "asyncio.Future"]] = None):
        self.bridge, self.on_result, self.on_death = bridge, on_result, on_death
        self.host, self.port = host, port
        self.writer: Optional[asyncio.StreamWriter] = None
        self.server: Optional[asyncio.AbstractServer] = None
        bridge.out = self._send

    def _send(self, lines: List[str]) -> None:
        if self.writer is None:
            return
        try:
            for line in lines:
                self.writer.write(line.encode("utf-8") + b"\x00")
        except Exception:
            self.writer = None

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._handle, self.host, self.port)

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        if self.writer is not None:               # newest connection wins
            self.writer.close()
        self.writer = writer
        buf = b""
        try:
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\x00" in buf:
                    raw, buf = buf.split(b"\x00", 1)
                    ids, goal = self.bridge.on_game_message(raw.decode("utf-8", "replace"))
                    if ids or goal:
                        await self.on_result(ids, goal)
                    deaths = self.bridge.take_deaths()
                    if deaths and self.on_death:
                        await self.on_death(deaths)
        finally:
            if self.writer is writer:
                self.writer = None
                self.bridge.on_game_disconnected()
            writer.close()

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()
