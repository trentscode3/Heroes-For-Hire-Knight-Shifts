import pygame

from core.settings import (
    HERO_PROJECTILE_MARGIN,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TURRET_BULLET_SIZE,
    TURRET_BULLET_SPEED,
)
from .sprite import Sprite


class TowerBullet(Sprite):
    def __init__(self, start_center, target_center, damage: float, source) -> None:
        start_pos = (
            start_center[0] - TURRET_BULLET_SIZE[0] / 2,
            start_center[1] - TURRET_BULLET_SIZE[1] / 2,
        )
        super().__init__(start_pos, TURRET_BULLET_SIZE, (235, 225, 175))
        direction = pygame.Vector2(target_center) - pygame.Vector2(start_center)
        if direction.length_squared() == 0:
            direction.update(1.0, 0.0)
        self.velocity = direction.normalize() * TURRET_BULLET_SPEED
        self.center_pos = pygame.Vector2(start_center)
        self.damage = damage
        self.source = source
        self.critical = False

    def update(self, dt: float) -> None:
        self.center_pos += self.velocity * dt
        self.rect.center = (round(self.center_pos.x), round(self.center_pos.y))
        self.pos.update(self.rect.topleft)
        self.hitbox = self.rect.copy()
        bounds = pygame.Rect(
            -HERO_PROJECTILE_MARGIN,
            -HERO_PROJECTILE_MARGIN,
            SCREEN_WIDTH + HERO_PROJECTILE_MARGIN * 2,
            SCREEN_HEIGHT + HERO_PROJECTILE_MARGIN * 2,
        )
        if not bounds.colliderect(self.rect):
            self.kill()
