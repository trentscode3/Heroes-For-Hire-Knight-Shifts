import random

import pygame

from core.settings import (
    CHARACTER_SHADOW_ANCHOR_RATIO,
    ENEMY_SIZE,
    ARCHER_ANIMATION_SOURCE_FRAME_SIZE,
    ARCHER_ATTACK_SPEED,
    ARCHER_ATTACK_TIME,
    ARCHER_CRIT_CHANCE,
    ARCHER_CRIT_MULTIPLIER,
    ARCHER_CHARACTER_PATH,
    ARCHER_COLOR,
    CLASSIC_ARCHER_PALETTE,
    ARCHER_DAMAGE,
    ARCHER_HEALTH,
    ARCHER_IDLE_ANIMATION_FPS,
    ARCHER_RANGE,
    ARCHER_RETREAT_DISTANCE,
    ARCHER_SIDE_ANIMATION_SOURCE_FACING,
    ARCHER_SLING_DURATION,
    ARCHER_WALK_ANIMATION_FPS,
    ENEMY_DEATH_ANIMATION_TIME,
    ARCHER_XP_REWARD,
)
from .enemy import Enemy
from .tower import Tower
from .animation import load_directional_animations


class Archer(Enemy):
    """Ranged enemy using Character 1 directional animations."""

    SIZE = ENEMY_SIZE
    CHARACTER_PATH = ARCHER_CHARACTER_PATH
    PALETTE = CLASSIC_ARCHER_PALETTE

    def __init__(self, start_pos: tuple[float, float], speed: float) -> None:
        super().__init__(
            start_pos=start_pos,
            size=ENEMY_SIZE,
            color=ARCHER_COLOR,
            speed=speed,
            max_health=ARCHER_HEALTH,
            damage=ARCHER_DAMAGE,
            attack_speed=ARCHER_ATTACK_SPEED,
            xp_reward=ARCHER_XP_REWARD,
            shadow_anchor_y_ratio=CHARACTER_SHADOW_ANCHOR_RATIO,
        )
        self.attack_range = ARCHER_RANGE
        self.attack_time = ARCHER_ATTACK_TIME
        self.attack_cooldown = 0.0
        self.attack_windup = 0.0
        self.is_attacking = False
        self.in_attack_range = False
        self.retreat_direction = pygame.Vector2()
        self.sling_timer = 0.0
        self.pending_shots: list[tuple[float, bool]] = []
        self.facing = "down"
        self.animation_state = "idle"
        self.animation_elapsed = 0.0
        self.animations = self.load_animations()
        self.image = self.animations[("down", "idle")][0]

    @staticmethod
    def facing_from_vector(direction: pygame.Vector2) -> str:
        if abs(direction.y) > abs(direction.x):
            return "down" if direction.y > 0 else "up"
        return "right" if direction.x >= 0 else "left"

    def load_animations(self):
        return load_directional_animations(
            str(self.CHARACTER_PATH),
            ARCHER_ANIMATION_SOURCE_FRAME_SIZE,
            self.SIZE,
            tuple(sorted(self.PALETTE.items())),
        )

    def ranged_attack(self, dt: float) -> None:
        if not self.is_attacking:
            self.attack_cooldown -= dt
            if self.attack_cooldown <= 0:
                self.is_attacking = True
                self.attack_windup = max(0.0, -self.attack_cooldown)
                self.attack_cooldown = 0.0
        else:
            self.attack_windup += dt

        if self.is_attacking and self.attack_windup >= self.attack_time:
            self.is_attacking = False
            self.attack_windup = 0.0
            self.attack_cooldown = self.attack_speed
            self.sling_timer = ARCHER_SLING_DURATION
            critical = random.random() < ARCHER_CRIT_CHANCE
            damage = self.damage * (ARCHER_CRIT_MULTIPLIER if critical else 1.0)
            self.pending_shots.append((damage, critical))

    def consume_pending_shots(self) -> list[tuple[float, bool]]:
        pending_shots = self.pending_shots
        self.pending_shots = []
        return pending_shots

    def get_visual_offset(self) -> pygame.Vector2:
        offset = super().get_visual_offset()
        retreat_amount = 0.0
        if self.is_attacking and self.attack_time > 0:
            progress = min(1.0, self.attack_windup / self.attack_time)
            retreat_amount = ARCHER_RETREAT_DISTANCE * (1 - (1 - progress) ** 2)
        elif self.sling_timer > 0 and ARCHER_SLING_DURATION > 0:
            progress = self.sling_timer / ARCHER_SLING_DURATION
            retreat_amount = ARCHER_RETREAT_DISTANCE * progress**2
        return offset + self.retreat_direction * retreat_amount

    def projectile_origin(self) -> tuple[float, float]:
        visual_offset = self.get_visual_offset()
        return (
            self.rect.centerx + visual_offset.x,
            self.rect.centery + visual_offset.y,
        )

    def update_animation(self, dt: float) -> None:
        if self.dying:
            state = "death"
        elif self.is_attacking or self.sling_timer > 0:
            state = "attack"
        elif self.in_attack_range:
            state = "idle"
        else:
            state = "walk"

        if state != self.animation_state:
            self.animation_state = state
            self.animation_elapsed = 0.0
        else:
            self.animation_elapsed += max(0.0, dt)

        sheet_direction = (
            "side" if self.facing in ("left", "right") else self.facing
        )
        frames = self.animations[(sheet_direction, state)]
        if state == "death":
            frame_index = self.animation_frame(
                self.death_elapsed,
                ENEMY_DEATH_ANIMATION_TIME,
                len(frames),
            )
        elif state == "attack":
            attack_elapsed = (
                self.attack_windup
                if self.is_attacking
                else self.attack_time
            )
            frame_index = self.animation_frame(
                attack_elapsed,
                self.attack_time,
                len(frames),
            )
        else:
            fps = (
                ARCHER_WALK_ANIMATION_FPS
                if state == "walk"
                else ARCHER_IDLE_ANIMATION_FPS
            )
            frame_index = int(self.animation_elapsed * fps) % len(frames)

        frame = frames[frame_index]
        flip_side_frame = (
            sheet_direction == "side"
            and self.facing != ARCHER_SIDE_ANIMATION_SOURCE_FACING
        )
        self.image = (
            pygame.transform.flip(frame, True, False)
            if flip_side_frame
            else frame
        )

    def update(self, dt: float, tower: Tower) -> None:
        if self.update_death(dt):
            self.update_animation(dt)
            return
        self.shake_timer = max(0.0, self.shake_timer - dt)
        self.sling_timer = max(0.0, self.sling_timer - dt)
        if self.stun_timer > 0:
            self.stun_timer = max(0.0, self.stun_timer - dt)
            self.move_dir.update(0.0, 0.0)
            self.is_attacking = False
            self.update_animation(dt)
            return
        to_tower = pygame.Vector2(tower.hitbox.center) - pygame.Vector2(
            self.hitbox.center
        )
        if to_tower.length_squared() > 0:
            self.facing = self.facing_from_vector(to_tower)

        if to_tower.length() <= self.attack_range:
            self.move_dir.update(0.0, 0.0)
            if not self.in_attack_range:
                self.in_attack_range = True
                self.is_attacking = False
                self.attack_windup = 0.0
                self.attack_cooldown = self.attack_speed / 2
                if to_tower.length_squared() > 0:
                    self.retreat_direction = -to_tower.normalize()
            self.ranged_attack(dt)
            self.update_animation(dt)
            return

        self.in_attack_range = False
        self.is_attacking = False
        self.attack_windup = 0.0
        self.attack_cooldown = 0.0
        self.move_dir = to_tower
        self.move(dt)
        self.sync_rect()
        self.update_animation(dt)
