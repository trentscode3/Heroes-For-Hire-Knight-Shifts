import math

import pygame

from core.audio_manager import audio
from core.settings import (
    LEVEL_UP_ARC_INCREASE,
    PLAYER_ATTACK_RADIUS,
    ROBIN_HOOD_CHARACTER_PATH,
    ROBIN_HOOD_CRIT_DISTANCE,
    ROBIN_HOOD_MAX_CRIT_CHANCE,
    ROBIN_HOOD_MIN_CRIT_CHANCE,
)
from .hero_arrow import HeroArrow
from .player import Player


class RobinHood(Player):
    HERO_ID = "robin_hood"
    HERO_NAME = "Robin Hood"
    HERO_DESCRIPTION = "A precision archer whose arrows travel through the battlefield."
    ATTACK_STYLE = "Aimed arrow"
    CHARACTER_PATH = ROBIN_HOOD_CHARACTER_PATH

    def __init__(self, start_pos=None) -> None:
        super().__init__() if start_pos is None else super().__init__(start_pos)
        self.crit_chance = ROBIN_HOOD_MIN_CRIT_CHANCE
        self.pending_projectiles: list[HeroArrow] = []
        self.arrow_size_multiplier = 2.0

    def reset_gear_bases(self) -> None:
        super().reset_gear_bases()
        self.crit_chance = ROBIN_HOOD_MIN_CRIT_CHANCE

    def refresh_progression_stats(self) -> None:
        super().refresh_progression_stats()
        self.arrow_size_multiplier = 2.0 * (
            self.attack_area_upgrade_multiplier
            + self.sword_arc_upgrade_count
            * LEVEL_UP_ARC_INCREASE
            * self.attack_area_upgrade_multiplier
        )

    def critical_chance_for_distance(self, distance: float) -> float:
        if distance <= PLAYER_ATTACK_RADIUS:
            distance_chance = ROBIN_HOOD_MIN_CRIT_CHANCE
        elif distance >= ROBIN_HOOD_CRIT_DISTANCE:
            distance_chance = ROBIN_HOOD_MAX_CRIT_CHANCE
        else:
            progress = (
                (distance - PLAYER_ATTACK_RADIUS)
                / (ROBIN_HOOD_CRIT_DISTANCE - PLAYER_ATTACK_RADIUS)
            )
            band = min(2, math.floor(progress * 3))
            distance_chance = ROBIN_HOOD_MIN_CRIT_CHANCE * (band + 1)
        gear_bonus = max(0.0, self.crit_chance - ROBIN_HOOD_MIN_CRIT_CHANCE)
        return min(1.0, distance_chance + gear_bonus)

    def attack(self, enemies: pygame.sprite.Group, dt: float) -> list:
        if self.is_dead:
            return []
        self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - dt)
        self.attack_animation_timer = max(0.0, self.attack_animation_timer - dt)
        if not self.attack_requested or self.attack_cooldown_timer > 1e-9:
            return []

        audio.play_sound("player_attack")
        if self.requested_attack_direction is not None:
            self.attack_direction = self.requested_attack_direction
        target = self.requested_attack_target
        if target is None:
            target = pygame.Vector2(self.rect.center) + self.attack_direction * 100
        self.facing = self.facing_from_vector(self.attack_direction)
        self.attack_cooldown_timer = self.attack_speed
        self.attack_animation_timer = self.attack_animation_time
        self.attack_is_critical = False
        self.animation_state = "attack"
        self.animation_elapsed = 0.0
        self.update_animation(0.0)
        damage = self.atkdmg
        self.pending_projectiles.append(
            HeroArrow(
                self.rect.center,
                target,
                damage,
                self,
                self.attack_is_critical,
                self.arrow_size_multiplier,
            )
        )
        return []

    def consume_projectiles(self) -> list[HeroArrow]:
        projectiles = self.pending_projectiles
        self.pending_projectiles = []
        return projectiles

    def display_attack(self, surface: pygame.Surface) -> None:
        # The arrow itself is the attack visual.
        return
