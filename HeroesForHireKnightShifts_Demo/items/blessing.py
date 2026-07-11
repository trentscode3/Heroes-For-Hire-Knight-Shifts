from dataclasses import dataclass, field

from core.asset_paths import item_asset
from .item import Item


@dataclass(frozen=True, kw_only=True)
class Blessing(Item):
    item_type: str = field(default="blessing", init=False)
    effect_type: str = ""
    effect_value: float = 0.0

    @property
    def value(self) -> float:
        return self.effect_value

    @property
    def effect_lines(self) -> tuple[str, ...]:
        if self.effect_type == "xp_gain":
            return (f"Nighttime XP gained: +{round(self.effect_value * 100)}%",)
        if self.effect_type == "tower_weight":
            return (f"Tower maximum weight: +{int(self.effect_value)}",)
        if self.effect_type == "crit_damage":
            return (f"{self.effect_value:g}x crit damage",)
        if self.effect_type == "anti_hoarding":
            return ("Owned items no longer appear in shop offers",)
        return ()


RARITIES = ("common", "uncommon", "rare", "legendary")
QUICK_LEARNER_VALUES = (0.20, 0.40, 0.60, 0.80)
BLUEPRINT_VALUES = (2, 4, 7, 10)

QUICK_LEARNER_DESCRIPTIONS = (
    "Your brain is big.",
    "Your brain is huge.",
    "Your brain is massive.",
    "Your brain is enormous.",
)

BLESSING_CATALOG = tuple(
    Blessing(
        item_id="quick_learner",
        rarity=rarity,
        name="Quick Learner",
        image_path=item_asset("brain.png"),
        description=description,
        effect_type="xp_gain",
        effect_value=value,
    )
    for rarity, value, description in zip(
        RARITIES,
        QUICK_LEARNER_VALUES,
        QUICK_LEARNER_DESCRIPTIONS,
    )
) + tuple(
    Blessing(
        item_id="better_blueprint_paper",
        rarity=rarity,
        name="Better Blueprint Paper",
        image_path=item_asset("better_blueprint.png"),
        description="We gotta get more of this stuff.",
        effect_type="tower_weight",
        effect_value=value,
    )
    for rarity, value in zip(RARITIES, BLUEPRINT_VALUES)
) + (
    Blessing(
        item_id="pressure_point_studies",
        rarity="rare",
        name="Pressure Point Studies",
        image_path=item_asset("pressure_point.png"),
        description="Unlocks forbidden enemy pressure points.",
        effect_type="crit_damage",
        effect_value=2.0,
    ),
    Blessing(
        item_id="anti_hoarding_spell",
        rarity="legendary",
        name="Anti-Hoarding Spell",
        image_path=item_asset("insider_trading.png"),
        description="What's that one show? With the hoarders?",
        effect_type="anti_hoarding",
        effect_value=1.0,
    ),
)
