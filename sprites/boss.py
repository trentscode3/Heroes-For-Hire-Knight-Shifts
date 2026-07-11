from pathlib import Path

import pygame

from core.settings import (
    CHARACTER_SHADOW_ANCHOR_RATIO,
    CHARACTER_SHADOW_PATH,
    CHARACTER_SHADOW_REFERENCE_SIZE,
    ENEMY_DEATH_ANIMATION_TIME,
    KNIGHT_ANIMATION_SOURCE_FRAME_SIZE,
    KNIGHT_IDLE_ANIMATION_FPS,
    KNIGHT_SIDE_ANIMATION_SOURCE_FACING,
    KNIGHT_WALK_ANIMATION_FPS,
)
from .animation import load_directional_animations
from .enemy import Enemy
from .sprite import collide_hitboxes, sprites_collide
from .tower import Tower


class Boss(Enemy):
    """Enemy with a timed, frame-based melee attack animation."""

    TITLE = "Boss"
    TITLE_CARD_PATH: Path | None = None
    IS_BOSS = True

    def __init__(
        self,
        start_pos: tuple[float, float],
        size: tuple[int, int],
        color: pygame.Color | tuple[int, int, int],
        speed: float,
        max_health: int,
        damage: int,
        attack_speed: float,
        attack_animation_time: float,
        xp_reward: int,
        sprite_path: str | Path | None = None,
        character_path: str | Path | None = None,
        palette: dict | None = None,
    ) -> None:
        super().__init__(
            start_pos,
            size,
            color,
            speed,
            max_health,
            damage,
            attack_speed,
            xp_reward,
            sprite_path,
        )
        self.attack_animation_time = attack_animation_time
        self.attack_cycle_timer = 0.0
        self.attack_animation_elapsed = 0.0
        self.is_attacking = False
        self.in_attack_range = False
        self.first_boss_attack = True
        self.tower_side = 1
        self.facing = "down"
        self.animation_state = "walk"
        self.animation_elapsed = 0.0
        self.animations = None
        if character_path is not None:
            self.animations = load_directional_animations(
                str(character_path),
                KNIGHT_ANIMATION_SOURCE_FRAME_SIZE,
                size,
                tuple(sorted((palette or {}).items())),
            )
            self.image = self.animations[("down", "walk")][0]
            self.set_collision_shadow(
                CHARACTER_SHADOW_PATH,
                CHARACTER_SHADOW_REFERENCE_SIZE,
                CHARACTER_SHADOW_ANCHOR_RATIO,
            )

    @staticmethod
    def facing_from_vector(direction: pygame.Vector2) -> str:
        if abs(direction.y) > abs(direction.x):
            return "down" if direction.y > 0 else "up"
        return "right" if direction.x >= 0 else "left"

    def update_character_animation(self, dt: float) -> None:
        if self.animations is None:
            return
        state = (
            "death"
            if self.dying
            else ("attack" if self.is_attacking else ("idle" if self.in_attack_range else "walk"))
        )
        if state != self.animation_state:
            self.animation_state = state
            self.animation_elapsed = 0.0
        else:
            self.animation_elapsed += max(0.0, dt)
        direction = "side" if self.facing in ("left", "right") else self.facing
        frames = self.animations[(direction, state)]
        if state == "death":
            frame_index = self.animation_frame(
                self.death_elapsed,
                ENEMY_DEATH_ANIMATION_TIME,
                len(frames),
            )
        elif state == "attack":
            frame_index = self.animation_frame(
                self.attack_animation_elapsed,
                self.attack_animation_time,
                len(frames),
            )
        else:
            fps = (
                KNIGHT_WALK_ANIMATION_FPS
                if state == "walk"
                else KNIGHT_IDLE_ANIMATION_FPS
            )
            frame_index = int(self.animation_elapsed * fps) % len(frames)
        frame = frames[frame_index]
        self.image = (
            pygame.transform.flip(frame, True, False)
            if direction == "side"
            and self.facing != KNIGHT_SIDE_ANIMATION_SOURCE_FACING
            else frame
        )

    def animated_attack(self, tower: Tower, dt: float) -> None:
        cycle_duration = (
            self.attack_speed / 2 if self.first_boss_attack else self.attack_speed
        )
        animation_start = max(0.0, cycle_duration - self.attack_animation_time)
        self.attack_cycle_timer += dt

        if self.attack_cycle_timer >= animation_start:
            self.is_attacking = True
            self.attack_animation_elapsed = min(
                self.attack_animation_time,
                self.attack_cycle_timer - animation_start,
            )

        if self.attack_cycle_timer >= cycle_duration:
            tower.take_damage(self.damage, self)
            self.attack_cycle_timer -= cycle_duration
            self.first_boss_attack = False
            self.is_attacking = False
            self.attack_animation_elapsed = 0.0

    def reset_attack(self) -> None:
        self.attack_cycle_timer = 0.0
        self.attack_animation_elapsed = 0.0
        self.is_attacking = False
        self.in_attack_range = False
        self.first_boss_attack = True

    def update(self, dt: float, tower: Tower) -> None:
        if self.update_death(dt):
            self.update_character_animation(dt)
            return
        self.shake_timer = max(0.0, self.shake_timer - dt)
        if self.stun_timer > 0:
            self.stun_timer = max(0.0, self.stun_timer - dt)
            self.move_dir.update(0.0, 0.0)
            self.in_attack_range = False
            self.is_attacking = False
            self.update_character_animation(dt)
            return
        to_tower = pygame.Vector2(tower.hitbox.center) - pygame.Vector2(
            self.hitbox.center
        )
        self.tower_side = 1 if to_tower.x >= 0 else -1
        if to_tower.length_squared() > 0:
            self.facing = self.facing_from_vector(to_tower)

        if sprites_collide(self, tower, collide_hitboxes):
            self.move_dir.update(0.0, 0.0)
            self.in_attack_range = True
            self.animated_attack(tower, dt)
            self.update_character_animation(dt)
            return

        self.reset_attack()
        self.move_dir = to_tower
        self.move(dt)
        self.sync_rect()
        self.update_character_animation(dt)
