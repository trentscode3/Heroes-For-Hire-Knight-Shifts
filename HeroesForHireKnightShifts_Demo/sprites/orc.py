import random

import pygame

from core.settings import (
    ORC_ATTACK_ANIMATION_TIME,
    ORC_ATTACK_SPEED,
    ORC_COLOR,
    ORC_CHARACTER_PATH,
    ORC_DAMAGE,
    ORC_DEFENSE_COOLDOWN,
    ORC_HEALTH,
    ORC_STOMP_DURATION,
    ORC_STOMP_LIFT,
    ORC_STOMP_PARTICLE_COLOR,
    ORC_STOMP_PARTICLE_COUNT,
    ORC_SIZE,
    ORC_SPEED_MULTIPLIER,
    ORC_PALETTE,
    ORC_TITLE_CARD_PATH,
    ORC_XP_REWARD,
)
from .blood_particle import BloodParticle
from .boss import Boss


class Orc(Boss):
    SIZE = ORC_SIZE
    TITLE = "The Orc"
    TITLE_CARD_PATH = ORC_TITLE_CARD_PATH

    def __init__(self, start_pos: tuple[float, float], speed: float) -> None:
        super().__init__(
            start_pos=start_pos,
            size=ORC_SIZE,
            color=ORC_COLOR,
            speed=speed * ORC_SPEED_MULTIPLIER,
            max_health=ORC_HEALTH,
            damage=ORC_DAMAGE,
            attack_speed=ORC_ATTACK_SPEED,
            attack_animation_time=ORC_ATTACK_ANIMATION_TIME,
            xp_reward=ORC_XP_REWARD,
            character_path=ORC_CHARACTER_PATH,
            palette=ORC_PALETTE,
        )
        self.defense_cooldown = 0.0
        self.stomp_elapsed = ORC_STOMP_DURATION
        self.pending_dirt_particles: list[BloodParticle] = []

    def update(self, dt: float, tower) -> None:
        self.defense_cooldown = max(0.0, self.defense_cooldown - dt)
        self.stomp_elapsed = min(ORC_STOMP_DURATION, self.stomp_elapsed + dt)
        super().update(dt, tower)

    def take_damage(self, amount: float, attacker=None) -> None:
        previous_health = self.health
        super().take_damage(amount, attacker)
        if self.is_alive and self.health < previous_health and self.defense_cooldown <= 0:
            self.start_stomp()

    def start_stomp(self) -> None:
        self.defense_cooldown = ORC_DEFENSE_COOLDOWN
        self.stomp_elapsed = 0.0
        self.spawn_dirt_particles()

    @property
    def stomp_active(self) -> bool:
        return self.stomp_elapsed < ORC_STOMP_DURATION

    def stomp_impact_ready(self) -> bool:
        return 0.45 <= self.stomp_elapsed / ORC_STOMP_DURATION < 0.62

    def spawn_dirt_particles(self) -> None:
        ground_y = self.hitbox.centery + random.uniform(-10, 10)
        for _ in range(ORC_STOMP_PARTICLE_COUNT):
            direction = pygame.Vector2(1, 0).rotate(random.uniform(0, 360))
            speed = random.uniform(55, 155)
            self.pending_dirt_particles.append(
                BloodParticle(
                    self.hitbox.center,
                    direction * speed + pygame.Vector2(0, random.uniform(-80, -25)),
                    ground_y + random.uniform(-22, 22),
                    random.choice((1, 3, 5)),
                    ORC_STOMP_PARTICLE_COLOR,
                )
            )

    def consume_dirt_particles(self) -> list[BloodParticle]:
        particles = self.pending_dirt_particles
        self.pending_dirt_particles = []
        return particles

    def get_visual_offset(self) -> pygame.Vector2:
        offset = super().get_visual_offset()
        if not self.stomp_active:
            return offset
        progress = self.stomp_elapsed / ORC_STOMP_DURATION
        if progress < 0.55:
            offset.y -= ORC_STOMP_LIFT * (progress / 0.55)
        else:
            offset.y -= ORC_STOMP_LIFT * max(0.0, 1.0 - (progress - 0.55) / 0.18)
        return offset

    def display(self, surface: pygame.Surface) -> None:
        super().display(surface)
