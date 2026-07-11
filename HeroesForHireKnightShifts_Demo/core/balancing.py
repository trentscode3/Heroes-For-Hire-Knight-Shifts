from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite

from core import settings


@dataclass(frozen=True)
class PlayerBalanceInput:
    games_played: int
    longest_employment: float
    expected_nights: float
    skill: float
    average_employment: float = 0.0
    knights_killed: int = 0
    archers_killed: int = 0
    orcs_killed: int = 0
    goliaths_killed: int = 0
    shamans_killed: int = 0


@dataclass(frozen=True)
class BalanceVariables:
    tower_health: float = settings.TOWER_MAX_HEALTH
    tower_defense: float = settings.TOWER_BASE_DEFENSE
    player_damage: float = settings.PLAYER_ATTACK_DAMAGE
    player_attack_speed: float = settings.PLAYER_ATTACK_SPEED
    player_attack_radius: float = settings.PLAYER_ATTACK_RADIUS
    player_speed: float = settings.PLAYER_SPEED
    friendly_spawn_interval: float = settings.FRIENDLY_KNIGHT_SPAWN_INTERVAL
    night_enemy_stat_bonus: float = settings.NIGHT_ENEMY_STAT_BONUS
    night_enemy_count_bonus: float = settings.NIGHT_ENEMY_COUNT_BONUS


@dataclass(frozen=True)
class BalanceReport:
    predicted_nights: float
    target_nights: float
    estimated_player_skill: float
    playtest_summary: dict[str, float]
    variable_weights: dict[str, float]
    recommended_settings: dict[str, float]
    recommendation_delta: dict[str, float]


BASE_WAVES = (
    (
        {"health": settings.KNIGHT_HEALTH, "damage": settings.KNIGHT_DAMAGE,
         "attack_speed": settings.KNIGHT_ATTACK_SPEED, "count": 7},
        {"health": settings.KNIGHT_HEALTH, "damage": settings.KNIGHT_DAMAGE,
         "attack_speed": settings.KNIGHT_ATTACK_SPEED, "count": 8},
        {"health": settings.ARCHER_HEALTH, "damage": settings.ARCHER_DAMAGE,
         "attack_speed": settings.ARCHER_ATTACK_SPEED, "count": 2},
        {"health": settings.KNIGHT_HEALTH, "damage": settings.KNIGHT_DAMAGE,
         "attack_speed": settings.KNIGHT_ATTACK_SPEED, "count": 10},
        {"health": settings.ARCHER_HEALTH, "damage": settings.ARCHER_DAMAGE,
         "attack_speed": settings.ARCHER_ATTACK_SPEED, "count": 5},
        {"health": settings.GOLIATH_HEALTH, "damage": settings.ORC_DAMAGE,
         "attack_speed": settings.ORC_ATTACK_SPEED, "count": 1},
    ),
    (
        {"health": settings.GOBLIN_HEALTH, "damage": settings.GOBLIN_DAMAGE,
         "attack_speed": settings.GOBLIN_ATTACK_SPEED, "count": 5},
        {"health": settings.GOBLIN_SOLDIER_HEALTH, "damage": settings.GOBLIN_SOLDIER_DAMAGE,
         "attack_speed": settings.GOBLIN_SOLDIER_ATTACK_SPEED, "count": 3},
        {"health": settings.GOBLIN_HEALTH, "damage": settings.GOBLIN_DAMAGE,
         "attack_speed": settings.GOBLIN_ATTACK_SPEED, "count": 8},
        {"health": settings.GOBLIN_SOLDIER_HEALTH, "damage": settings.GOBLIN_SOLDIER_DAMAGE,
         "attack_speed": settings.GOBLIN_SOLDIER_ATTACK_SPEED, "count": 5},
        {"health": settings.SHAMAN_HEALTH, "damage": settings.SHAMAN_DAMAGE,
         "attack_speed": settings.SHAMAN_ATTACK_SPEED, "count": 1},
        {"health": settings.GOBLIN_HEALTH, "damage": settings.GOBLIN_DAMAGE,
         "attack_speed": settings.GOBLIN_ATTACK_SPEED, "count": 8},
        {"health": settings.GOBLIN_SOLDIER_HEALTH, "damage": settings.GOBLIN_SOLDIER_DAMAGE,
         "attack_speed": settings.GOBLIN_SOLDIER_ATTACK_SPEED, "count": 7},
        {"health": settings.SHAMAN_HEALTH, "damage": settings.SHAMAN_DAMAGE,
         "attack_speed": settings.SHAMAN_ATTACK_SPEED, "count": 2},
        {"health": settings.ORC_HEALTH, "damage": settings.ORC_DAMAGE,
         "attack_speed": settings.ORC_ATTACK_SPEED, "count": 1},
    ),
)


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def clean_number(value: float, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if isfinite(parsed) else fallback


def estimate_skill(player: PlayerBalanceInput) -> float:
    declared = clamp(clean_number(player.skill), 0.0, 1.0)
    if player.games_played <= 0:
        return declared
    expected = max(1.0, player.expected_nights)
    experience = clamp(player.games_played / 40, 0.0, 1.0)
    performance = clamp(player.longest_employment / expected, 0.0, 1.35) / 1.35
    average = clamp(player.average_employment / expected, 0.0, 1.0)
    inferred = 0.65 * performance + 0.20 * average + 0.15 * experience
    return clamp(declared * 0.65 + inferred * 0.35, 0.0, 1.0)


def player_power(variables: BalanceVariables, skill: float) -> float:
    attack_rate = 1 / max(0.05, variables.player_attack_speed)
    area = (variables.player_attack_radius / settings.PLAYER_ATTACK_RADIUS) ** 0.55
    mobility = (variables.player_speed / settings.PLAYER_SPEED) ** 0.25
    friendly_rate = 1 / max(1.0, variables.friendly_spawn_interval)
    friendly_power = (
        settings.KNIGHT_DAMAGE
        / settings.KNIGHT_ATTACK_SPEED
        * friendly_rate
        * 5.6
    )
    skill_bonus = 0.55 + skill * 1.75
    return (
        variables.player_damage * attack_rate * area * mobility * skill_bonus
        + friendly_power
    )


def enemy_pressure_for_night(night: int, variables: BalanceVariables) -> float:
    stat_scale = (1 + variables.night_enemy_stat_bonus) ** max(0, night - 1)
    count_scale = (1 + variables.night_enemy_count_bonus) ** max(0, night - 1)
    groups = BASE_WAVES[:1] if night == 1 else BASE_WAVES
    total = 0.0
    for group in groups:
        group_pressure = 0.0
        for enemy in group:
            health = enemy["health"] * stat_scale
            damage = enemy["damage"] * stat_scale
            attack_speed = max(0.1, enemy["attack_speed"])
            count = enemy["count"] * count_scale
            group_pressure += count * (health / 12) ** 0.45 * damage / attack_speed
        total += group_pressure
    return total / len(groups)


def survival_budget(variables: BalanceVariables, skill: float) -> float:
    tower = variables.tower_health * (1 + variables.tower_defense / 100)
    return tower * 0.16 + player_power(variables, skill) * 8.5


def predict_survival_nights(
    variables: BalanceVariables,
    skill: float,
    max_nights: int = 30,
) -> float:
    budget = survival_budget(variables, skill)
    for night in range(1, max_nights + 1):
        pressure = enemy_pressure_for_night(night, variables)
        ratio = budget / max(0.001, pressure)
        if ratio < 1:
            return max(0.0, night - 1 + ratio)
        budget *= 1.025 + skill * 0.035
    return float(max_nights)


def variable_sensitivity(
    variables: BalanceVariables,
    skill: float,
) -> dict[str, float]:
    baseline = predict_survival_nights(variables, skill)
    raw: dict[str, float] = {}
    for name, value in asdict(variables).items():
        value = float(value)
        if value == 0:
            continue
        changed = variables_with(variables, **{name: value * 1.10})
        delta = predict_survival_nights(changed, skill) - baseline
        raw[name] = delta
    total = sum(abs(value) for value in raw.values()) or 1.0
    return {
        name: round(value / total, 4)
        for name, value in sorted(
            raw.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )
    }


def run_playtest_batch(
    variables: BalanceVariables,
    skill: float,
    samples: int = 41,
) -> dict[str, float]:
    samples = max(5, int(samples))
    spread = 0.22
    results = []
    for index in range(samples):
        t = index / max(1, samples - 1)
        offset = (t - 0.5) * 2 * spread
        sampled_skill = clamp(skill + offset, 0.0, 1.0)
        results.append(predict_survival_nights(variables, sampled_skill))
    results.sort()

    def percentile(amount: float) -> float:
        position = amount * (len(results) - 1)
        lower = int(position)
        upper = min(len(results) - 1, lower + 1)
        fraction = position - lower
        return results[lower] * (1 - fraction) + results[upper] * fraction

    return {
        "min": round(results[0], 2),
        "p10": round(percentile(0.10), 2),
        "median": round(percentile(0.50), 2),
        "p90": round(percentile(0.90), 2),
        "max": round(results[-1], 2),
        "mean": round(sum(results) / len(results), 2),
    }


def variables_with(variables: BalanceVariables, **changes: float) -> BalanceVariables:
    data = asdict(variables)
    data.update(changes)
    data["tower_health"] = clamp(data["tower_health"], 10, 250)
    data["tower_defense"] = clamp(data["tower_defense"], 0, 99)
    data["player_damage"] = clamp(data["player_damage"], 1, 50)
    data["player_attack_speed"] = clamp(data["player_attack_speed"], 0.15, 3.0)
    data["player_attack_radius"] = clamp(data["player_attack_radius"], 24, 220)
    data["player_speed"] = clamp(data["player_speed"], 80, 600)
    data["friendly_spawn_interval"] = clamp(data["friendly_spawn_interval"], 2, 25)
    data["night_enemy_stat_bonus"] = clamp(data["night_enemy_stat_bonus"], 0, 0.35)
    data["night_enemy_count_bonus"] = clamp(data["night_enemy_count_bonus"], 0, 0.35)
    return BalanceVariables(**data)


def solve_for_target(
    player: PlayerBalanceInput,
    variables: BalanceVariables = BalanceVariables(),
) -> BalanceReport:
    skill = estimate_skill(player)
    target = max(0.1, clean_number(player.expected_nights, 1.0))
    current = variables
    predicted = predict_survival_nights(current, skill)
    for _ in range(220):
        error = target - predicted
        if abs(error) <= 0.15:
            break
        needs_easier = error > 0
        factor = 1.018 if needs_easier else 0.982
        inverse = 0.982 if needs_easier else 1.018
        current = variables_with(
            current,
            tower_health=current.tower_health * factor,
            player_damage=current.player_damage * factor,
            player_attack_speed=current.player_attack_speed * inverse,
            friendly_spawn_interval=current.friendly_spawn_interval * inverse,
            night_enemy_stat_bonus=current.night_enemy_stat_bonus * inverse,
            night_enemy_count_bonus=current.night_enemy_count_bonus * inverse,
        )
        predicted = predict_survival_nights(current, skill)

    base = asdict(variables)
    recommended = {
        key: round(value, 4)
        for key, value in asdict(current).items()
    }
    delta = {
        key: round(recommended[key] - float(base[key]), 4)
        for key in recommended
    }
    return BalanceReport(
        predicted_nights=round(predicted, 2),
        target_nights=round(target, 2),
        estimated_player_skill=round(skill, 3),
        playtest_summary=run_playtest_batch(current, skill),
        variable_weights=variable_sensitivity(current, skill),
        recommended_settings=recommended,
        recommendation_delta=delta,
    )


def report_to_dict(report: BalanceReport) -> dict:
    return asdict(report)
