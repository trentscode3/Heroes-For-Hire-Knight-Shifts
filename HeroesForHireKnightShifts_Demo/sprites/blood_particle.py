import pygame

from core.settings import (
    ENEMY_BLOOD_COLOR,
    ENEMY_BLOOD_GRAVITY,
    ENEMY_BLOOD_PARTICLE_SIZES,
)


class BloodParticle(pygame.sprite.Sprite):
    def __init__(
        self,
        position,
        velocity,
        ground_y: float,
        size: int,
        color=ENEMY_BLOOD_COLOR,
    ) -> None:
        super().__init__()
        if size not in ENEMY_BLOOD_PARTICLE_SIZES:
            raise ValueError(f"Unsupported blood particle size: {size}")
        self.image = pygame.Surface((size, size))
        self.image.fill(color)
        self.pos = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.ground_y = ground_y
        self.settled = False
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def update(self, dt: float) -> None:
        if self.settled:
            return
        self.velocity.y += ENEMY_BLOOD_GRAVITY * dt
        self.pos += self.velocity * dt
        if self.pos.y >= self.ground_y:
            self.pos.y = self.ground_y
            self.velocity.update(0, 0)
            self.settled = True
        self.rect.center = (round(self.pos.x), round(self.pos.y))
