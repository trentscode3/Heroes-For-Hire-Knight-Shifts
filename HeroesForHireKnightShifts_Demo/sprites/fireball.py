import pygame

from core.settings import (
    FIREBALL_ASSET_PATH,
    FIREBALL_COLOR,
    FIREBALL_EXPLOSION_DURATION,
    FIREBALL_EXPLOSION_RADIUS,
    FIREBALL_EXPLOSION_STEPS,
    FIREBALL_SIZE,
    FIREBALL_SPEED,
)
from .sprite import Sprite


class Fireball(Sprite):
    def __init__(self, start_center, target_center, damage: float, source) -> None:
        start_pos = (
            start_center[0] - FIREBALL_SIZE[0] / 2,
            start_center[1] - FIREBALL_SIZE[1] / 2,
        )
        super().__init__(start_pos, FIREBALL_SIZE, (0, 0, 0, 0), FIREBALL_ASSET_PATH)
        if self.image.get_bounding_rect().width <= 0:
            self.image.fill((0, 0, 0, 0))
            pygame.draw.circle(
                self.image,
                FIREBALL_COLOR,
                self.image.get_rect().center,
                min(FIREBALL_SIZE) // 2,
            )
        self.mask = pygame.mask.from_surface(self.image)
        direction = pygame.Vector2(target_center) - pygame.Vector2(start_center)
        if direction.length_squared() == 0:
            direction.update(1.0, 0.0)
        self.velocity = direction.normalize() * FIREBALL_SPEED
        self.center_pos = pygame.Vector2(start_center)
        self.damage = damage
        self.source = source
        self.active = True
        self.exploding = False
        self.explosion_elapsed = 0.0
        self.base_image = self.image.copy()

    def explode(self) -> None:
        if self.exploding:
            return
        self.active = False
        self.exploding = True
        self.explosion_elapsed = 0.0

    def update_explosion_image(self) -> None:
        progress = min(1.0, self.explosion_elapsed / FIREBALL_EXPLOSION_DURATION)
        step_progress = (
            int(progress * FIREBALL_EXPLOSION_STEPS) + 1
        ) / FIREBALL_EXPLOSION_STEPS
        size = max(2, round(FIREBALL_EXPLOSION_RADIUS * 2 * step_progress))
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        alpha = round(220 * (1.0 - progress))
        color = (255, 255, 255) if progress > 0.72 else FIREBALL_COLOR
        pygame.draw.circle(
            self.image,
            (*color, alpha),
            self.image.get_rect().center,
            size // 2,
        )
        self.rect = self.image.get_rect(center=self.center_pos)
        self.pos.update(self.rect.topleft)
        self.hitbox = self.rect.copy()
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, dt: float) -> None:
        if self.exploding:
            self.explosion_elapsed += dt
            if self.explosion_elapsed >= FIREBALL_EXPLOSION_DURATION:
                self.kill()
                return
            self.update_explosion_image()
            return
        self.center_pos += self.velocity * dt
        self.rect.center = (round(self.center_pos.x), round(self.center_pos.y))
        self.pos.update(self.rect.topleft)
        self.hitbox = self.rect.copy()
