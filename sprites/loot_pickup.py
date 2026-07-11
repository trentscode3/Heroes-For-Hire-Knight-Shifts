import math
import random
from typing import TYPE_CHECKING

import pygame

from core.audio_manager import audio
from items import Gear
from items.item import load_item_image
from core.settings import (
    COIN_PICKUP_COLOR,
    COIN_PICKUP_HIGHLIGHT_COLOR,
    COIN_PICKUP_SIZE,
    GEAR_PICKUP_SIZE,
    XP_BURST_SPEED_MAX,
    XP_BURST_SPEED_MIN,
    XP_GRAVITY_DELAY,
    XP_PICKUP_DELAY,
    XP_SPRITE_ACCELERATION,
    XP_SPRITE_MAX_SPEED,
)
from .player import Player
from .sprite import Sprite

if TYPE_CHECKING:
    from core.game_state import GameState


class LootPickup(Sprite):
    def __init__(self, center: tuple[float, float], size: tuple[int, int]) -> None:
        super().__init__(
            (center[0] - size[0] / 2, center[1] - size[1] / 2),
            size,
            (0, 0, 0, 0),
        )
        self.age = 0.0
        angle = random.uniform(0.0, math.tau)
        speed = random.uniform(XP_BURST_SPEED_MIN, XP_BURST_SPEED_MAX)
        self.velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed

    def update_motion(self, dt: float, player: Player) -> bool:
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
        return self.age >= XP_PICKUP_DELAY and self.rect.colliderect(player.hitbox)


class CoinPickup(LootPickup):
    def __init__(self, center: tuple[float, float]) -> None:
        super().__init__(center, COIN_PICKUP_SIZE)
        self.image.fill((0, 0, 0, 0))
        pygame.draw.ellipse(self.image, (111, 71, 12), self.image.get_rect())
        pygame.draw.ellipse(
            self.image,
            COIN_PICKUP_COLOR,
            self.image.get_rect().inflate(-2, -2),
        )
        pygame.draw.arc(
            self.image,
            COIN_PICKUP_HIGHLIGHT_COLOR,
            self.image.get_rect().inflate(-3, -3),
            math.pi * 0.55,
            math.pi * 1.35,
            1,
        )
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, dt: float, player: Player, state: "GameState") -> None:
        if self.update_motion(dt, player):
            state.gold += 1
            audio.play_sound("money")
            self.kill()


class GearPickup(LootPickup):
    def __init__(self, center: tuple[float, float], gear: Gear) -> None:
        super().__init__(center, GEAR_PICKUP_SIZE)
        self.gear = gear
        self.image.fill((*gear.color, 255))
        pygame.draw.rect(self.image, (20, 20, 24), self.image.get_rect(), width=2)
        item_image = (
            load_item_image(str(gear.image_path))
            if gear.image_path is not None
            else None
        )
        if item_image is not None:
            displayed = pygame.transform.scale(item_image, (18, 18))
            self.image.blit(displayed, displayed.get_rect(center=self.image.get_rect().center))
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, dt: float, player: Player, state: "GameState") -> None:
        if self.update_motion(dt, player):
            equipped = state.receive_item(self.gear)
            if equipped:
                state.apply_player_gear(player)
            self.kill()
