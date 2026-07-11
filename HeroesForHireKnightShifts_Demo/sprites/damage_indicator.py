import pygame

from core.ui_font import ui_font

from core.settings import (
    DAMAGE_INDICATOR_FONT_SIZE,
    DAMAGE_INDICATOR_LIFETIME,
    DAMAGE_INDICATOR_RISE_SPEED,
)


class DamageIndicator(pygame.sprite.Sprite):
    """Short-lived floating combat text anchored at a world position."""

    def __init__(
        self,
        center: tuple[float, float],
        damage: float,
        color: tuple[int, int, int],
    ) -> None:
        super().__init__()
        self.lifetime = DAMAGE_INDICATOR_LIFETIME
        self.remaining = self.lifetime
        self.position = pygame.Vector2(center)
        value = str(round(damage)) if float(damage).is_integer() else f"{damage:.1f}"
        font = ui_font(DAMAGE_INDICATOR_FONT_SIZE)
        self.original_image = font.render(value, True, color)
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=center)

    def update(self, dt: float) -> None:
        self.remaining = max(0.0, self.remaining - dt)
        self.position.y -= DAMAGE_INDICATOR_RISE_SPEED * dt
        self.image = self.original_image.copy()
        self.image.set_alpha(round(255 * self.remaining / self.lifetime))
        self.rect = self.image.get_rect(center=(round(self.position.x), round(self.position.y)))
        if self.remaining <= 0:
            self.kill()
