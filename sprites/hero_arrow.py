import pygame

from core.settings import (
    HERO_PROJECTILE_MARGIN,
    ROBIN_HOOD_ARROW_COLOR,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from .arrow import Arrow


class HeroArrow(Arrow):
    """Player-fired arrow that continues toward the edge of the screen."""

    def __init__(
        self,
        start_center,
        target_center,
        damage,
        source,
        critical,
        size_multiplier: float = 2.0,
    ) -> None:
        super().__init__(
            start_center,
            target_center,
            damage,
            source,
            color=ROBIN_HOOD_ARROW_COLOR,
        )
        self.critical = critical
        self.base_damage = damage
        self.origin = pygame.Vector2(start_center)
        self.hit_enemies: set[pygame.sprite.Sprite] = set()
        self.kill_count = 0
        center = self.rect.center
        size = (
            max(1, round(self.image.get_width() * size_multiplier)),
            max(1, round(self.image.get_height() * size_multiplier)),
        )
        self.image = pygame.transform.scale(self.image, size)
        self.rect = self.image.get_rect(center=center)
        self.pos.update(self.rect.topleft)
        self.hitbox = self.rect.copy()
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, dt: float) -> None:
        super().update(dt)
        bounds = pygame.Rect(
            -HERO_PROJECTILE_MARGIN,
            -HERO_PROJECTILE_MARGIN,
            SCREEN_WIDTH + HERO_PROJECTILE_MARGIN * 2,
            SCREEN_HEIGHT + HERO_PROJECTILE_MARGIN * 2,
        )
        if not bounds.colliderect(self.rect):
            self.kill()
