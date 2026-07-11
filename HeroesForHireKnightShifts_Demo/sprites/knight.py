import pygame

from core.settings import (
    CHARACTER_SHADOW_ANCHOR_RATIO,
    ENEMY_SIZE,
    ENEMY_DEATH_ANIMATION_TIME,
    KNIGHT_ANIMATION_SOURCE_FRAME_SIZE,
    KNIGHT_ATTACK_ANIMATION_TIME,
    KNIGHT_ATTACK_SPEED,
    KNIGHT_CHARACTER_PATH,
    KNIGHT_COLOR,
    CLASSIC_KNIGHT_PALETTE,
    KNIGHT_DAMAGE,
    KNIGHT_HEALTH,
    KNIGHT_IDLE_ANIMATION_FPS,
    KNIGHT_SIDE_ANIMATION_SOURCE_FACING,
    KNIGHT_WALK_ANIMATION_FPS,
    KNIGHT_XP_REWARD,
)
from .enemy import Enemy
from .sprite import collide_hitboxes, sprites_collide
from .tower import Tower
from .animation import load_directional_animations


class Knight(Enemy):
    SIZE = ENEMY_SIZE
    CHARACTER_PATH = KNIGHT_CHARACTER_PATH
    PALETTE = CLASSIC_KNIGHT_PALETTE

    def __init__(self, start_pos: tuple[float, float], speed: float) -> None:
        super().__init__(
            start_pos=start_pos,
            size=ENEMY_SIZE,
            color=KNIGHT_COLOR,
            speed=speed,
            max_health=KNIGHT_HEALTH,
            damage=KNIGHT_DAMAGE,
            attack_speed=KNIGHT_ATTACK_SPEED,
            xp_reward=KNIGHT_XP_REWARD,
            shadow_anchor_y_ratio=CHARACTER_SHADOW_ANCHOR_RATIO,
        )
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
            KNIGHT_ANIMATION_SOURCE_FRAME_SIZE,
            self.SIZE,
            tuple(sorted(self.PALETTE.items())),
        )

    def current_state(self, touching_tower: bool) -> tuple[str, float]:
        if self.dying:
            return "death", self.death_elapsed
        if not touching_tower:
            return "walk", 0.0

        attack_delay = (
            self.attack_speed / 2
            if self.first_attack_pending
            else self.attack_speed
        )
        time_until_attack = max(0.0, attack_delay - self.attack_timer)
        if time_until_attack <= KNIGHT_ATTACK_ANIMATION_TIME:
            return (
                "attack",
                KNIGHT_ATTACK_ANIMATION_TIME - time_until_attack,
            )
        return "idle", 0.0

    def update_animation(
        self,
        dt: float,
        touching_tower: bool,
    ) -> None:
        state, attack_elapsed = self.current_state(touching_tower)
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
            frame_index = self.animation_frame(
                attack_elapsed,
                KNIGHT_ATTACK_ANIMATION_TIME,
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
        flip_side_frame = (
            sheet_direction == "side"
            and self.facing != KNIGHT_SIDE_ANIMATION_SOURCE_FACING
        )
        self.image = (
            pygame.transform.flip(frame, True, False)
            if flip_side_frame
            else frame
        )

    def update(self, dt: float, tower: Tower) -> None:
        to_tower = pygame.Vector2(tower.hitbox.center) - pygame.Vector2(
            self.hitbox.center
        )
        if to_tower.length_squared() > 0:
            self.facing = self.facing_from_vector(to_tower)

        super().update(dt, tower)
        touching_tower = sprites_collide(self, tower, collide_hitboxes)
        self.update_animation(dt, touching_tower)
