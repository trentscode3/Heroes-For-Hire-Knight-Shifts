from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.asset_paths import item_asset
from core.settings import (
    PORTAL_BOOTS_COOLDOWN,
    ROCKET_BOOTS_COOLDOWN,
    ROCKET_BOOTS_DISTANCE,
)
from .item import Item
from core.units import meters_label

if TYPE_CHECKING:
    from sprites import Player


GEAR_TYPES = ("boots", "chest", "head", "gloves")


@dataclass(frozen=True, kw_only=True)
class Gear(Item):
    item_type: str = field(default="gear", init=False)
    gear_type: str
    effects: dict[str, float | bool | str] = field(default_factory=dict)

    @property
    def effect_lines(self) -> tuple[str, ...]:
        lines = []
        if "attack_area_multiplier" in self.effects:
            value = float(self.effects["attack_area_multiplier"])
            lines.append(f"Attack area and range: +{round((value - 1) * 100)}%")
        if "move_speed_multiplier" in self.effects:
            value = float(self.effects["move_speed_multiplier"])
            lines.append(f"Movement speed: +{round((value - 1) * 100)}%")
        if "base_damage_bonus" in self.effects:
            bonus = round(float(self.effects["base_damage_bonus"]) * 100)
            lines.append(f"Base damage: +{bonus}%")
        if "attack_rate_multiplier" in self.effects:
            value = float(self.effects["attack_rate_multiplier"])
            lines.append(f"Attack speed: +{round((value - 1) * 100)}%")
        if "crit_chance_bonus" in self.effects:
            bonus = round(float(self.effects["crit_chance_bonus"]) * 100)
            lines.append(f"Critical chance: +{bonus}%")
        if self.effects.get("enemy_stick"):
            lines.append("Non-boss enemies stick to the Hero")
        mobility = self.effects.get("mobility_ability")
        if mobility == "rocket":
            lines.append(
                f"Space: dash {meters_label(ROCKET_BOOTS_DISTANCE)} toward the pointer "
                f"({ROCKET_BOOTS_COOLDOWN:g} s cooldown)"
            )
        elif mobility == "portal":
            lines.append(
                f"Space: teleport safely to the pointer "
                f"({PORTAL_BOOTS_COOLDOWN:g} s cooldown)"
            )
        if "boss_damage_reduction" in self.effects:
            reduction = round(float(self.effects["boss_damage_reduction"]) * 100)
            lines.append(f"Boss damage taken: -{reduction}%")
        return tuple(lines)

    def apply_to_player(self, player: "Player") -> None:
        attack_area = self.effects.get("attack_area_multiplier", 1.0)
        player.base_attack_radius *= attack_area
        player.base_attack_half_angle *= attack_area
        player.attack_area_upgrade_multiplier *= attack_area

        player.base_move_speed *= self.effects.get(
            "move_speed_multiplier",
            1.0,
        )
        player.base_attack_damage *= 1.0 + self.effects.get(
            "base_damage_bonus",
            0.0,
        )
        player.base_attack_speed /= self.effects.get(
            "attack_rate_multiplier",
            1.0,
        )
        player.crit_chance += float(self.effects.get("crit_chance_bonus", 0.0))
        if self.effects.get("enemy_stick", False):
            player.enemies_stick_to_player = True
        mobility = self.effects.get("mobility_ability")
        if isinstance(mobility, str):
            player.mobility_ability = mobility
        player.boss_damage_reduction += float(
            self.effects.get("boss_damage_reduction", 0.0)
        )


COMMON_GEAR = (
    Gear(
        item_id="wide_eyed_helmet",
        gear_type="head",
        rarity="common",
        name="Wide-Eyed Helmet",
        image_path=item_asset("wide_eyed_helmet.png"),
        effects={"attack_area_multiplier": 1.25},
        description="Improves visibility for a larger melee attack area.",
    ),
    Gear(
        item_id="machasins",
        gear_type="boots",
        rarity="common",
        name="Machasins",
        image_path=item_asset("machasins.png"),
        effects={"move_speed_multiplier": 1.2},
        description="Protects your feet and increases movement speed.",
    ),
    Gear(
        item_id="chest_plate",
        gear_type="chest",
        rarity="common",
        name="Chest Plate",
        image_path=item_asset("chest_plate.png"),
        description="Increases defenses against bosses",
        effects={"boss_damage_reduction": 0.25},
    ),
    Gear(
        item_id="garden_gloves",
        gear_type="gloves",
        rarity="common",
        name="Garden Gloves",
        image_path=item_asset("garden_gloves.png"),
        effects={"attack_rate_multiplier": 1.2},
        description="Provides a steadier grip for faster attacks.",
    ),
)

UNCOMMON_GEAR = (
    Gear(
        item_id="fake_abs",
        gear_type="chest",
        rarity="uncommon",
        name="Fake Abs",
        image_path=item_asset("fake_abs.png"),
        effects={"base_damage_bonus": 0.25},
        description="Makes every swing feel heavier and more convincing.",
    ),
    Gear(
        item_id="tacticool_glasses",
        gear_type="head",
        rarity="uncommon",
        name="Tacticool Glasses",
        image_path=item_asset("tacticool_glasses.png"),
        description="Allows the user to see an opponent's weak strategies",
        effects={"crit_chance_bonus": 0.20},
    ),
    Gear(
        item_id="rocket_boots",
        gear_type="boots",
        rarity="uncommon",
        name="Rocket Boots",
        image_path=item_asset("rocket_boots.png"),
        description="Buckle up and press space",
        effects={"mobility_ability": "rocket"},
    ),
)

RARE_GEAR = (
    Gear(
        item_id="sticky_fingers",
        gear_type="gloves",
        rarity="rare",
        name="Sticky Fingers",
        image_path=item_asset("sticky_fingers.png"),
        description="The Hero ate wings for dinner",
        effects={"enemy_stick": True},
    ),
)

LEGENDARY_GEAR = (
    Gear(
        item_id="portal_boots",
        gear_type="boots",
        rarity="legendary",
        name="Portal Boots",
        image_path=item_asset("portal_boots.png"),
        description="Press space to teleport to the mouse pointer",
        effects={"mobility_ability": "portal"},
    ),
)

GEAR_CATALOG = (*COMMON_GEAR, *UNCOMMON_GEAR, *RARE_GEAR, *LEGENDARY_GEAR)
