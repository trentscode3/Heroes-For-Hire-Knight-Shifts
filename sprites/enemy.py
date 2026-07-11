import math
import random
from pathlib import Path

import pygame

from core.audio_manager import audio
from core.settings import (
    CHARACTER_SHADOW_PATH,
    CHARACTER_SHADOW_REFERENCE_SIZE,
    ENEMY_HEALTH_BAR_BG_COLOR,
    ENEMY_HEALTH_BAR_COLOR,
    ENEMY_HEALTH_BAR_GAP,
    ENEMY_HEALTH_BAR_SIZE,
    ENEMY_BLOOD_PARTICLE_COUNT,
    ENEMY_BLOOD_PARTICLE_SIZES,
    ENEMY_DEATH_ANIMATION_TIME,
    ENEMY_HIT_SHAKE_DISTANCE,
    ENEMY_HIT_SHAKE_DURATION,
    ENEMY_HIT_SHAKE_FREQUENCY,
)
from .sprite import Sprite, collide_hitboxes, sprites_collide
from .blood_particle import BloodParticle
from .tower import Tower


class Enemy(Sprite):
    """Base class for enemies with movement and health."""

    def __init__(
        self,
        start_pos: tuple[float, float],
        size: tuple[int, int],
        color: pygame.Color | tuple[int, int, int],
        speed: float,
        max_health: int,
        damage: int,
        attack_speed: float,
        xp_reward: int,
        sprite_path: str | Path | None = None,
        bounds: pygame.Rect | None = None,
        shadow_anchor_y_ratio: float = 1.0,
    ) -> None:
        if speed < 0:
            raise ValueError("Speed cannot be negative")
        if max_health <= 0:
            raise ValueError("Maximum health must be positive")
        if damage < 0:
            raise ValueError("Damage cannot be negative")
        if attack_speed <= 0:
            raise ValueError("Attack speed must be positive")
        if xp_reward < 0:
            raise ValueError("XP reward cannot be negative")

        super().__init__(start_pos, size, color, sprite_path)
        self.set_collision_shadow(
            CHARACTER_SHADOW_PATH,
            CHARACTER_SHADOW_REFERENCE_SIZE,
            shadow_anchor_y_ratio,
        )
        self.speed = speed
        self.max_health = max_health
        self.health = max_health
        self.damage = damage
        self.attack_speed = attack_speed
        self.xp_reward = xp_reward
        self.attack_timer = 0.0
        self.first_attack_pending = True
        self.shake_timer = 0.0
        self.move_dir = pygame.Vector2()
        self.bounds = bounds
        self.dying = False
        self.death_elapsed = 0.0
        self.defeat_recorded = False
        self.pending_blood_particles: list[BloodParticle] = []
        self.stun_timer = 0.0

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    def take_damage(self, amount: float, attacker=None) -> None:
        if amount < 0:
            raise ValueError("Damage cannot be negative")

        if self.dying:
            return
        self.health = max(0, self.health - amount)
        if amount > 0:
            audio.play_sound("enemy_damaged")
            self.shake_timer = ENEMY_HIT_SHAKE_DURATION
            self.spawn_blood_particles()
        if not self.is_alive:
            self.start_death()

    def stun(self, duration: float) -> None:
        if duration <= 0 or self.dying:
            return
        self.stun_timer = max(self.stun_timer, duration)

    def start_death(self) -> None:
        if self.dying:
            return
        self.dying = True
        self.death_elapsed = 0.0
        self.move_dir.update(0, 0)
        # Death visuals remain in their draw group, but no longer participate
        # in any Pygame sprite collision checks.
        self.mask.clear()
        self.collision_group.empty()
        if hasattr(self, "is_attacking"):
            self.is_attacking = False
        self.spawn_blood_particles()

    def spawn_blood_particles(self) -> None:
        base_ground_y = (
            self.shadow_rect.centery
            if self.shadow_rect is not None
            else self.hitbox.centery
        )
        for _ in range(ENEMY_BLOOD_PARTICLE_COUNT):
            self.pending_blood_particles.append(
                BloodParticle(
                    (
                        self.rect.centerx + random.uniform(-8, 8),
                        self.rect.centery + random.uniform(-5, 4),
                    ),
                    (random.uniform(-75, 75), random.uniform(-105, -25)),
                    base_ground_y + random.uniform(-18, 18),
                    random.choice(ENEMY_BLOOD_PARTICLE_SIZES),
                )
            )

    def consume_blood_particles(self) -> list[BloodParticle]:
        particles = self.pending_blood_particles
        self.pending_blood_particles = []
        return particles

    def update_death(self, dt: float) -> bool:
        if not self.dying:
            return False
        self.shake_timer = max(0.0, self.shake_timer - dt)
        self.death_elapsed = min(
            ENEMY_DEATH_ANIMATION_TIME,
            self.death_elapsed + dt,
        )
        if self.death_elapsed >= ENEMY_DEATH_ANIMATION_TIME:
            self.kill()
        return True

    def move(self, dt: float) -> None:
        direction = (
            self.move_dir.normalize()
            if self.move_dir.length_squared() > 0
            else self.move_dir
        )
        self.pos += direction * self.speed * dt

    def attack(self, tower: Tower, dt: float) -> None:
        self.attack_timer += dt
        attack_delay = (
            self.attack_speed / 2
            if self.first_attack_pending
            else self.attack_speed
        )
        while self.attack_timer >= attack_delay and tower.is_alive:
            tower.take_damage(self.damage, self)
            self.attack_timer -= attack_delay
            self.first_attack_pending = False
            attack_delay = self.attack_speed

    def update(self, dt: float, tower: Tower) -> None:
        """Move toward the tower, then attack while touching it."""
        if self.update_death(dt):
            return
        self.shake_timer = max(0.0, self.shake_timer - dt)
        if self.stun_timer > 0:
            self.stun_timer = max(0.0, self.stun_timer - dt)
            self.move_dir.update(0.0, 0.0)
            return
        if sprites_collide(self, tower, collide_hitboxes):
            self.move_dir.update(0.0, 0.0)
            self.attack(tower, dt)
            return

        self.attack_timer = 0.0
        self.first_attack_pending = True
        self.move_dir = pygame.Vector2(tower.hitbox.center) - pygame.Vector2(
            self.hitbox.center
        )
        self.move(dt)
        if self.bounds is not None:
            self.clamp_to(self.bounds)
        else:
            self.sync_rect()

    def get_visual_offset(self) -> pygame.Vector2:
        offset = pygame.Vector2()
        if self.shake_timer > 0:
            offset.x = round(
                math.sin(
                    self.shake_timer * ENEMY_HIT_SHAKE_FREQUENCY * math.tau
                )
                * ENEMY_HIT_SHAKE_DISTANCE
            )
        return offset

    def display(self, surface: pygame.Surface) -> None:
        visual_offset = self.get_visual_offset()
        self.display_shadow(surface)
        draw_rect = self.rect.move(
            round(visual_offset.x), round(visual_offset.y)
        )
        if self.dying:
            progress = min(1.0, self.death_elapsed / ENEMY_DEATH_ANIMATION_TIME)
            death_image = self.image.copy()
            death_image.set_alpha(round(255 * (1 - progress * 0.65)))
            death_image = pygame.transform.rotate(death_image, progress * 12)
            death_rect = death_image.get_rect(midbottom=draw_rect.midbottom)
            surface.blit(death_image, death_rect)
        else:
            surface.blit(self.image, draw_rect)

        if self.dying:
            return

        bar_width, bar_height = ENEMY_HEALTH_BAR_SIZE
        bar_rect = pygame.Rect(
            draw_rect.centerx - bar_width // 2,
            draw_rect.top - ENEMY_HEALTH_BAR_GAP - bar_height,
            bar_width,
            bar_height,
        )
        pygame.draw.rect(surface, ENEMY_HEALTH_BAR_BG_COLOR, bar_rect)

        health_ratio = max(0.0, min(1.0, self.health / self.max_health))
        health_rect = bar_rect.copy()
        health_rect.width = round(bar_width * health_ratio)
        pygame.draw.rect(surface, ENEMY_HEALTH_BAR_COLOR, health_rect)
