import math
import random

import pygame

from core.settings import (
    XP_BURST_SPEED_MAX,
    XP_BURST_SPEED_MIN,
    XP_GRAVITY_DELAY,
    XP_PICKUP_DELAY,
    XP_SPRITE_ACCELERATION,
    XP_SPRITE_COLORS,
    XP_SPRITE_MAX_SPEED,
    XP_SPRITE_SIZES,
)
from .player import Player
from .sprite import Sprite, collide_hitboxes, sprites_collide


class XPSprite(Sprite):
    def __init__(self, center: tuple[float, float], value: int = 1) -> None:
        if value not in XP_SPRITE_SIZES:
            raise ValueError(f"Unsupported XP value: {value}")

        size = XP_SPRITE_SIZES[value]
        start_pos = (
            center[0] - size[0] / 2,
            center[1] - size[1] / 2,
        )
        super().__init__(start_pos, size, XP_SPRITE_COLORS[value])
        self.value = value
        self.age = 0.0
        burst_angle = random.uniform(0.0, math.tau)
        burst_speed = random.uniform(XP_BURST_SPEED_MIN, XP_BURST_SPEED_MAX)
        self.velocity = pygame.Vector2(
            math.cos(burst_angle), math.sin(burst_angle)
        ) * burst_speed

    def update(self, dt: float, player: Player) -> None:
        self.age += dt
        direction = pygame.Vector2(player.hitbox.center) - pygame.Vector2(
            self.rect.center
        )
        if self.age >= XP_GRAVITY_DELAY and direction.length_squared() > 0:
            self.velocity += direction.normalize() * XP_SPRITE_ACCELERATION * dt
            if self.velocity.length() > XP_SPRITE_MAX_SPEED:
                self.velocity.scale_to_length(XP_SPRITE_MAX_SPEED)

        self.pos += self.velocity * dt
        self.sync_rect()
        if self.age >= XP_PICKUP_DELAY and sprites_collide(
            self,
            player,
            collide_hitboxes,
        ):
            player.add_xp(self.value)
            self.kill()
