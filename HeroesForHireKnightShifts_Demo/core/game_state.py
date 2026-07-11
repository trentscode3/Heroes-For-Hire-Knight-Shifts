from dataclasses import dataclass, field
import random
from typing import ClassVar

from items import (
    BLESSING_CATALOG,
    GEAR_CATALOG,
    UPGRADE_CATALOG,
    Blessing,
    Gear,
    Item,
    TowerUpgrade,
)
from items.factory import clone_item
from core.settings import (
    BLESSING_SLOT_COUNT,
    DAY_BASE_GOLD,
    TOWER_UPGRADE_WEIGHT_CAP,
    TOWER_BASE_DEFENSE,
    PLAYER_CRIT_MULTIPLIER,
    TOWER_MAX_HEALTH,
)
from core.user_preferences import preferences
from core.units import meters_label


@dataclass
class GameState:
    """Persistent state shared by the day and night scenes."""

    gold: int = 0
    pending_level_gold: int = 0
    day_active: bool = False
    day_elapsed: float = 0.0
    inventory: list[Item] = field(default_factory=list)
    equipped_gear: dict[str, Gear] = field(default_factory=dict)
    equipped_reinforcement_gear: dict[str, Gear] = field(default_factory=dict)
    equipped_upgrades: list[TowerUpgrade] = field(default_factory=list)
    blessings: list[Blessing | None] = field(
        default_factory=lambda: [None] * BLESSING_SLOT_COUNT
    )
    tower_upgrade_weight_cap: int = TOWER_UPGRADE_WEIGHT_CAP
    hero_id: str = "warrior"
    night_count: int = 0
    current_enemy_group_id: str | None = None
    night_player_start_pos: tuple[float, float] | None = None
    night_player_return_pos: tuple[float, float] | None = None
    tower_health: float = TOWER_MAX_HEALTH
    enemy_stat_upgrades: dict[str, dict[str, dict[str, int]]] = field(
        default_factory=dict
    )
    hero_promotions: dict[str, str] = field(
        default_factory=lambda: {
            "warrior": "employee",
            "robin_hood": "training",
            "nimbus": "training",
        }
    )
    quest_progress: dict[str, int] = field(
        default_factory=lambda: {
            "archers_defeated": 0,
            "shamans_defeated": 0,
            "warrior_nights_survived": 0,
            "robin_long_range_kills": 0,
            "nimbus_shamans_defeated": 0,
            "warrior_right_click_kills": 0,
            "robin_nights_survived": 0,
            "nimbus_epic_blessings": 0,
            "warrior_boss_kills": 0,
            "robin_collateral_kills": 0,
            "nimbus_nights_survived": 0,
        }
    )
    lifetime_stats: dict[str, int] = field(
        default_factory=lambda: {
            "games_played": 0,
            "knights_killed": 0,
            "archers_killed": 0,
            "orcs_killed": 0,
            "goliaths_killed": 0,
            "shamans_killed": 0,
            "longest_employment": 0,
            "total_nights_survived": 0,
        }
    )
    run_active: bool = False
    resume_scene: str = "day"
    night_snapshot: dict = field(default_factory=dict)
    inventory_sort: str = "name"
    day_shop_offers: dict[str, dict] = field(default_factory=dict)
    day_shop_sold: list[str] = field(default_factory=list)
    locked_shop_offers: dict[str, dict] = field(default_factory=dict)
    knowledge_points: dict[str, int] = field(
        default_factory=lambda: {"warrior": 0, "robin_hood": 0, "nimbus": 0}
    )
    knowledge_skills: dict[str, list[str]] = field(
        default_factory=lambda: {"warrior": [], "robin_hood": [], "nimbus": []}
    )

    RARITY_RANK: ClassVar[dict[str, int]] = {
        "common": 0,
        "uncommon": 1,
        "rare": 2,
        "legendary": 3,
    }
    LEGACY_ITEM_IDS: ClassVar[dict[str, str]] = {
        "moccasins": "machasins",
        "baddie_grabbers": "sticky_fingers",
        "baddie grabbers": "sticky_fingers",
        "speed_launcher": "lager_launcher",
        "speed launcher": "lager_launcher",
    }
    KNOWLEDGE_SKILL_COSTS: ClassVar[dict[str, int]] = {
        "conditioning": 1,
        "new_sword": 1,
        "slash_and_dash": 1,
        "whistle": 1,
        "sword_spin": 1,
        "kinetic_conversion": 1,
        "well_equipped_soldiers": 1,
        "heavier_sword": 1,
        "energy_core": 1,
        "elite_soldiers": 1,
    }

    def start_new_run(self, hero_id: str = "warrior") -> None:
        self.gold = 0
        self.pending_level_gold = 0
        self.day_active = False
        self.day_elapsed = 0.0
        self.inventory.clear()
        self.equipped_gear.clear()
        self.equipped_reinforcement_gear.clear()
        self.equipped_upgrades.clear()
        self.blessings = [None] * BLESSING_SLOT_COUNT
        self.hero_id = hero_id
        self.night_count = 0
        self.current_enemy_group_id = None
        self.night_player_start_pos = None
        self.night_player_return_pos = None
        self.tower_health = TOWER_MAX_HEALTH
        self.enemy_stat_upgrades.clear()
        self.day_shop_offers.clear()
        self.day_shop_sold.clear()
        self.locked_shop_offers.clear()
        self.knowledge_points = {
            "warrior": 0,
            "robin_hood": 0,
            "nimbus": 0,
        }
        self.knowledge_skills = {
            "warrior": [],
            "robin_hood": [],
            "nimbus": [],
        }
        self.run_active = True
        self.resume_scene = "day"
        self.night_snapshot.clear()
        self.quest_progress["warrior_nights_survived"] = 0
        self.quest_progress["robin_nights_survived"] = 0
        self.quest_progress["nimbus_nights_survived"] = 0
        self.lifetime_stats["games_played"] += 1

    def populate_debug_inventory(self) -> int:
        """Add one of every catalogued item without duplicating existing items."""
        existing = {
            (item.item_type, item.item_id, item.rarity)
            for item in self.inventory
        }
        added = 0
        for item in (*GEAR_CATALOG, *UPGRADE_CATALOG, *BLESSING_CATALOG):
            key = (item.item_type, item.item_id, item.rarity)
            if key in existing:
                continue
            self.receive_item(item)
            existing.add(key)
            added += 1
        return added

    def start_day(self) -> int:
        """Award this day's income once, even if the scene is reopened."""
        if self.day_active:
            return 0
        award = DAY_BASE_GOLD + self.pending_level_gold
        self.gold += award
        self.pending_level_gold = 0
        self.day_active = True
        return award

    def begin_night(self) -> None:
        self.day_active = False
        self.day_elapsed = 0.0
        self.day_shop_offers.clear()
        self.day_shop_sold.clear()
        from core.enemy_groups import ENEMY_GROUPS

        self.night_count += 1
        group_ids = tuple(ENEMY_GROUPS)
        self.current_enemy_group_id = (
            "classic"
            if self.night_count == 1
            else random.choice(group_ids)
        )

    def improve_previous_enemy_group(self) -> None:
        """Permanently improve one random stat per prior enemy type."""
        if self.current_enemy_group_id is None:
            return
        from core.enemy_groups import get_enemy_group

        group = get_enemy_group(self.current_enemy_group_id)
        group_upgrades = self.enemy_stat_upgrades.setdefault(group.group_id, {})
        for enemy_type in group.enemy_types:
            enemy_upgrades = group_upgrades.setdefault(enemy_type.__name__, {})
            stat = random.choice(("health", "damage", "attack_speed", "speed"))
            enemy_upgrades[stat] = enemy_upgrades.get(stat, 0) + 1

    def enemy_upgrades_for(self, enemy_type: type) -> dict[str, int]:
        if self.current_enemy_group_id is None:
            return {}
        return self.enemy_stat_upgrades.get(
            self.current_enemy_group_id, {}
        ).get(enemy_type.__name__, {})

    def finish_night(self, levels_gained: int) -> None:
        self.night_snapshot.clear()
        self.record_night_survived()
        self.pending_level_gold = max(0, levels_gained)
        if self.hero_id == "warrior":
            survived = min(
                2,
                self.quest_progress.get("warrior_nights_survived", 0) + 1,
            )
            self.quest_progress["warrior_nights_survived"] = survived
            if survived >= 2 and not self.has_promotion("warrior", "shift_lead"):
                self.advance_promotion("warrior", "shift_lead")
        elif self.hero_id == "robin_hood":
            survived = min(
                3,
                self.quest_progress.get("robin_nights_survived", 0) + 1,
            )
            self.quest_progress["robin_nights_survived"] = survived
            if survived >= 3:
                self.advance_promotion("robin_hood", "assistant_manager")
        elif self.hero_id == "nimbus":
            survived = min(
                4,
                self.quest_progress.get("nimbus_nights_survived", 0) + 1,
            )
            self.quest_progress["nimbus_nights_survived"] = survived
            if survived >= 4:
                self.advance_promotion("nimbus", "manager")

    def buy(self, items: list[Item]) -> bool:
        total = sum(item.price for item in items)
        if total > self.gold:
            return False
        self.gold -= total
        self.receive_items(items)
        return True

    def receive_item(self, item: Item) -> bool:
        """Store an item and optionally equip it according to user preferences."""
        self.inventory.append(item)
        if isinstance(item, Blessing):
            if self.hero_id == "nimbus" and item.rarity in ("rare", "legendary"):
                progress = min(
                    3,
                    self.quest_progress.get("nimbus_epic_blessings", 0) + 1,
                )
                self.quest_progress["nimbus_epic_blessings"] = progress
                if progress >= 3:
                    self.advance_promotion("nimbus", "assistant_manager")
        if not preferences.auto_equip_enabled:
            return False
        if isinstance(item, Gear):
            equipped = self.equipped_gear.get(item.gear_type)
            if equipped is not None and self.rarity_rank(item) <= self.rarity_rank(equipped):
                return False
            return self.equip_gear(item)
        if isinstance(item, TowerUpgrade):
            if self.equip_upgrade(item):
                return True
            lower = sorted(
                (
                    upgrade for upgrade in self.equipped_upgrades
                    if self.rarity_rank(upgrade) < self.rarity_rank(item)
                ),
                key=self.rarity_rank,
            )
            removed: list[TowerUpgrade] = []
            for upgrade in lower:
                self.equipped_upgrades.remove(upgrade)
                removed.append(upgrade)
                if self.equip_upgrade(item):
                    return True
            self.equipped_upgrades.extend(removed)
            return False
        if isinstance(item, Blessing):
            return self.equip_blessing(item)
        return False

    def receive_items(self, items: list[Item]) -> list[Item]:
        equipped = []
        for item in items:
            if self.receive_item(item):
                equipped.append(item)
        return equipped

    def clear_items_after_death(self) -> None:
        self.inventory.clear()
        self.equipped_gear.clear()
        self.equipped_reinforcement_gear.clear()
        self.equipped_upgrades.clear()
        self.blessings = [None] * BLESSING_SLOT_COUNT
        self.gold = 0
        self.pending_level_gold = 0
        self.day_active = False
        self.day_elapsed = 0.0
        self.night_count = 0
        self.current_enemy_group_id = None
        self.enemy_stat_upgrades.clear()
        self.day_shop_offers.clear()
        self.day_shop_sold.clear()
        self.locked_shop_offers.clear()
        self.run_active = False
        self.resume_scene = "day"
        self.night_snapshot.clear()
        self.quest_progress["warrior_nights_survived"] = 0
        self.quest_progress["robin_nights_survived"] = 0
        self.quest_progress["nimbus_nights_survived"] = 0

    def record_night_survived(self) -> None:
        self.lifetime_stats["total_nights_survived"] = (
            self.lifetime_stats.get("total_nights_survived", 0) + 1
        )
        self.record_employment_end(self.night_count)

    def record_employment_end(self, nights_lasted: int) -> None:
        self.lifetime_stats["longest_employment"] = max(
            self.lifetime_stats.get("longest_employment", 0),
            max(0, int(nights_lasted)),
        )

    def hero_unlocked(self, hero_id: str) -> bool:
        return self.has_promotion(hero_id, "employee")

    def quest_text(self, hero_id: str) -> str:
        tier = self.hero_promotions.get(hero_id, "training")
        if hero_id == "warrior":
            if tier == "employee":
                value = self.quest_progress.get("warrior_nights_survived", 0)
                return f"Survived {value} / 2 Nights as Warrior"
            if tier == "shift_lead":
                value = self.quest_progress.get("warrior_right_click_kills", 0)
                return f"Right-click kills: {value} / 30"
            if tier == "assistant_manager":
                value = self.quest_progress.get("warrior_boss_kills", 0)
                return f"Bosses defeated: {value} / 100"
            return "Manager promotion achieved"
        if hero_id == "robin_hood":
            if tier == "training":
                return f"Defeated {self.quest_progress['archers_defeated']} / 10 Archers"
            if tier == "employee":
                value = self.quest_progress.get("robin_long_range_kills", 0)
                return f"Kills from {meters_label(300)}+: {value} / 5"
            if tier == "shift_lead":
                value = self.quest_progress.get("robin_nights_survived", 0)
                return f"Survived {value} / 3 Nights as Robin Hood"
            if tier == "assistant_manager":
                value = self.quest_progress.get("robin_collateral_kills", 0)
                return f"Collateral kills: {value} / 20"
            return "Manager promotion achieved"
        if hero_id == "nimbus":
            if tier == "training":
                return f"Defeated {self.quest_progress['shamans_defeated']} / 10 Shamans"
            if tier == "employee":
                value = self.quest_progress.get("nimbus_shamans_defeated", 0)
                return f"Shamans defeated as Nimbus: {value} / 10"
            if tier == "shift_lead":
                value = self.quest_progress.get("nimbus_epic_blessings", 0)
                return f"Lifetime Epic Blessings: {value} / 3"
            if tier == "assistant_manager":
                value = self.quest_progress.get("nimbus_nights_survived", 0)
                return f"Survived {value} / 4 Nights as Nimbus"
            return "Manager promotion achieved"
        return "Training complete"

    def has_promotion(self, hero_id: str, tier: str) -> bool:
        tiers = (
            "training",
            "employee",
            "shift_lead",
            "assistant_manager",
            "manager",
        )
        owned = self.hero_promotions.get(hero_id, "training")
        return owned in tiers and tiers.index(owned) >= tiers.index(tier)

    def advance_promotion(self, hero_id: str, tier: str) -> bool:
        tiers = (
            "training",
            "employee",
            "shift_lead",
            "assistant_manager",
            "manager",
        )
        current = self.hero_promotions.get(hero_id, "training")
        current_index = tiers.index(current)
        target_index = tiers.index(tier)
        if target_index != current_index + 1:
            return False
        self.hero_promotions[hero_id] = tier
        if hero_id == "warrior" and tier == "shift_lead":
            if self.quest_progress.get("warrior_right_click_kills", 0) >= 30:
                self.advance_promotion("warrior", "assistant_manager")
        elif hero_id == "warrior" and tier == "assistant_manager":
            if self.quest_progress.get("warrior_boss_kills", 0) >= 100:
                self.advance_promotion("warrior", "manager")
        elif hero_id == "robin_hood" and tier == "shift_lead":
            if self.quest_progress.get("robin_nights_survived", 0) >= 3:
                self.advance_promotion("robin_hood", "assistant_manager")
        elif hero_id == "robin_hood" and tier == "assistant_manager":
            if self.quest_progress.get("robin_collateral_kills", 0) >= 20:
                self.advance_promotion("robin_hood", "manager")
        elif hero_id == "nimbus" and tier == "shift_lead":
            if self.quest_progress.get("nimbus_epic_blessings", 0) >= 3:
                self.advance_promotion("nimbus", "assistant_manager")
        elif hero_id == "nimbus" and tier == "assistant_manager":
            if self.quest_progress.get("nimbus_nights_survived", 0) >= 4:
                self.advance_promotion("nimbus", "manager")
        return True

    def record_enemy_defeat(self, enemy) -> None:
        enemy_name = type(enemy).__name__
        stat_keys = {
            "Knight": "knights_killed",
            "Archer": "archers_killed",
            "Orc": "orcs_killed",
            "Goliath": "goliaths_killed",
            "Shaman": "shamans_killed",
        }
        stat_key = stat_keys.get(enemy_name)
        if stat_key is not None:
            self.lifetime_stats[stat_key] += 1
        if (
            self.hero_id == "warrior"
            and getattr(enemy, "IS_BOSS", False)
        ):
            value = min(
                100,
                self.quest_progress.get("warrior_boss_kills", 0) + 1,
            )
            self.quest_progress["warrior_boss_kills"] = value
            if value >= 100:
                self.advance_promotion("warrior", "manager")
        if enemy_name == "Archer":
            key = "archers_defeated"
            hero_id = "robin_hood"
        elif enemy_name == "Shaman":
            key = "shamans_defeated"
            hero_id = "nimbus"
            if self.hero_id == "nimbus" and self.has_promotion("nimbus", "employee"):
                value = min(
                    10,
                    self.quest_progress.get("nimbus_shamans_defeated", 0) + 1,
                )
                self.quest_progress["nimbus_shamans_defeated"] = value
                if value >= 10:
                    self.advance_promotion("nimbus", "shift_lead")
        else:
            return
        self.quest_progress[key] = min(10, self.quest_progress[key] + 1)
        if (
            self.quest_progress[key] >= 10
            and not self.has_promotion(hero_id, "employee")
        ):
            self.advance_promotion(hero_id, "employee")

    def record_right_click_kill(self, count: int = 1) -> None:
        if self.hero_id != "warrior":
            return
        value = min(
            30,
            self.quest_progress.get("warrior_right_click_kills", 0) + count,
        )
        self.quest_progress["warrior_right_click_kills"] = value
        if value >= 30:
            self.advance_promotion("warrior", "assistant_manager")

    def record_robin_long_range_kill(self, count: int = 1) -> None:
        if self.hero_id != "robin_hood":
            return
        value = min(
            5,
            self.quest_progress.get("robin_long_range_kills", 0) + count,
        )
        self.quest_progress["robin_long_range_kills"] = value
        if value >= 5:
            self.advance_promotion("robin_hood", "shift_lead")

    def record_robin_collateral_kill(self, count: int = 1) -> None:
        if self.hero_id != "robin_hood":
            return
        value = min(
            20,
            self.quest_progress.get("robin_collateral_kills", 0) + count,
        )
        self.quest_progress["robin_collateral_kills"] = value
        if value >= 20:
            self.advance_promotion("robin_hood", "manager")

    def to_save_data(self) -> dict:
        inventory = [
            {
                "item_type": item.item_type,
                "item_id": item.item_id,
                "name": item.name,
                "rarity": item.rarity,
                "price": item.price,
            }
            for item in self.inventory
        ]
        item_indices = {id(item): index for index, item in enumerate(self.inventory)}
        return {
            "gold": self.gold,
            "pending_level_gold": self.pending_level_gold,
            "day_active": self.day_active,
            "day_elapsed": self.day_elapsed,
            "inventory": inventory,
            "equipped_gear": {
                gear_type: item_indices[id(item)]
                for gear_type, item in self.equipped_gear.items()
                if id(item) in item_indices
            },
            "equipped_reinforcement_gear": {
                gear_type: item_indices[id(item)]
                for gear_type, item in self.equipped_reinforcement_gear.items()
                if id(item) in item_indices
            },
            "equipped_upgrades": [
                item_indices[id(item)]
                for item in self.equipped_upgrades
                if id(item) in item_indices
            ],
            "blessings": [
                item_indices.get(id(item)) if item is not None else None
                for item in self.blessings
            ],
            "tower_upgrade_weight_cap": self.tower_upgrade_weight_cap,
            "hero_id": self.hero_id,
            "night_count": self.night_count,
            "current_enemy_group_id": self.current_enemy_group_id,
            "tower_health": self.tower_health,
            "enemy_stat_upgrades": self.enemy_stat_upgrades,
            "hero_promotions": self.hero_promotions,
            "quest_progress": self.quest_progress,
            "lifetime_stats": self.lifetime_stats,
            "run_active": self.run_active,
            "resume_scene": self.resume_scene,
            "night_snapshot": self.night_snapshot,
            "inventory_sort": self.inventory_sort,
            "day_shop_offers": self.day_shop_offers,
            "day_shop_sold": self.day_shop_sold,
            "locked_shop_offers": self.locked_shop_offers,
            "knowledge_points": self.knowledge_points,
            "knowledge_skills": self.knowledge_skills,
        }

    @classmethod
    def from_save_data(cls, data: dict) -> "GameState":
        state = cls()
        for field_name in (
            "gold",
            "pending_level_gold",
            "day_active",
            "day_elapsed",
            "tower_upgrade_weight_cap",
            "hero_id",
            "night_count",
            "current_enemy_group_id",
            "tower_health",
            "enemy_stat_upgrades",
            "run_active",
            "resume_scene",
            "night_snapshot",
            "inventory_sort",
            "day_shop_offers",
            "day_shop_sold",
            "locked_shop_offers",
            "knowledge_points",
            "knowledge_skills",
        ):
            if field_name in data:
                setattr(state, field_name, data[field_name])

        legacy_tiers = {
            None: "training",
            "bronze": "employee",
            "silver": "shift_lead",
            "gold": "assistant_manager",
            "diamond": "manager",
        }
        saved_promotions = data.get("hero_promotions")
        if not isinstance(saved_promotions, dict):
            saved_promotions = {
                hero_id: legacy_tiers.get(tier, "training")
                for hero_id, tier in data.get("hero_trophies", {}).items()
            }
        valid_promotions = {
            "training",
            "employee",
            "shift_lead",
            "assistant_manager",
            "manager",
        }
        state.hero_promotions.update(
            {
                hero_id: mapped
                for hero_id, tier in saved_promotions.items()
                if (mapped := legacy_tiers.get(tier, tier)) in valid_promotions
            }
        )
        saved_quests = data.get("quest_progress", {})
        state.quest_progress.update(saved_quests)
        if (
            "nimbus_shamans_defeated" not in saved_quests
            and "nimbus_silver_shamans" in saved_quests
        ):
            state.quest_progress["nimbus_shamans_defeated"] = saved_quests[
                "nimbus_silver_shamans"
            ]
        state.quest_progress.pop("nimbus_silver_shamans", None)
        state.lifetime_stats.update(data.get("lifetime_stats", {}))
        try:
            state.day_elapsed = max(0.0, float(state.day_elapsed))
        except (TypeError, ValueError):
            state.day_elapsed = 0.0
        if not isinstance(state.night_snapshot, dict):
            state.night_snapshot = {}
        legacy_knowledge = {
            "better_sword": "new_sword",
            "sword_slash": "slash_and_dash",
            "sword_throw": "slash_and_dash",
        }
        state.knowledge_skills = {
            hero_id: list(dict.fromkeys(
                legacy_knowledge.get(skill_id, skill_id)
                for skill_id in skills
            ))
            for hero_id, skills in state.knowledge_skills.items()
        }

        catalog = (*GEAR_CATALOG, *UPGRADE_CATALOG, *BLESSING_CATALOG)
        templates_by_name = {
            (item.item_type, item.name.casefold(), item.rarity): item
            for item in catalog
        }
        templates_by_id = {
            (item.item_type, item.item_id, item.rarity): item
            for item in catalog
        }
        templates_by_base_id = {
            (item.item_type, item.item_id): item
            for item in catalog
        }
        loaded_by_index: dict[int, Item] = {}
        for index, item_data in enumerate(data.get("inventory", [])):
            saved_id = str(item_data.get("item_id", ""))
            saved_name = str(item_data.get("name", "")).casefold()
            canonical_id = cls.LEGACY_ITEM_IDS.get(saved_id or saved_name, saved_id)
            id_key = (
                item_data.get("item_type"),
                canonical_id,
                item_data.get("rarity"),
            )
            name_key = (
                item_data.get("item_type"),
                saved_name,
                item_data.get("rarity"),
            )
            template = (
                templates_by_id.get(id_key)
                or templates_by_name.get(name_key)
                or templates_by_base_id.get(
                    (item_data.get("item_type"), canonical_id)
                )
            )
            if template is None:
                continue
            item = clone_item(template, item_data.get("price"))
            state.inventory.append(item)
            loaded_by_index[index] = item

        state.equipped_gear = {
            gear_type: item
            for gear_type, index in data.get("equipped_gear", {}).items()
            if isinstance((item := loaded_by_index.get(index)), Gear)
        }
        state.equipped_reinforcement_gear = {
            gear_type: item
            for gear_type, index in data.get(
                "equipped_reinforcement_gear", {}
            ).items()
            if isinstance((item := loaded_by_index.get(index)), Gear)
        }
        state.equipped_upgrades = [
            item
            for index in data.get("equipped_upgrades", [])
            if isinstance((item := loaded_by_index.get(index)), TowerUpgrade)
        ]
        state.blessings = [None] * BLESSING_SLOT_COUNT
        for slot, index in enumerate(data.get("blessings", [])[:BLESSING_SLOT_COUNT]):
            item = loaded_by_index.get(index) if index is not None else None
            if isinstance(item, Blessing):
                state.blessings[slot] = item
        return state

    def hero_knowledge_points(self, hero_id: str | None = None) -> int:
        return self.knowledge_points.get(hero_id or self.hero_id, 0)

    def hero_knowledge_skills(self, hero_id: str | None = None) -> set[str]:
        return set(self.knowledge_skills.get(hero_id or self.hero_id, []))

    def add_knowledge_points(self, amount: int, hero_id: str | None = None) -> None:
        if amount <= 0:
            return
        hero_id = hero_id or self.hero_id
        self.knowledge_points[hero_id] = (
            self.knowledge_points.get(hero_id, 0) + amount
        )

    @classmethod
    def knowledge_cost(cls, skill_id: str) -> int:
        return cls.KNOWLEDGE_SKILL_COSTS.get(skill_id, 0)

    def unlock_knowledge(self, skill_id: str) -> tuple[bool, str]:
        hero_id = self.hero_id
        if hero_id != "warrior":
            return False, "This hero's Knowledge Tree is not available yet"
        unlocked = self.hero_knowledge_skills(hero_id)
        if skill_id in unlocked:
            return False, "Knowledge already learned"
        prerequisites = {
            "conditioning": set(),
            "new_sword": {"conditioning"},
            "slash_and_dash": {"conditioning", "new_sword"},
            "whistle": {"conditioning", "new_sword"},
            "sword_spin": {"slash_and_dash"},
            "kinetic_conversion": set(),
            "well_equipped_soldiers": {"whistle"},
            "heavier_sword": {"sword_spin"},
            "energy_core": {"kinetic_conversion"},
            "elite_soldiers": {"well_equipped_soldiers"},
        }
        if skill_id not in prerequisites:
            return False, "Unknown knowledge"
        if not prerequisites[skill_id].issubset(unlocked):
            return False, "Learn the earlier knowledge first"
        if skill_id == "kinetic_conversion" and not (
            {"slash_and_dash", "whistle"} & unlocked
        ):
            return False, "Choose a tier-three branch first"
        if skill_id in ("slash_and_dash", "whistle"):
            if not self.has_promotion("warrior", "shift_lead"):
                return False, "Requires the Warrior Shift Lead promotion"
            other_branch = "whistle" if skill_id == "slash_and_dash" else "slash_and_dash"
            branch_finished = (
                "heavier_sword" in unlocked
                if other_branch == "slash_and_dash"
                else "elite_soldiers" in unlocked
            )
            if other_branch in unlocked and not branch_finished:
                return False, "Finish the current branch before learning this one"
        cost = self.knowledge_cost(skill_id)
        if self.hero_knowledge_points(hero_id) < cost:
            return False, "Not enough Knowledge"
        self.knowledge_points[hero_id] -= cost
        self.knowledge_skills.setdefault(hero_id, []).append(skill_id)
        return True, "Knowledge learned"

    def apply_player_knowledge(self, player) -> None:
        player.new_sword_unlocked = False
        player.conditioning_unlocked = False
        player.warrior_branch = None
        player.sword_spin_unlocked = False
        player.kinetic_conversion_unlocked = False
        player.well_equipped_soldiers_unlocked = False
        player.heavier_sword_unlocked = False
        skills = self.hero_knowledge_skills(player.HERO_ID)
        player.conditioning_unlocked = "conditioning" in skills
        player.new_sword_unlocked = "new_sword" in skills
        if "slash_and_dash" in skills:
            player.warrior_branch = "slash_and_dash"
        elif "whistle" in skills:
            player.warrior_branch = "whistle"
        player.sword_spin_unlocked = "sword_spin" in skills
        player.kinetic_conversion_unlocked = "kinetic_conversion" in skills
        player.well_equipped_soldiers_unlocked = "well_equipped_soldiers" in skills
        player.heavier_sword_unlocked = "heavier_sword" in skills
        player.energy_core_unlocked = "energy_core" in skills
        player.elite_soldiers_unlocked = "elite_soldiers" in skills
        player.refresh_progression_stats()

    @classmethod
    def rarity_rank(cls, item: Item) -> int:
        return cls.RARITY_RANK.get(item.rarity, -1)

    @staticmethod
    def item_to_data(item: Item) -> dict:
        return {
            "item_type": item.item_type,
            "item_id": item.item_id,
            "name": item.name,
            "rarity": item.rarity,
            "price": item.price,
        }

    @staticmethod
    def item_from_data(data: dict | None) -> Item | None:
        if not data:
            return None
        catalog = (*GEAR_CATALOG, *UPGRADE_CATALOG, *BLESSING_CATALOG)
        saved_id = str(data.get("item_id", ""))
        saved_name = str(data.get("name", "")).casefold()
        canonical_id = GameState.LEGACY_ITEM_IDS.get(saved_id or saved_name, saved_id)
        template = next(
            (
                item for item in catalog
                if item.item_type == data.get("item_type")
                and item.rarity == data.get("rarity")
                and (
                    item.item_id == canonical_id
                    or item.name.casefold() == saved_name
                )
            ),
            None,
        )
        return clone_item(template, data.get("price")) if template is not None else None

    @property
    def tower_upgrade_weight(self) -> int:
        return sum(upgrade.weight for upgrade in self.equipped_upgrades)

    @property
    def xp_gain_multiplier(self) -> float:
        return 1.0 + sum(
            blessing.effect_value
            for blessing in self.blessings
            if blessing is not None and blessing.effect_type == "xp_gain"
        )

    @property
    def effective_tower_upgrade_weight_cap(self) -> int:
        bonus = sum(
            int(blessing.effect_value)
            for blessing in self.blessings
            if blessing is not None and blessing.effect_type == "tower_weight"
        )
        return self.tower_upgrade_weight_cap + bonus

    @property
    def anti_hoarding_enabled(self) -> bool:
        return any(
            blessing is not None and blessing.effect_type == "anti_hoarding"
            for blessing in self.blessings
        )

    @property
    def owned_item_names(self) -> set[str]:
        return {item.name for item in self.inventory}

    @property
    def tower_defense(self) -> int:
        defense = TOWER_BASE_DEFENSE + sum(
            int(upgrade.effects.get("defense_bonus", 0))
            for upgrade in self.equipped_upgrades
        )
        return max(0, min(99, defense))

    def auto_equip(self, item: Item) -> bool:
        if isinstance(item, Gear):
            return self.equip_gear(item)
        if isinstance(item, TowerUpgrade):
            return self.equip_upgrade(item)
        if isinstance(item, Blessing):
            return self.equip_blessing(item)
        return False

    def owns(self, item: Item) -> bool:
        return any(owned is item for owned in self.inventory)

    def equip_gear(self, item: Gear) -> bool:
        if not self.owns(item):
            return False
        for gear_type, equipped in list(self.equipped_reinforcement_gear.items()):
            if equipped is item:
                del self.equipped_reinforcement_gear[gear_type]
        self.equipped_gear[item.gear_type] = item
        return True

    def equip_reinforcement_gear(self, item: Gear) -> bool:
        if not self.owns(item):
            return False
        if "well_equipped_soldiers" not in self.hero_knowledge_skills("warrior"):
            return False
        for gear_type, equipped in list(self.equipped_gear.items()):
            if equipped is item:
                del self.equipped_gear[gear_type]
        self.equipped_reinforcement_gear[item.gear_type] = item
        return True

    def equip_upgrade(self, item: TowerUpgrade) -> bool:
        if not self.owns(item):
            return False
        if any(upgrade is item for upgrade in self.equipped_upgrades):
            return True
        if (
            self.tower_upgrade_weight + item.weight
            > self.effective_tower_upgrade_weight_cap
        ):
            return False
        self.equipped_upgrades.append(item)
        return True

    def equip_blessing(
        self,
        item: Blessing,
        slot_index: int | None = None,
    ) -> bool:
        if not self.owns(item):
            return False
        if any(blessing is item for blessing in self.blessings if blessing is not None):
            return True
        same_effect = next(
            (
                index for index, blessing in enumerate(self.blessings)
                if blessing is not None and blessing.effect_type == item.effect_type
            ),
            None,
        )
        if same_effect is not None:
            current = self.blessings[same_effect]
            if current is not None and self.rarity_rank(item) <= self.rarity_rank(current):
                return False
            slot_index = same_effect
        if slot_index is None:
            slot_index = next(
                (index for index, blessing in enumerate(self.blessings) if blessing is None),
                -1,
            )
            if slot_index < 0:
                lowest = min(
                    range(len(self.blessings)),
                    key=lambda index: self.rarity_rank(self.blessings[index]),
                )
                current = self.blessings[lowest]
                if current is not None and self.rarity_rank(item) > self.rarity_rank(current):
                    slot_index = lowest
        if not 0 <= slot_index < BLESSING_SLOT_COUNT:
            return False
        self.blessings[slot_index] = item
        return True

    def unequip(self, item: Item) -> bool:
        if isinstance(item, Gear):
            equipped = self.equipped_gear.get(item.gear_type)
            if equipped is item:
                del self.equipped_gear[item.gear_type]
                return True
            reinforcement = self.equipped_reinforcement_gear.get(item.gear_type)
            if reinforcement is item:
                del self.equipped_reinforcement_gear[item.gear_type]
                return True
        elif isinstance(item, TowerUpgrade):
            for index, equipped in enumerate(self.equipped_upgrades):
                if equipped is item:
                    self.equipped_upgrades.pop(index)
                    return True
        elif isinstance(item, Blessing):
            for index, equipped in enumerate(self.blessings):
                if equipped is item:
                    self.blessings[index] = None
                    return True
        return False

    def apply_player_gear(self, player) -> None:
        player.reset_gear_bases()
        for gear in self.equipped_gear.values():
            gear.apply_to_player(player)
        player.refresh_progression_stats()

    def apply_player_blessings(self, player) -> None:
        player.xp_gain_multiplier = self.xp_gain_multiplier
        player.crit_multiplier = PLAYER_CRIT_MULTIPLIER
        for blessing in self.blessings:
            if blessing is not None and blessing.effect_type == "crit_damage":
                player.crit_multiplier *= blessing.effect_value

    def apply_reinforcement_gear(self, knight) -> None:
        for gear in self.equipped_reinforcement_gear.values():
            effects = gear.effects
            knight.speed *= float(effects.get("move_speed_multiplier", 1.0))
            knight.damage *= 1.0 + float(effects.get("base_damage_bonus", 0.0))
            knight.attack_speed /= float(effects.get("attack_rate_multiplier", 1.0))
            knight.crit_chance += float(effects.get("crit_chance_bonus", 0.0))
            knight.melee_range_multiplier *= float(
                effects.get("attack_area_multiplier", 1.0)
            )
            knight.boss_damage_reduction += float(
                effects.get("boss_damage_reduction", 0.0)
            )
            mobility = effects.get("mobility_ability")
            if isinstance(mobility, str):
                knight.mobility_ability = mobility

    def apply_tower_upgrades(self, tower) -> None:
        tower.defense = TOWER_BASE_DEFENSE
        tower.damage_reflection = 0.0
        tower.lager_launcher_enabled = False
        tower.wooden_stakes_enabled = False
        tower.turret_enabled = False
        tower.archer_enabled = False
        tower.boss_damage_reduction = sum(
            float(gear.effects.get("boss_damage_reduction", 0.0))
            for gear in self.equipped_gear.values()
        )
        for upgrade in self.equipped_upgrades:
            upgrade.apply_to_tower(tower)
        tower.defense = max(0, min(99, tower.defense))
