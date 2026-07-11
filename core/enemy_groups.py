from dataclasses import dataclass

from sprites import Archer, Goblin, GoblinSoldier, Goliath, Knight, Orc, Shaman


@dataclass(frozen=True)
class EnemyGroup:
    group_id: str
    incoming_text: str
    boss_type: type
    waves: tuple[dict, dict, dict]

    def __post_init__(self) -> None:
        if len(self.waves) != 3:
            raise ValueError("Every enemy group must define exactly three waves")
        final_types = {
            enemy_type for enemy_type, _ in self.waves[-1]["enemies"]
        }
        if self.boss_type not in final_types:
            raise ValueError("An enemy group's boss must appear in wave three")

    @property
    def enemy_types(self) -> tuple[type, ...]:
        ordered = []
        for wave in self.waves:
            for enemy_type, _ in wave["enemies"]:
                if enemy_type not in ordered:
                    ordered.append(enemy_type)
        return tuple(ordered)


CLASSIC = EnemyGroup(
    group_id="classic",
    incoming_text="You hear an army approaching ...",
    boss_type=Goliath,
    waves=(
        {"enemies": ((Knight, 7),), "modifiers": {}},
        {"enemies": ((Knight, 8), (Archer, 2)), "modifiers": {}},
        {"enemies": ((Knight, 10), (Archer, 5), (Goliath, 1)), "modifiers": {}},
    ),
)

GREEN_GUYS = EnemyGroup(
    group_id="green_guys",
    incoming_text="You smell something coming closer ...",
    boss_type=Orc,
    waves=(
        {"enemies": ((Goblin, 5), (GoblinSoldier, 3)), "modifiers": {}},
        {"enemies": ((Goblin, 8), (GoblinSoldier, 5), (Shaman, 1)), "modifiers": {}},
        {"enemies": ((Goblin, 8), (GoblinSoldier, 7), (Shaman, 2), (Orc, 1)), "modifiers": {}},
    ),
)


# Register future three-wave enemy sets here. Night one always uses Classic;
# later nights randomly select from every registered group.
ENEMY_GROUPS = {
    CLASSIC.group_id: CLASSIC,
    GREEN_GUYS.group_id: GREEN_GUYS,
}


def get_enemy_group(group_id: str | None) -> EnemyGroup:
    return ENEMY_GROUPS.get(group_id, CLASSIC)
