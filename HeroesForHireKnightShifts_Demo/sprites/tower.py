import math
from functools import lru_cache

import pygame

from core.audio_manager import audio
from core.settings import (
    TOWER_COLOR,
    TOWER_BASE_DEFENSE,
    TOWER_MAX_HEALTH,
    TOWER_SIZE,
    TOWER_SPRITE_PATH,
    TOWER_SHEET_COLUMNS,
    TOWER_SHEET_FRAME_SIZE,
    TOWER_HEALTH_FRAME_COUNT,
    TOWER_DEMOTION_SHAKE_DISTANCE,
    TOWER_DEMOTION_SHAKE_DURATION,
    TOWER_DEMOTION_SHAKE_FREQUENCY,
    PLAYER_ANIMATION_SOURCE_FRAME_SIZE,
    ROBIN_HOOD_CHARACTER_PATH,
    TOWER_ARCHER_PALETTE,
    TOWER_ARCHER_SIZE,
    TURRET_COLOR,
    WOODEN_STAKES_DISPLAY_SIZE,
    WOODEN_STAKES_PATH,
    LAGER_LAUNCHER_CATAPULT_COLOR,
    LAGER_LAUNCHER_CATAPULT_DARK_COLOR,
)
from .sprite import Sprite
from .palette import replace_palette


@lru_cache(maxsize=1)
def load_tower_health_frames() -> tuple[pygame.Surface, ...]:
    try:
        sheet = pygame.image.load(TOWER_SPRITE_PATH).convert_alpha()
    except (FileNotFoundError, pygame.error):
        return ()
    frame_width, frame_height = TOWER_SHEET_FRAME_SIZE
    frames = []
    for index in range(TOWER_HEALTH_FRAME_COUNT):
        column = index % TOWER_SHEET_COLUMNS
        row = index // TOWER_SHEET_COLUMNS
        source = sheet.subsurface(
            column * frame_width,
            row * frame_height,
            frame_width,
            frame_height,
        )
        frames.append(pygame.transform.scale(source, TOWER_SIZE))
    return tuple(frames)


@lru_cache(maxsize=1)
def load_tower_archer_image() -> pygame.Surface | None:
    try:
        sheet = pygame.image.load(
            ROBIN_HOOD_CHARACTER_PATH / "D_Idle.png"
        ).convert_alpha()
    except (FileNotFoundError, pygame.error):
        return None
    frame_width, frame_height = PLAYER_ANIMATION_SOURCE_FRAME_SIZE
    frame = sheet.subsurface((0, 0, frame_width, frame_height)).copy()
    return pygame.transform.scale(
        replace_palette(frame, TOWER_ARCHER_PALETTE),
        TOWER_ARCHER_SIZE,
    )


@lru_cache(maxsize=1)
def load_wooden_stakes_image() -> pygame.Surface | None:
    try:
        image = pygame.image.load(WOODEN_STAKES_PATH).convert_alpha()
    except (FileNotFoundError, pygame.error):
        return None
    return pygame.transform.scale(image, WOODEN_STAKES_DISPLAY_SIZE)


class Tower(Sprite):
    def __init__(self, center: tuple[float, float]) -> None:
        start_pos = (
            center[0] - TOWER_SIZE[0] / 2,
            center[1] - TOWER_SIZE[1] / 2,
        )
        super().__init__(
            start_pos=start_pos,
            size=TOWER_SIZE,
            color=TOWER_COLOR,
            sprite_path=None,
        )
        self.health_frames = load_tower_health_frames() or (self.image.copy(),)
        self.health_stage = 0
        if self.health_frames:
            self.image = self.health_frames[0]
        self.max_health = TOWER_MAX_HEALTH
        self.health = self.max_health
        self.defense = TOWER_BASE_DEFENSE
        self.damage_reflection = 0.0
        self.lager_launcher_enabled = False
        self.wooden_stakes_enabled = False
        self.turret_enabled = False
        self.archer_enabled = False
        self.turret_cooldown = 0.0
        self.archer_cooldown = 0.0
        self.boss_damage_reduction = 0.0
        self.demotion_shake_timer = 0.0
        self.damage_events: list[tuple[tuple[int, int], float, str]] = []
        self.archer_image = load_tower_archer_image()
        self.wooden_stakes_image = load_wooden_stakes_image()

    def health_stage_for(self, health: float) -> int:
        ratio = health / self.max_health
        if ratio >= 0.75:
            return 0
        if ratio >= 0.50:
            return 1
        if ratio >= 0.25:
            return 2
        if health > 0:
            return 3
        return 4

    def refresh_health_frame(self) -> None:
        new_stage = self.health_stage_for(self.health)
        if new_stage > self.health_stage:
            self.demotion_shake_timer = TOWER_DEMOTION_SHAKE_DURATION
        self.health_stage = new_stage
        self.image = self.health_frames[min(new_stage, len(self.health_frames) - 1)]

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount: float, attacker=None) -> float:
        if amount < 0:
            raise ValueError("Damage cannot be negative")
        if attacker is not None and getattr(attacker, "IS_BOSS", False):
            amount *= 1.0 - self.boss_damage_reduction
        self.defense = max(0, min(99, self.defense))
        health_lost = amount * (100 - self.defense) / 100
        self.health = max(0, self.health - health_lost)
        self.refresh_health_frame()
        if health_lost > 0:
            audio.play_sound("tower_damaged")
            self.damage_events.append((self.rect.center, health_lost, "monster"))
            if attacker is not None and self.damage_reflection > 0:
                reflected = health_lost * self.damage_reflection
                attacker.take_damage(reflected)
                self.damage_events.append(
                    (attacker.rect.center, reflected, "player")
                )
        return health_lost

    def consume_damage_events(
        self,
    ) -> list[tuple[tuple[int, int], float, str]]:
        events = self.damage_events
        self.damage_events = []
        return events

    def update(self, dt: float) -> None:
        self.demotion_shake_timer = max(0.0, self.demotion_shake_timer - dt)

    def mounted_upgrade_drop(self) -> int:
        """Follow the visible roof height of each tower damage frame."""
        return (0, 6, 14, 55, 88)[min(self.health_stage, 4)]

    def lager_launch_center(self) -> tuple[float, float]:
        return (
            self.rect.centerx + 2,
            self.rect.top + 8 + self.mounted_upgrade_drop(),
        )

    @staticmethod
    def draw_wooden_stake(
        surface: pygame.Surface,
        center_x: int,
        base_y: int,
    ) -> None:
        outline = (
            (center_x, base_y - 25),
            (center_x - 7, base_y),
            (center_x + 7, base_y),
        )
        wood = (
            (center_x, base_y - 21),
            (center_x - 4, base_y - 1),
            (center_x + 4, base_y - 1),
        )
        pygame.draw.polygon(surface, (48, 29, 18), outline)
        pygame.draw.polygon(surface, (126, 78, 39), wood)
        pygame.draw.line(
            surface,
            (183, 121, 62),
            (center_x - 1, base_y - 17),
            (center_x - 2, base_y - 4),
            2,
        )

    def display(self, surface: pygame.Surface) -> None:
        shake_offset = 0
        if self.demotion_shake_timer > 0:
            shake_offset = round(
                math.sin(
                    self.demotion_shake_timer
                    * TOWER_DEMOTION_SHAKE_FREQUENCY
                    * math.tau
                )
                * TOWER_DEMOTION_SHAKE_DISTANCE
            )
        display_rect = self.rect.move(shake_offset, 0)
        surface.blit(self.image, display_rect)
        upgrade_drop = self.mounted_upgrade_drop()
        if self.wooden_stakes_enabled:
            stake_y = display_rect.bottom - 7
            if self.wooden_stakes_image is not None:
                for center_x in (display_rect.centerx - 27, display_rect.centerx + 27):
                    stake_rect = self.wooden_stakes_image.get_rect(
                        midbottom=(center_x, stake_y)
                    )
                    surface.blit(self.wooden_stakes_image, stake_rect)
            else:
                self.draw_wooden_stake(surface, display_rect.centerx - 25, stake_y)
                self.draw_wooden_stake(surface, display_rect.centerx + 25, stake_y)
        if self.lager_launcher_enabled:
            base = pygame.Rect(0, 0, 30, 12)
            base.midbottom = (
                display_rect.centerx - 20,
                display_rect.top + 36 + upgrade_drop,
            )
            pygame.draw.rect(surface, LAGER_LAUNCHER_CATAPULT_COLOR, base)
            pygame.draw.rect(surface, LAGER_LAUNCHER_CATAPULT_DARK_COLOR, base, width=2)
            pivot = pygame.Vector2(base.centerx, base.top + 2)
            arm_end = pivot + pygame.Vector2(22, -18)
            pygame.draw.line(surface, LAGER_LAUNCHER_CATAPULT_DARK_COLOR, pivot, arm_end, 5)
            pygame.draw.circle(surface, LAGER_LAUNCHER_CATAPULT_COLOR, pivot, 5)
            bucket = pygame.Rect(0, 0, 10, 7)
            bucket.center = arm_end
            pygame.draw.rect(surface, LAGER_LAUNCHER_CATAPULT_DARK_COLOR, bucket)
        if self.turret_enabled:
            turret_rect = pygame.Rect(0, 0, 22, 14)
            turret_rect.midbottom = (
                display_rect.centerx,
                display_rect.top + 10 + upgrade_drop,
            )
            pygame.draw.rect(surface, TURRET_COLOR, turret_rect)
            pygame.draw.rect(surface, (25, 25, 28), turret_rect, width=2)
        if self.archer_enabled and self.archer_image is not None:
            archer_x = display_rect.centerx + (20 if self.lager_launcher_enabled else 0)
            archer_rect = self.archer_image.get_rect(
                midbottom=(archer_x, display_rect.top + 24 + upgrade_drop)
            )
            surface.blit(self.archer_image, archer_rect)
