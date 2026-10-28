from dataclasses import dataclass

from Options import Choice, DeathLink, PerGameCommonOptions, Range, Toggle, DefaultOnToggle

from .data import FLOWER_FACE_MAX, SILVER_COIN_ITEM_MAX, STAR_ITEM_MAX


class Goal(Choice):
    """What completes your game.
    mario_giga_mario: beat Mario and Giga Mario in 5-3.
    beat_5_4: beat the true ending in 5-4.
    boss_rush: beat the boss rush in 1-0 (the airship), which unlocks after beating 5-4."""
    display_name = "Goal"
    option_mario_giga_mario = 0
    option_beat_5_4 = 1
    option_boss_rush = 2
    default = 1


class StartingWorld(Choice):
    """World whose unlock item you start with."""
    display_name = "Starting World"
    option_world_1 = 1
    option_world_2 = 2
    option_world_3 = 3
    option_world_4 = 4
    option_world_5 = 5
    default = 1


class SilverCoinChecks(DefaultOnToggle):
    """Each silver coin in each level is a check (75 total)."""
    display_name = "Silver Coin Checks"


class SecretExitChecks(DefaultOnToggle):
    """Each secret exit is a check."""
    display_name = "Secret Exit Checks"


class CheckpointChecks(DefaultOnToggle):
    """Each checkpoint is a check: one per level plus the boss room checkpoints (31 total)."""
    display_name = "Checkpoint Checks"


class BabyKillChecks(DefaultOnToggle):
    """Each of the 4 babies in every level is a check (100 total)."""
    display_name = "Baby Kill Checks"


class FlowerFaceChecks(Range):
    """Number of flower face unlock checks (face N unlocks at 500*N coins collected)."""
    display_name = "Flower Face Checks"
    range_start = 0
    range_end = FLOWER_FACE_MAX
    default = FLOWER_FACE_MAX


class SilverCoinItems(Range):
    """How many Silver Coin items are added to the item pool (the game has 75 silver coins).
    The goal is not complete until you have received all of them. 0 turns this requirement off."""
    display_name = "Silver Coin Items"
    range_start = 0
    range_end = SILVER_COIN_ITEM_MAX
    default = 75


class KoopalingStarItems(Range):
    """How many Koopaling Star items are added to the item pool (the game has 7 koopalings).
    The goal is not complete until you have received all of them. 0 turns this requirement off."""
    display_name = "Koopaling Star Items"
    range_start = 0
    range_end = STAR_ITEM_MAX
    default = 7


class CastleMarioGoalRequiresItems(Toggle):
    """If the goal is beating Mario and Giga Mario in 5-3, also require the Silver Coin and Koopaling
    Star items. Ignored (always required) when the goal is beating 5-4 or the boss rush."""
    display_name = "Castle Mario Goal Requires Items"


class PowerStarFiller(Toggle):
    """Add Power Stars to the filler item pool (they are not randomized otherwise)."""
    display_name = "Power Star Filler"


@dataclass
class KoopaOptions(PerGameCommonOptions):
    goal: Goal
    silver_coin_items: SilverCoinItems
    koopaling_star_items: KoopalingStarItems
    castle_mario_goal_requires_items: CastleMarioGoalRequiresItems
    death_link: DeathLink
    starting_world: StartingWorld
    silver_coin_checks: SilverCoinChecks
    secret_exit_checks: SecretExitChecks
    checkpoint_checks: CheckpointChecks
    baby_kill_checks: BabyKillChecks
    flower_face_checks: FlowerFaceChecks
    power_star_filler: PowerStarFiller
