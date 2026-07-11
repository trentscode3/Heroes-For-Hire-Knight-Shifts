import math

import pygame

from core.settings import (
    ARROW_COLOR,
    ARROW_HEAD_LENGTH,
    ARROW_HEAD_WIDTH,
    ARROW_SHAFT_SIZE,
    ARROW_SPEED,
)
from .sprite import Sprite


class Arrow(Sprite):
    def __init__(
        self,
        start_center: tuple[float, float],
        target_center: tuple[float, float],
        damage: float,
        source=None,
        color: tuple[int, int, int] = ARROW_COLOR,
    ) -> None:
        direction = pygame.Vector2(target_center) - pygame.Vector2(start_center)
        if direction.length_squared() == 0:
            direction.update(1.0, 0.0)
        direction.normalize_ip()

        shaft_length, shaft_width = ARROW_SHAFT_SIZE
        base_width = shaft_length + ARROW_HEAD_LENGTH
        base_height = max(shaft_width, ARROW_HEAD_WIDTH)
        base_image = pygame.Surface((base_width, base_height), pygame.SRCALPHA)
        shaft_y = (base_height - shaft_width) // 2
        pygame.draw.rect(
            base_image,
            color,
            pygame.Rect(0, shaft_y, shaft_length, shaft_width),
        )
        pygame.draw.polygon(
            base_image,
            color,
            (
                (shaft_length, 0),
                (base_width, base_height // 2),
                (shaft_length, base_height - 1),
            ),
        )

        angle = -math.degrees(math.atan2(direction.y, direction.x))
        arrow_image = pygame.transform.rotate(base_image, angle)
        start_pos = (
            start_center[0] - arrow_image.get_width() / 2,
            start_center[1] - arrow_image.get_height() / 2,
        )
        super().__init__(start_pos, arrow_image.get_size(), (0, 0, 0, 0))
        self.image = arrow_image
        self.rect = self.image.get_rect(center=start_center)
        self.pos = pygame.Vector2(self.rect.topleft)
        self.sync_hitbox()
        self.center_pos = pygame.Vector2(start_center)
        self.velocity = direction * ARROW_SPEED
        self.damage = damage
        self.source = source

    def update(self, dt: float) -> None:
        self.center_pos += self.velocity * dt
        self.rect.center = (round(self.center_pos.x), round(self.center_pos.y))
        self.pos.update(self.rect.topleft)
        self.sync_hitbox()
