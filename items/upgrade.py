from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.asset_paths import item_asset
from core.settings import (
    LAGER_LAUNCHER_COOLDOWN,
    LAGER_LAUNCHER_BUFF_DURATION,
    LAGER_LAUNCHER_BUFF_MULTIPLIER,
    PLAYER_ANIMATION_SOURCE_FRAME_SIZE,
    ROBIN_HOOD_CHARACTER_PATH,
    TOWER_ARCHER_ATTACK_SPEED,
    TOWER_ARCHER_DAMAGE,
    TOWER_ARCHER_RANGE,
    TURRET_ATTACK_SPEED,
    TURRET_DAMAGE,
    TURRET_RANGE,
)
from .item import Item
from core.units import meters_label

if TYPE_CHECKING:
    from sprites import Tower


@dataclass(frozen=True, kw_only=True)
class TowerUpgrade(Item):
    item_type: str = field(default="upgrade", init=False)
    weight: int
    effects: dict[str, float | bool] = field(default_factory=dict)

    @property
    def stat_lines(self) -> tuple[str, ...]:
        lines = [f"Weight: {self.weight}"]
        if "damage_reflection" in self.effects:
            lines.append(
                f"Damage reflected: {round(float(self.effects['damage_reflection']) * 100)}%"
            )
        if "defense_bonus" in self.effects:
            lines.append(f"Tower defense: +{int(self.effects['defense_bonus'])}")
        if self.effects.get("lager_launcher"):
            bonus = round((LAGER_LAUNCHER_BUFF_MULTIPLIER - 1) * 100)
            duration = LAGER_LAUNCHER_BUFF_DURATION
            lines.extend(
                (
                    f"Cooldown: {LAGER_LAUNCHER_COOLDOWN:g} s",
                    f"Possible: +{bonus}% damage for {duration:g} s",
                    f"Possible: +{bonus}% attack speed for {duration:g} s",
                    f"Possible: +{bonus}% movement speed for {duration:g} s",
                )
            )
        if self.effects.get("turret"):
            lines.append(
                f"Shots: {TURRET_DAMAGE:g} damage | "
                f"{meters_label(TURRET_RANGE)} | every {TURRET_ATTACK_SPEED:g} s"
            )
        if self.effects.get("tower_archer"):
            lines.append(
                f"Arrows: {TOWER_ARCHER_DAMAGE:g} damage | "
                f"{meters_label(TOWER_ARCHER_RANGE)} | "
                f"every {TOWER_ARCHER_ATTACK_SPEED:g} s"
            )
        return tuple(lines)

    def apply_to_tower(self, tower: "Tower") -> None:
        tower.defense += int(self.effects.get("defense_bonus", 0))
        tower.damage_reflection += float(
            self.effects.get("damage_reflection", 0.0)
        )
        if self.effects.get("lager_launcher", False):
            tower.lager_launcher_enabled = True
        if self.effects.get("wooden_stakes", False):
            tower.wooden_stakes_enabled = True
        if self.effects.get("turret", False):
            tower.turret_enabled = True
        if self.effects.get("tower_archer", False):
            tower.archer_enabled = True


COMMON_UPGRADES = (
    TowerUpgrade(
        item_id="wooden_stakes",
        rarity="common",
        weight=2,
        name="Wooden Stakes",
        image_path=item_asset("wooden_stakes.png"),
        description="A prickly deterrent that reflects damage.",
        effects={"damage_reflection": 0.25, "wooden_stakes": True},
    ),
    TowerUpgrade(
        item_id="reinforced_bricks",
        rarity="common",
        weight=4,
        name="Reinforced Bricks",
        image_path=item_asset("reinforced_bricks.png"),
        description="Sturdy masonry inspired by the fourth little pig.",
        effects={"defense_bonus": 25},
    ),
)

UNCOMMON_UPGRADES = (
    TowerUpgrade(
        item_id="tower_archer",
        rarity="uncommon",
        weight=3,
        name="Archer",
        image_path=ROBIN_HOOD_CHARACTER_PATH / "D_Idle.png",
        image_crop=(0, 0, *PLAYER_ANIMATION_SOURCE_FRAME_SIZE),
        description="This is literally his whole job",
        effects={"tower_archer": True},
    ),
)

RARE_UPGRADES = (
    TowerUpgrade(
        item_id="lager_launcher",
        rarity="rare",
        weight=5,
        name="Lager Launcher",
        image_path=item_asset("lager_launcher.png"),
        description="It's 8:00 AM somewhere. Patent Pending Pilsner Propulsion.",
        effects={"lager_launcher": True},
    ),
)

LEGENDARY_UPGRADES = (
    TowerUpgrade(
        item_id="turret",
        rarity="legendary",
        weight=10,
        name="Turret",
        image_path=item_asset("turret.png"),
        description="I'm not sure how they get the ammo for this",
        effects={"turret": True},
    ),
)

UPGRADE_CATALOG = (
    *COMMON_UPGRADES,
    *UNCOMMON_UPGRADES,
    *RARE_UPGRADES,
    *LEGENDARY_UPGRADES,
)
