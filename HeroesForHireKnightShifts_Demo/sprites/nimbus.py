import math
import random

import pygame

from core.audio_manager import audio
from core.settings import (
    NIMBUS_CHARACTER_PATH,
    NIMBUS_ATTACK_SPEED,
    NIMBUS_ATTACK_DAMAGE,
    NIMBUS_LIGHTNING_COLOR,
    NIMBUS_MAX_DAMAGE_MULTIPLIER,
    NIMBUS_MIN_DAMAGE_MULTIPLIER,
    NIMBUS_MULTIPLIER_RING_RADIUS,
    NIMBUS_MULTIPLIER_RING_STEP,
    NIMBUS_STRIKE_COLOR,
    NIMBUS_STRIKE_RADIUS,
    LEVEL_UP_ARC_INCREASE,
    LEVEL_UP_RADIUS_INCREASE,
)
from .player import Player


class Nimbus(Player):
    HERO_ID = "nimbus"
    HERO_NAME = "Nimbus"
    HERO_DESCRIPTION = "A storm caller whose lightning is strongest at close range."
    ATTACK_STYLE = "Lightning strike"
    BASE_ATTACK_DAMAGE = NIMBUS_ATTACK_DAMAGE
    CHARACTER_PATH = NIMBUS_CHARACTER_PATH

    def __init__(self, start_pos=None) -> None:
        super().__init__() if start_pos is None else super().__init__(start_pos)
        self.strike_target: pygame.Vector2 | None = None
        self.minimum_damage_multiplier = NIMBUS_MIN_DAMAGE_MULTIPLIER
        self.reset_gear_bases()
        self.refresh_progression_stats()

    def reset_gear_bases(self) -> None:
        super().reset_gear_bases()
        self.base_attack_radius = float(NIMBUS_STRIKE_RADIUS)
        self.base_attack_speed = float(NIMBUS_ATTACK_SPEED)

    def refresh_progression_stats(self) -> None:
        super().refresh_progression_stats()
        self.attack_radius = round(
            self.base_attack_radius
            + self.sword_arc_upgrade_count
            * NIMBUS_STRIKE_RADIUS
            * LEVEL_UP_ARC_INCREASE
            * self.attack_area_upgrade_multiplier
        )
        self.minimum_damage_multiplier = min(
            NIMBUS_MAX_DAMAGE_MULTIPLIER,
            NIMBUS_MIN_DAMAGE_MULTIPLIER
            * (
                1
                + self.attack_radius_upgrade_count
                * LEVEL_UP_RADIUS_INCREASE
            ),
        )

    def distance_multiplier(self, enemy_position: pygame.Vector2) -> float:
        distance = pygame.Vector2(self.rect.center).distance_to(enemy_position)
        ring = max(0, math.ceil(distance / NIMBUS_MULTIPLIER_RING_RADIUS) - 1)
        return max(
            self.minimum_damage_multiplier,
            NIMBUS_MAX_DAMAGE_MULTIPLIER - ring * NIMBUS_MULTIPLIER_RING_STEP,
        )

    def attack(self, enemies: pygame.sprite.Group, dt: float) -> list:
        killed_enemies = []
        if self.is_dead:
            return killed_enemies
        self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - dt)
        self.attack_animation_timer = max(0.0, self.attack_animation_timer - dt)
        if not self.attack_requested or self.attack_cooldown_timer > 1e-9:
            return killed_enemies

        audio.play_sound("player_attack")
        target = self.requested_attack_target
        if target is None:
            target = pygame.Vector2(self.rect.center) + self.attack_direction * 100
        self.strike_target = pygame.Vector2(target)
        direction = self.strike_target - pygame.Vector2(self.rect.center)
        if direction.length_squared() > 0:
            self.attack_direction = direction.normalize()
            self.facing = self.facing_from_vector(direction)
        self.attack_cooldown_timer = self.attack_speed
        self.attack_animation_timer = self.attack_animation_time
        self.attack_is_critical = random.random() < self.crit_chance
        self.animation_state = "attack"
        self.animation_elapsed = 0.0
        self.update_animation(0.0)

        for enemy in list(enemies):
            closest = pygame.Vector2(
                max(enemy.hitbox.left, min(self.strike_target.x, enemy.hitbox.right)),
                max(enemy.hitbox.top, min(self.strike_target.y, enemy.hitbox.bottom)),
            )
            if closest.distance_to(self.strike_target) > self.attack_radius:
                continue
            damage = self.atkdmg * self.distance_multiplier(
                pygame.Vector2(enemy.hitbox.center)
            )
            if self.attack_is_critical:
                damage *= self.crit_multiplier
            if self.damage_enemy(enemy, damage, self.attack_is_critical):
                killed_enemies.append(enemy)
        return killed_enemies

    def display_attack(self, surface: pygame.Surface) -> None:
        if self.attack_animation_timer <= 0 or self.strike_target is None:
            return
        target = self.strike_target
        points = [(round(target.x), 0)]
        segments = 7
        for index in range(1, segments):
            y = target.y * index / segments
            x = target.x + (-1 if index % 2 else 1) * (8 + index * 2)
            points.append((round(x), round(y)))
        points.append((round(target.x), round(target.y)))
        pygame.draw.lines(surface, NIMBUS_LIGHTNING_COLOR, False, points, 4)
        pygame.draw.circle(
            surface,
            NIMBUS_STRIKE_COLOR,
            (round(target.x), round(target.y)),
            round(self.attack_radius),
            width=3,
        )
