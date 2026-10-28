"""Archipelago client for A Koopa's Revenge 2.

Run it from the Archipelago Launcher ("A Koopa's Revenge 2 Client") or with
  python -m worlds.koopas_revenge_2.Client --connect host:port --name Slot
then start the patched SWF; it connects to this client on 127.0.0.1:21221.

NOTE: written against Archipelago 0.5.x's CommonClient. It has not been run
against a real server yet (no Archipelago install was available when writing).
"""
import asyncio
import os
import typing

import Utils
from CommonClient import (ClientCommandProcessor, CommonContext, get_base_parser,
                          gui_enabled, handle_url_arg, logger, server_loop)
from NetUtils import ClientStatus

from . import ITEM_IDS, LOC_IDS
from . import data as D
from .bridge_core import Bridge, DeltaStore, GameServer

ID_TO_ITEM = {v: k for k, v in ITEM_IDS.items()}
ID_TO_LOC = {v: k for k, v in LOC_IDS.items()}


class KoopaCommandProcessor(ClientCommandProcessor):
    def _game_cmd(self, name: str, ok_text: str):
        bridge = self.ctx.bridge
        if bridge is None:
            logger.info("Connect to the Archipelago server first.")
        elif getattr(bridge, name)():
            logger.info(ok_text)
        else:
            logger.info("The game is not connected - start the patched SWF.")

    def _cmd_game(self):
        """Show whether the game is connected to the bridge."""
        up = self.ctx.bridge is not None and self.ctx.bridge.game_up
        logger.info("Game connected." if up else "Game NOT connected - start the patched SWF.")

    def _cmd_resync(self):
        """Re-send every received item (blocks, cheats, worlds, power-ups) to the game."""
        self._game_cmd("resync", "Items re-sent to the game.")

    def _cmd_kill(self):
        """Kill your Koopa (useful when stuck). Does not send a DeathLink."""
        self._game_cmd("kill", "Sent kill command.")

    def _cmd_cheatsoff(self):
        """Turn off every active cheat toggle (Space Jump, Screw Jump, Bloodshed, debug). Rush Coil stays on."""
        self._game_cmd("cheats_off", "Cheats turned off (Rush Coil unchanged).")

    def _cmd_disablecheats(self):
        """Same as /cheatsoff."""
        self._cmd_cheatsoff()

    def _cmd_powerup(self, name: str = ""):
        """Give yourself a power-up you have unlocked, on the map screen only: /powerup fire, flight, dragon, spiny, thunder, bone, water, hammer. No argument lists yours."""
        bridge = self.ctx.bridge
        if bridge is None:
            logger.info("Connect to the Archipelago server first.")
        elif not name:
            have = bridge.powerup_list()
            logger.info("Power-ups you can give yourself: " + (", ".join(have) if have else "(none unlocked yet)"))
        else:
            logger.info(bridge.powerup(name)[1])

    def _cmd_warp(self, target: str = ""):
        """Teleport to a level from the map: /warp 1-4, /warp 2-A, /warp airship, /warp yellow. No argument lists the levels you can warp to."""
        bridge = self.ctx.bridge
        if bridge is None:
            logger.info("Connect to the Archipelago server first.")
        elif not target:
            options = bridge.warp_list()
            logger.info("You can warp to: " + (", ".join(options) if options else "(nothing unlocked yet)"))
        else:
            logger.info(bridge.warp(target)[1])




class KoopaContext(CommonContext):
    game = D.GAME_NAME
    command_processor = KoopaCommandProcessor
    items_handling = 0b111          # receive everything, including starting items and own items

    def __init__(self, server_address, password, game_port: int):
        super().__init__(server_address, password)
        self.bridge: typing.Optional[Bridge] = None
        self.game_server: typing.Optional[GameServer] = None
        self.game_port = game_port
        self.death_link_on = False
        self.store = DeltaStore(os.path.join(Utils.user_path(), "koopas_revenge_2_state.json"))

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def _item_names(self) -> typing.List[str]:
        return [ID_TO_ITEM[i.item] for i in self.items_received if i.item in ID_TO_ITEM]

    async def _report(self, location_ids: typing.List[int], goal: bool):
        if location_ids:
            await self.send_msgs([{"cmd": "LocationChecks", "locations": location_ids}])
        if goal:
            await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])

    async def _on_death(self, count: int):
        """The player died in the game: send one DeathLink (if enabled)."""
        if not self.death_link_on:
            return
        try:
            name = self.player_names[self.slot]
        except Exception:
            name = "Koopa"
        await self.send_death(f"{name} was defeated in A Koopa's Revenge 2")

    def on_deathlink(self, data: dict):
        super().on_deathlink(data)
        if self.death_link_on and self.bridge is not None:
            self.bridge.incoming_death(f"{data.get('source', 'someone')}")

    def on_package(self, cmd: str, args: dict):
        if cmd == "Connected":
            slot_data = args.get("slot_data", {})
            self.death_link_on = bool(slot_data.get("death_link", False))
            if self.death_link_on:
                asyncio.create_task(self.update_death_link(True), name="DeathLinkTag")
            existing = set(args.get("missing_locations", [])) | set(args.get("checked_locations", []))
            enabled = {n for n, i in LOC_IDS.items() if i in existing}
            key = f"{self.seed_name}:{self.slot}"
            goal_items = {D.SILVER_COIN_ITEM: int(slot_data.get("goal_silver_coins", 0)),
                          D.STAR_ITEM: int(slot_data.get("goal_koopaling_stars", 0))}
            self.bridge = Bridge(LOC_IDS, int(slot_data.get("goal", 1)), self.store, key, enabled,
                                 goal_items)
            self.bridge.mark_checked(ID_TO_LOC[i] for i in self.checked_locations if i in ID_TO_LOC)
            self.bridge.note = logger.info
            if self.game_server is None:
                self.game_server = GameServer(self.bridge, self._report, port=self.game_port,
                                            on_death=self._on_death)
                asyncio.create_task(self.game_server.start(), name="GameServer")
            else:
                self.game_server.bridge = self.bridge
                self.bridge.out = self.game_server._send
        elif cmd == "ReceivedItems" and self.bridge is not None:
            ids = self.bridge.on_items(self._item_names())
            goal = self.bridge.goal_after_items()
            if ids or goal:       # a cheat item also sends its check; the last goal item can finish the game
                asyncio.create_task(self._report(ids, goal), name="ItemChecks")

    async def shutdown(self):
        if self.game_server:
            await self.game_server.stop()
        await super().shutdown()


def launch(*launch_args: str) -> None:
    async def main(args):
        ctx = KoopaContext(args.connect, args.password, args.game_port)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        await ctx.exit_event.wait()
        ctx.server_address = None
        await ctx.shutdown()

    parser = get_base_parser(description="A Koopa's Revenge 2 Archipelago client")
    parser.add_argument("--game-port", type=int, default=21221, help="local port the patched SWF connects to")
    parser.add_argument("url", nargs="?", help="archipelago://name:pass@host:port")
    args = parser.parse_args(launch_args)
    args = handle_url_arg(args, parser=parser)

    import colorama
    colorama.just_fix_windows_console()
    asyncio.run(main(args))
    colorama.deinit()


if __name__ == "__main__":
    import sys
    launch(*sys.argv[1:])
