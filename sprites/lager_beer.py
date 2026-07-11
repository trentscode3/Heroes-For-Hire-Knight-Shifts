import pygame

from core.settings import (
    LAGER_LAUNCHER_BEER_SIZE,
    LAGER_LAUNCHER_BEER_PATH,
    LAGER_LAUNCHER_BEER_SPEED,
    LAGER_LAUNCHER_BUFF_DURATION,
    LAGER_LAUNCHER_BUFF_MULTIPLIER,
    LAGER_LAUNCHER_HOMING_SPEED,
    LAGER_LAUNCHER_PICKUP_RANGE,
)
from .player import Player
from .sprite import Sprite


class LagerBeer(Sprite):
    """A launched beer that flies outward, then homes into the hero."""

    def __init__(
        self,
        center: tuple[float, float],
        target: tuple[float, float],
        buff_type: str,
    ) -> None:
        width, height = LAGER_LAUNCHER_BEER_SIZE
        super().__init__(
            (center[0] - width / 2, center[1] - height / 2),
            LAGER_LAUNCHER_BEER_SIZE,
            (194, 126, 40),
            LAGER_LAUNCHER_BEER_PATH,
        )
        self.buff_type = buff_type
        self.landing_position = pygame.Vector2(target)
        direction = self.landing_position - pygame.Vector2(self.rect.center)
        if direction.length_squared() == 0:
            direction.update(0.0, 1.0)
        self.velocity = direction.normalize() * LAGER_LAUNCHER_BEER_SPEED
        self.state = "flying"
        self.mask = pygame.mask.from_surface(self.image)
        self.hitbox = self.rect.copy()

    def update(self, dt: float, player: Player) -> None:
        if self.state == "flying":
            to_landing = self.landing_position - pygame.Vector2(self.rect.center)
            movement = self.velocity * dt
            if movement.length_squared() >= to_landing.length_squared():
                self.pos.update(
                    self.landing_position.x - self.rect.width / 2,
                    self.landing_position.y - self.rect.height / 2,
                )
                self.velocity.update(0.0, 0.0)
                self.state = "waiting"
            else:
                self.pos += movement
            self.sync_rect()

        if self.state == "waiting":
            pickup_area = pygame.Rect((0, 0), LAGER_LAUNCHER_PICKUP_RANGE)
            pickup_area.center = self.rect.center
            if pickup_area.collidepoint(player.hitbox.center):
                self.state = "homing"

        if self.state == "homing":
            direction = pygame.Vector2(player.hitbox.center) - pygame.Vector2(
                self.rect.center
            )
            if direction.length_squared() > 0:
                self.velocity += (
                    direction.normalize()
                    * LAGER_LAUNCHER_HOMING_SPEED
                    * 3.0
                    * dt
                )
                if self.velocity.length() > LAGER_LAUNCHER_HOMING_SPEED:
                    self.velocity.scale_to_length(LAGER_LAUNCHER_HOMING_SPEED)

            self.pos += self.velocity * dt
            self.sync_rect()
        if self.state == "homing" and self.rect.colliderect(player.hitbox):
            player.apply_temporary_buff(
                self.buff_type,
                LAGER_LAUNCHER_BUFF_MULTIPLIER,
                LAGER_LAUNCHER_BUFF_DURATION,
            )
            self.kill()
