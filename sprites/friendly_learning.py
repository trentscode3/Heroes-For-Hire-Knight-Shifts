import random
from collections.abc import Iterable

import pygame

from core.settings import FRIENDLY_KNIGHT_HOME_RADIUS
from .enemy import Enemy


class FriendlyKnightLearningPolicy:
    """Small online Q-learning policy shared by spawned friendly knights."""

    ACTIONS = (
        "closest",
        "weakest",
        "highest_threat",
        "tower_guard",
        "finisher",
    )

    def __init__(
        self,
        learning_rate: float = 0.22,
        discount: float = 0.82,
        exploration_rate: float = 0.16,
    ) -> None:
        self.learning_rate = learning_rate
        self.discount = discount
        self.exploration_rate = exploration_rate
        self.q_values: dict[tuple[str, str], float] = {}

    def state_for(
        self,
        knight,
        enemies: Iterable[Enemy],
        home: pygame.Vector2,
    ) -> str:
        alive_enemies = [enemy for enemy in enemies if enemy.is_alive]
        if not alive_enemies:
            return "no_enemies"

        health_ratio = knight.health / max(1.0, knight.max_health)
        health_bucket = "hurt" if health_ratio < 0.45 else "steady"
        closest_to_tower = min(
            home.distance_to(enemy.hitbox.center) for enemy in alive_enemies
        )
        if closest_to_tower < FRIENDLY_KNIGHT_HOME_RADIUS * 0.35:
            tower_pressure = "high_pressure"
        elif closest_to_tower < FRIENDLY_KNIGHT_HOME_RADIUS * 0.70:
            tower_pressure = "medium_pressure"
        else:
            tower_pressure = "low_pressure"
        density = "swarm" if len(alive_enemies) >= 5 else "skirmish"
        boss = "boss" if any(getattr(enemy, "IS_BOSS", False) for enemy in alive_enemies) else "normal"
        return "|".join((health_bucket, tower_pressure, density, boss))

    def q_value(self, state: str, action: str) -> float:
        return self.q_values.get((state, action), 0.0)

    def choose_action(self, state: str) -> str:
        if random.random() < self.exploration_rate:
            return random.choice(self.ACTIONS)
        best_value = max(self.q_value(state, action) for action in self.ACTIONS)
        best_actions = [
            action
            for action in self.ACTIONS
            if self.q_value(state, action) == best_value
        ]
        return random.choice(best_actions)

    def learn(
        self,
        state: str | None,
        action: str | None,
        reward: float,
        next_state: str,
    ) -> None:
        if state is None or action is None:
            return
        current = self.q_value(state, action)
        future = max(self.q_value(next_state, next_action) for next_action in self.ACTIONS)
        target = reward + self.discount * future
        self.q_values[(state, action)] = current + self.learning_rate * (target - current)

    def snapshot(self) -> dict:
        return {
            "q_values": {
                f"{state}\t{action}": value
                for (state, action), value in self.q_values.items()
            },
            "exploration_rate": self.exploration_rate,
        }

    def restore(self, data: dict) -> None:
        self.exploration_rate = float(
            data.get("exploration_rate", self.exploration_rate)
        )
        self.q_values.clear()
        for key, value in data.get("q_values", {}).items():
            if not isinstance(key, str) or "\t" not in key:
                continue
            state, action = key.split("\t", 1)
            if action in self.ACTIONS:
                self.q_values[(state, action)] = float(value)
