import random

from core.settings import ITEM_RARITIES
from .blessing import BLESSING_CATALOG, Blessing
from .gear import GEAR_CATALOG, Gear
from .item import Item
from .upgrade import UPGRADE_CATALOG, TowerUpgrade


RARITY_ORDER = tuple(ITEM_RARITIES)


def random_rarity() -> str:
    weights = tuple(ITEM_RARITIES[name]["weight"] for name in RARITY_ORDER)
    return random.choices(RARITY_ORDER, weights=weights, k=1)[0]


def rollover_order(rarity: str) -> tuple[str, ...]:
    start = RARITY_ORDER.index(rarity)
    return RARITY_ORDER[start:] + tuple(reversed(RARITY_ORDER[:start]))


def clone_item(template: Item, price: int | None) -> Item:
    common = {
        "item_id": template.item_id,
        "rarity": template.rarity,
        "name": template.name,
        "description": template.description,
        "image_path": template.image_path,
        "price": price,
    }
    if isinstance(template, Gear):
        return Gear(
            **common,
            gear_type=template.gear_type,
            effects=template.effects,
        )
    if isinstance(template, TowerUpgrade):
        return TowerUpgrade(
            **common,
            weight=template.weight,
            effects=template.effects,
        )
    if isinstance(template, Blessing):
        return Blessing(
            **common,
            effect_type=template.effect_type,
            effect_value=template.effect_value,
        )
    raise TypeError(f"Unsupported item template: {type(template).__name__}")


def random_item(
    item_type: str,
    price: int | None = None,
    excluded_names: set[str] | None = None,
) -> Item | None:
    catalogs = {
        "gear": GEAR_CATALOG,
        "upgrade": UPGRADE_CATALOG,
        "blessing": BLESSING_CATALOG,
        "enchant": BLESSING_CATALOG,
    }
    if item_type not in catalogs:
        raise ValueError(f"Unknown item type: {item_type}")

    excluded = {name.casefold() for name in (excluded_names or set())}
    catalog = [
        item
        for item in catalogs[item_type]
        if item.name.casefold() not in excluded
    ]
    rolled_rarity = random_rarity()
    for rarity in rollover_order(rolled_rarity):
        candidates = [item for item in catalog if item.rarity == rarity]
        if candidates:
            return clone_item(random.choice(candidates), price)
    return None


def random_collector_item(
    item_type: str,
    excluded_names: set[str] | None = None,
) -> Item | None:
    """Roll a five-gold pack: 30% uncommon, 60% rare, 10% legendary."""
    catalogs = {
        "gear": GEAR_CATALOG,
        "upgrade": UPGRADE_CATALOG,
        "blessing": BLESSING_CATALOG,
        "enchant": BLESSING_CATALOG,
    }
    if item_type not in catalogs:
        raise ValueError(f"Unknown item type: {item_type}")
    excluded = {name.casefold() for name in (excluded_names or set())}
    catalog = [
        item for item in catalogs[item_type]
        if item.name.casefold() not in excluded
    ]
    rolled = random.choices(
        ("uncommon", "rare", "legendary"),
        weights=(30, 60, 10),
        k=1,
    )[0]
    orders = {
        "uncommon": ("uncommon", "rare", "legendary", "common"),
        "rare": ("rare", "legendary", "uncommon", "common"),
        "legendary": ("legendary", "rare", "uncommon", "common"),
    }
    for rarity in orders[rolled]:
        candidates = [item for item in catalog if item.rarity == rarity]
        if candidates:
            return clone_item(random.choice(candidates), 5)
    return None
