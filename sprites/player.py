import math
import random
from collections.abc import Iterable

import pygame

from core.audio_manager import audio
from core.display_manager import display

from core.settings import (
    CHARACTER_SHADOW_PATH,
    CHARACTER_SHADOW_REFERENCE_SIZE,
    CHARACTER_SHADOW_ANCHOR_RATIO,
    LEVEL_UP_ARC_INCREASE,
    LEVEL_UP_BUFFER_MULTIPLIER,
    LEVEL_UP_DAMAGE_INCREASE,
    LEVEL_UP_RADIUS_INCREASE,
    PLAYER_ACCELERATION,
    PLAYER_ATTACK_ARC_STEPS,
    PLAYER_ATTACK_ANIMATION_TIME,
    PLAYER_ATTACK_COLOR,
    PLAYER_CRIT_CHANCE,
    PLAYER_CRIT_MULTIPLIER,
    PLAYER_ATTACK_DAMAGE,
    PLAYER_ATTACK_FRAME_COUNT,
    PLAYER_ATTACK_HALF_ANGLE,
    PLAYER_ATTACK_INITIAL_DIRECTION,
    PLAYER_ATTACK_RADIUS,
    PLAYER_ATTACK_SPEED,
    PLAYER_ANIMATION_SOURCE_FRAME_SIZE,
    PLAYER_CHARACTER_PATH,
    PLAYER_COLOR,
    PLAYER_DECELERATION,
    PLAYER_DEATH_ANIMATION_TIME,
    PLAYER_SIZE,
    PLAYER_SIDE_ANIMATION_SOURCE_FACING,
    PLAYER_SPEED,
    PLAYER_TOWER_COLLISION_OVERLAP,
    PLAYER_IDLE_ANIMATION_FPS,
    PLAYER_START_POS,
    PLAYER_START_LEVEL,
    PLAYER_XP_BASE,
    PLAYER_XP_GROWTH_BASE,
    PLAYER_XP_GROWTH_STEP,
    PORTAL_BOOTS_COOLDOWN,
    PORTAL_RESOLVE_STEP,
    ROCKET_BOOTS_COOLDOWN,
    ROCKET_BOOTS_DISTANCE,
    ROCKET_BOOTS_SPEED,
    PLAYER_WALK_ANIMATION_FPS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WARRIOR_NEW_SWORD_DAMAGE_MULTIPLIER,
    WARRIOR_NEW_SWORD_SIZE_MULTIPLIER,
    WARRIOR_CONDITIONING_MOVE_MULTIPLIER,
    WARRIOR_CONDITIONING_ATTACK_RATE_MULTIPLIER,
    WARRIOR_LEVEL_DAMAGE_MULTIPLIER,
    WARRIOR_LEVEL_ATTACK_SPEED_MULTIPLIER,
    WARRIOR_LEVEL_SIZE_MULTIPLIER,
    WARRIOR_SWORD_SPIN_SIZE_MULTIPLIER,
    WARRIOR_SWORD_SPIN_ANIMATION_MULTIPLIER,
    WARRIOR_SWORD_SPIN_MOVE_MULTIPLIER,
    WARRIOR_HEAVY_SWORD_SIZE_MULTIPLIER,
    WARRIOR_HEAVY_SWORD_DAMAGE_MULTIPLIER,
    WARRIOR_HEAVY_SWORD_ANIMATION_MULTIPLIER,
    WARRIOR_KINETIC_MOVE_MULTIPLIER,
    WARRIOR_KINETIC_ACCELERATION_MULTIPLIER,
    WARRIOR_ENERGY_CORE_ATTACK_RATE_MULTIPLIER,
    WARRIOR_ENERGY_CORE_MOVE_MULTIPLIER,
    WARRIOR_SPECIAL_SLASH_COLOR,
    WARRIOR_SPECIAL_SLASH_DASH_DISTANCE,
    WARRIOR_SPECIAL_SLASH_DASH_SPEED,
    WARRIOR_SPECIAL_SLASH_RANGE,
)
from .enemy import Enemy
from .animation import load_directional_animations
from .sprite import Sprite, collide_hitboxes
from .tower import Tower


class Player(Sprite):
    HERO_ID = "warrior"
    HERO_NAME = "Warrior"
    HERO_DESCRIPTION = "A close-range fighter with a broad melee slash."
    ATTACK_STYLE = "Sword swing"
    BASE_ATTACK_DAMAGE = PLAYER_ATTACK_DAMAGE
    CHARACTER_PATH = PLAYER_CHARACTER_PATH
    ANIMATION_SOURCE_FRAME_SIZE = PLAYER_ANIMATION_SOURCE_FRAME_SIZE
    SIDE_ANIMATION_SOURCE_FACING = PLAYER_SIDE_ANIMATION_SOURCE_FACING

    def __init__(
        self, start_pos: tuple[float, float] = PLAYER_START_POS
    ) -> None:
        super().__init__(
            start_pos=start_pos,
            size=PLAYER_SIZE,
            color=PLAYER_COLOR,
            sprite_path=None,
        )
        self.set_collision_shadow(
            CHARACTER_SHADOW_PATH,
            CHARACTER_SHADOW_REFERENCE_SIZE,
            CHARACTER_SHADOW_ANCHOR_RATIO,
        )
        self.move_dir = pygame.Vector2()
        self.velocity = pygame.Vector2()
        self.acceleration = pygame.Vector2()
        self.interacting = False
        self.attack_requested = False
        self.special_attack_requested = False
        self.attack_direction = pygame.Vector2(PLAYER_ATTACK_INITIAL_DIRECTION)
        self.special_attack_direction = pygame.Vector2(PLAYER_ATTACK_INITIAL_DIRECTION)
        self.requested_attack_direction: pygame.Vector2 | None = None
        self.requested_attack_target: pygame.Vector2 | None = None
        self.base_move_speed = float(PLAYER_SPEED)
        self.base_attack_damage = float(self.BASE_ATTACK_DAMAGE)
        self.base_attack_speed = float(PLAYER_ATTACK_SPEED)
        self.base_attack_radius = float(PLAYER_ATTACK_RADIUS)
        self.base_attack_half_angle = PLAYER_ATTACK_HALF_ANGLE
        self.crit_chance = PLAYER_CRIT_CHANCE
        self.crit_multiplier = PLAYER_CRIT_MULTIPLIER
        self.attack_area_upgrade_multiplier = 1.0
        self.damage_upgrade_count = 0
        self.attack_speed_upgrade_count = 0
        self.attack_radius_upgrade_count = 0
        self.sword_arc_upgrade_count = 0
        self.new_sword_unlocked = False
        self.conditioning_unlocked = False
        self.warrior_branch: str | None = None
        self.sword_spin_unlocked = False
        self.kinetic_conversion_unlocked = False
        self.well_equipped_soldiers_unlocked = False
        self.heavier_sword_unlocked = False
        self.energy_core_unlocked = False
        self.elite_soldiers_unlocked = False
        self.reinforcement_spawn_upgrade_count = 0
        self.reinforcement_power_upgrade_count = 0
        self.whistle_target: pygame.Vector2 | None = None
        self.acceleration_multiplier = 1.0
        self.attack_spin_count = 1
        self.special_cooldown_timer = 0.0
        self.special_attack_timer = 0.0
        self.special_combo_ready = False
        self.special_dash_remaining = 0.0
        self.special_hit_enemies: set[Enemy] = set()
        self.reset_combat_stats()
        self.attack_cooldown_timer = 0.0
        self.attack_animation_timer = 0.0
        self.attack_animation_time = PLAYER_ATTACK_ANIMATION_TIME
        self.attack_hit_enemies: set[Enemy] = set()
        self.attack_is_critical = False
        self.damage_events: list[tuple[tuple[int, int], float, bool]] = []
        self.combat_quest_events: list[str] = []
        self.is_dead = False
        self.death_animation_elapsed = 0.0
        self.temporary_buffs: dict[str, tuple[float, float]] = {}
        self.facing = "down"
        self.animation_state = "idle"
        self.animation_elapsed = 0.0
        self.animations = self.load_animations()
        self.update_animation(0.0)
        self.level = PLAYER_START_LEVEL
        self.xp = 0
        self.xpmax = self.calculate_xpmax()
        self.xp_gain_multiplier = 1.0
        self.mobility_ability: str | None = None
        self.mobility_cooldown = 0.0
        self.dash_remaining = 0.0
        self.dash_direction = pygame.Vector2()
        self.pending_portal_target: pygame.Vector2 | None = None
        self.enemies_stick_to_player = False
        self.boss_damage_reduction = 0.0

    def calculate_xpmax(self) -> int:
        completed_levels = max(0, self.level - PLAYER_START_LEVEL)
        return (
            PLAYER_XP_BASE
            + completed_levels * PLAYER_XP_GROWTH_BASE
            + completed_levels * (completed_levels - 1) * PLAYER_XP_GROWTH_STEP // 2
        )

    def load_animations(self):
        return load_directional_animations(
            str(self.CHARACTER_PATH),
            self.ANIMATION_SOURCE_FRAME_SIZE,
            PLAYER_SIZE,
        )

    @staticmethod
    def facing_from_vector(direction: pygame.Vector2) -> str:
        if abs(direction.y) > abs(direction.x):
            return "down" if direction.y > 0 else "up"
        return "right" if direction.x >= 0 else "left"

    def face_mouse(self, mouse_pos: tuple[int, int]) -> None:
        offset = pygame.Vector2(mouse_pos) - pygame.Vector2(self.rect.center)
        if offset.length_squared() > 0:
            self.facing = self.facing_from_vector(offset)

    def update_animation(self, dt: float) -> None:
        if self.is_dead:
            state = "death"
        elif self.attack_animation_timer > 0:
            state = "attack"
        elif self.velocity.length_squared() > 1.0:
            state = "walk"
        else:
            state = "idle"

        if state != self.animation_state:
            self.animation_state = state
            self.animation_elapsed = 0.0
        else:
            animation_dt = max(0.0, dt)
            if state == "walk":
                animation_dt *= self.velocity.length() / PLAYER_SPEED
            self.animation_elapsed += animation_dt

        sheet_direction = (
            "side" if self.facing in ("left", "right") else self.facing
        )
        frames = self.animations[(sheet_direction, state)]
        if state == "death":
            frame_index = self.animation_frame(
                self.death_animation_elapsed,
                PLAYER_DEATH_ANIMATION_TIME,
                len(frames),
            )
        elif state == "attack":
            elapsed = self.attack_animation_time - self.attack_animation_timer
            frame_index = self.animation_frame(
                elapsed,
                self.attack_animation_time,
                len(frames),
            )
        else:
            fps = (
                PLAYER_WALK_ANIMATION_FPS
                if state == "walk"
                else PLAYER_IDLE_ANIMATION_FPS
            )
            frame_index = int(self.animation_elapsed * fps) % len(frames)

        frame = frames[frame_index]
        flip_side_frame = (
            sheet_direction == "side"
            and self.facing != self.SIDE_ANIMATION_SOURCE_FACING
        )
        self.image = (
            pygame.transform.flip(frame, True, False)
            if flip_side_frame
            else frame
        )

    def add_xp(self, amount: int) -> None:
        if amount < 0:
            raise ValueError("XP cannot be negative")

        self.xp += amount * self.xp_gain_multiplier
        while self.xp >= self.xpmax:
            self.xp -= self.xpmax
            self.level += 1
            self.xpmax = self.calculate_xpmax()

    def reset_progression(self) -> None:
        """Reset battle-only XP, levels, and selected level-up bonuses."""
        self.level = PLAYER_START_LEVEL
        self.xp = 0
        self.xpmax = self.calculate_xpmax()
        self.damage_upgrade_count = 0
        self.attack_speed_upgrade_count = 0
        self.attack_radius_upgrade_count = 0
        self.sword_arc_upgrade_count = 0
        self.new_sword_unlocked = False
        self.conditioning_unlocked = False
        self.warrior_branch = None
        self.sword_spin_unlocked = False
        self.kinetic_conversion_unlocked = False
        self.well_equipped_soldiers_unlocked = False
        self.heavier_sword_unlocked = False
        self.energy_core_unlocked = False
        self.elite_soldiers_unlocked = False
        self.reinforcement_spawn_upgrade_count = 0
        self.reinforcement_power_upgrade_count = 0
        self.special_cooldown_timer = 0.0
        self.special_attack_timer = 0.0
        self.special_combo_ready = False
        self.special_dash_remaining = 0.0
        self.refresh_progression_stats()

    def reset_gear_bases(self) -> None:
        self.base_move_speed = float(PLAYER_SPEED)
        self.base_attack_damage = float(self.BASE_ATTACK_DAMAGE)
        self.base_attack_speed = float(PLAYER_ATTACK_SPEED)
        self.base_attack_radius = float(PLAYER_ATTACK_RADIUS)
        self.base_attack_half_angle = PLAYER_ATTACK_HALF_ANGLE
        self.attack_area_upgrade_multiplier = 1.0
        self.crit_chance = PLAYER_CRIT_CHANCE
        self.mobility_ability = None
        self.enemies_stick_to_player = False
        self.boss_damage_reduction = 0.0

    def reset_combat_stats(self) -> None:
        """Restore active combat stats to their gear-modified bases."""
        self.move_speed = self.base_move_speed
        self.atkdmg = self.base_attack_damage
        self.attack_speed = self.base_attack_speed
        self.attack_radius = round(self.base_attack_radius)
        self.attack_half_angle = self.base_attack_half_angle
        self.attack_animation_time = PLAYER_ATTACK_ANIMATION_TIME
        self.acceleration_multiplier = 1.0
        self.attack_spin_count = 1

    def refresh_progression_stats(self) -> None:
        """Rebuild current stats from gear bases and selected XP upgrades."""
        self.reset_combat_stats()
        if self.HERO_ID == "warrior":
            self.atkdmg *= WARRIOR_LEVEL_DAMAGE_MULTIPLIER ** self.damage_upgrade_count
            self.attack_speed *= (
                WARRIOR_LEVEL_ATTACK_SPEED_MULTIPLIER
                ** self.attack_speed_upgrade_count
            )
        else:
            self.atkdmg += (
                self.damage_upgrade_count
                * self.BASE_ATTACK_DAMAGE
                * LEVEL_UP_DAMAGE_INCREASE
            )
            self.attack_speed *= (
                LEVEL_UP_BUFFER_MULTIPLIER ** self.attack_speed_upgrade_count
            )
        if self.HERO_ID == "warrior":
            self.attack_radius = round(
                self.attack_radius
                * WARRIOR_LEVEL_SIZE_MULTIPLIER
                ** self.attack_radius_upgrade_count
            )
            self.attack_half_angle = min(
                math.pi,
                self.attack_half_angle
                * WARRIOR_LEVEL_SIZE_MULTIPLIER
                ** self.sword_arc_upgrade_count,
            )
        else:
            radius_increase = round(
                PLAYER_ATTACK_RADIUS
                * LEVEL_UP_RADIUS_INCREASE
                * self.attack_area_upgrade_multiplier
            )
            self.attack_radius += self.attack_radius_upgrade_count * radius_increase
            arc_increase = (
                PLAYER_ATTACK_HALF_ANGLE
                * LEVEL_UP_ARC_INCREASE
                * self.attack_area_upgrade_multiplier
            )
            self.attack_half_angle = min(
                math.pi,
                self.attack_half_angle + self.sword_arc_upgrade_count * arc_increase,
            )
        if self.new_sword_unlocked:
            self.atkdmg *= WARRIOR_NEW_SWORD_DAMAGE_MULTIPLIER
            self.attack_radius = round(
                self.attack_radius * WARRIOR_NEW_SWORD_SIZE_MULTIPLIER
            )
            self.attack_half_angle = min(
                math.pi,
                self.attack_half_angle * WARRIOR_NEW_SWORD_SIZE_MULTIPLIER,
            )
        if self.conditioning_unlocked:
            self.move_speed *= WARRIOR_CONDITIONING_MOVE_MULTIPLIER
            self.attack_speed /= WARRIOR_CONDITIONING_ATTACK_RATE_MULTIPLIER
        if self.sword_spin_unlocked:
            self.attack_half_angle = math.pi
            self.attack_radius = round(
                self.attack_radius * WARRIOR_SWORD_SPIN_SIZE_MULTIPLIER
            )
            self.attack_animation_time *= WARRIOR_SWORD_SPIN_ANIMATION_MULTIPLIER
        if self.heavier_sword_unlocked:
            self.attack_radius = round(
                self.attack_radius * WARRIOR_HEAVY_SWORD_SIZE_MULTIPLIER
            )
            self.atkdmg *= WARRIOR_HEAVY_SWORD_DAMAGE_MULTIPLIER
            self.attack_animation_time *= WARRIOR_HEAVY_SWORD_ANIMATION_MULTIPLIER
            self.attack_spin_count = 2
        if self.kinetic_conversion_unlocked:
            self.move_speed *= WARRIOR_KINETIC_MOVE_MULTIPLIER
            self.acceleration_multiplier = WARRIOR_KINETIC_ACCELERATION_MULTIPLIER
        if self.energy_core_unlocked:
            self.move_speed *= WARRIOR_ENERGY_CORE_MOVE_MULTIPLIER
            self.attack_speed /= WARRIOR_ENERGY_CORE_ATTACK_RATE_MULTIPLIER
        for buff_type, (multiplier, remaining) in self.temporary_buffs.items():
            if remaining <= 0:
                continue
            if buff_type == "damage":
                self.atkdmg *= multiplier
            elif buff_type == "attack_speed":
                self.attack_speed /= multiplier
            elif buff_type == "move_speed":
                self.move_speed *= multiplier

    def apply_temporary_buff(
        self,
        buff_type: str,
        multiplier: float,
        duration: float,
    ) -> None:
        self.temporary_buffs[buff_type] = (multiplier, duration)
        self.refresh_progression_stats()

    def update_temporary_buffs(self, dt: float) -> None:
        expired = False
        updated = {}
        for buff_type, (multiplier, remaining) in self.temporary_buffs.items():
            new_remaining = max(0.0, remaining - dt)
            updated[buff_type] = (multiplier, new_remaining)
            expired = expired or (remaining > 0 and new_remaining == 0)
        self.temporary_buffs = updated
        if expired:
            self.refresh_progression_stats()

    def die(self) -> None:
        if self.is_dead:
            return
        self.is_dead = True
        self.death_animation_elapsed = 0.0
        self.velocity.update(0.0, 0.0)
        self.acceleration.update(0.0, 0.0)
        self.move_dir.update(0.0, 0.0)
        self.attack_requested = False
        self.animation_state = "death"
        self.animation_elapsed = 0.0
        self.update_animation(0.0)

    @property
    def death_animation_finished(self) -> bool:
        return self.death_animation_elapsed >= PLAYER_DEATH_ANIMATION_TIME

    def upgrade_damage(self) -> None:
        self.damage_upgrade_count += 1
        self.refresh_progression_stats()

    def upgrade_attack_speed(self) -> None:
        self.attack_speed_upgrade_count += 1
        self.refresh_progression_stats()

    def upgrade_attack_radius(self) -> None:
        self.attack_radius_upgrade_count += 1
        self.refresh_progression_stats()

    def upgrade_sword_arc(self) -> None:
        self.sword_arc_upgrade_count += 1
        self.refresh_progression_stats()

    def upgrade_attack_size(self) -> None:
        self.attack_radius_upgrade_count += 1
        self.sword_arc_upgrade_count += 1
        self.refresh_progression_stats()

    def upgrade_reinforcement_spawn(self) -> None:
        self.reinforcement_spawn_upgrade_count += 1

    def upgrade_reinforcement_power(self) -> None:
        self.reinforcement_power_upgrade_count += 1

    @property
    def attack_visual_frame_count(self) -> int:
        frames = max(
            PLAYER_ATTACK_FRAME_COUNT,
            round(
                PLAYER_ATTACK_FRAME_COUNT
                * self.attack_half_angle
                / PLAYER_ATTACK_HALF_ANGLE
            ),
        )
        return frames * self.attack_spin_count

    def movement_damage_multiplier(self) -> float:
        if not self.kinetic_conversion_unlocked or self.move_speed <= 0:
            return 1.0
        return 1.0 + min(1.0, self.velocity.length() / self.move_speed)

    def consume_whistle_target(self) -> pygame.Vector2 | None:
        if (
            self.warrior_branch != "whistle"
            or not self.special_attack_requested
            or self.requested_attack_target is None
        ):
            return None
        target = self.requested_attack_target.copy()
        self.special_attack_requested = False
        return target

    @staticmethod
    def obstacle_group(
        obstacles: Sprite | Iterable[Sprite] | None,
    ) -> pygame.sprite.AbstractGroup:
        if obstacles is None:
            return pygame.sprite.Group()
        if isinstance(obstacles, pygame.sprite.AbstractGroup):
            return obstacles
        if isinstance(obstacles, Sprite):
            return obstacles.collision_group
        return pygame.sprite.Group(*obstacles)

    @staticmethod
    def collision_rect(obstacle: Sprite) -> pygame.Rect:
        collision_rect = obstacle.hitbox.copy()
        if isinstance(obstacle, Tower):
            inset = min(
                PLAYER_TOWER_COLLISION_OVERLAP,
                max(0, (collision_rect.width - 1) // 2),
                max(0, (collision_rect.height - 1) // 2),
            )
            collision_rect.inflate_ip(-inset * 2, -inset * 2)
        return collision_rect

    @staticmethod
    def collide_obstacle(player: "Player", obstacle: Sprite) -> bool:
        """Pygame callback preserving tower inset and sprite hitboxes."""
        if not isinstance(obstacle, Tower):
            return collide_hitboxes(player, obstacle)
        return player.hitbox.colliderect(player.collision_rect(obstacle))

    def resolve_axis_collisions(
        self,
        obstacles: pygame.sprite.AbstractGroup,
        movement: float,
        axis: str,
    ) -> None:
        if movement == 0:
            return
        correction_budget = abs(movement)
        collided_obstacles = pygame.sprite.spritecollide(
            self,
            obstacles,
            False,
            self.collide_obstacle,
        )
        for obstacle in collided_obstacles:
            collision_rect = self.collision_rect(obstacle)
            if axis == "x":
                if movement > 0:
                    correction = collision_rect.left - self.hitbox.right
                else:
                    correction = collision_rect.right - self.hitbox.left
                correction = max(
                    -correction_budget,
                    min(correction_budget, correction),
                )
                self.pos.x += correction
                self.velocity.x = 0.0
                self.acceleration.x = 0.0
            else:
                if movement > 0:
                    correction = collision_rect.top - self.hitbox.bottom
                else:
                    correction = collision_rect.bottom - self.hitbox.top
                correction = max(
                    -correction_budget,
                    min(correction_budget, correction),
                )
                self.pos.y += correction
                self.velocity.y = 0.0
                self.acceleration.y = 0.0
            correction_budget = max(0.0, correction_budget - abs(correction))
            self.sync_rect()

    def move(
        self,
        dt: float,
        obstacles: Sprite | Iterable[Sprite] | None = None,
    ) -> None:
        if dt <= 0:
            self.acceleration.update(0.0, 0.0)
            return

        direction = (
            self.move_dir.normalize()
            if self.move_dir.length_squared() > 0
            else self.move_dir
        )
        attack_move_multiplier = (
            WARRIOR_SWORD_SPIN_MOVE_MULTIPLIER
            if self.sword_spin_unlocked and self.attack_animation_timer > 0
            else 1.0
        )
        target_velocity = direction * self.move_speed * attack_move_multiplier
        velocity_change = target_velocity - self.velocity
        rate = (
            PLAYER_ACCELERATION
            if direction.length_squared() > 0
            else PLAYER_DECELERATION
        )
        max_change = rate * self.acceleration_multiplier * dt
        previous_velocity = self.velocity.copy()
        if velocity_change.length_squared() <= max_change**2:
            self.velocity = target_velocity
        elif velocity_change.length_squared() > 0:
            self.velocity += velocity_change.normalize() * max_change

        self.acceleration = (self.velocity - previous_velocity) / dt
        movement = self.velocity * dt
        obstacle_group = self.obstacle_group(obstacles)

        self.pos.x += movement.x
        self.sync_rect()
        self.resolve_axis_collisions(obstacle_group, movement.x, "x")

        self.pos.y += movement.y
        self.sync_rect()
        self.resolve_axis_collisions(obstacle_group, movement.y, "y")

    def move_dash(
        self,
        dt: float,
        obstacles: Sprite | Iterable[Sprite] | None,
    ) -> None:
        step = min(self.dash_remaining, ROCKET_BOOTS_SPEED * dt)
        movement = self.dash_direction * step
        obstacle_group = self.obstacle_group(obstacles)
        self.velocity = self.dash_direction * ROCKET_BOOTS_SPEED
        self.pos.x += movement.x
        self.sync_rect()
        self.resolve_axis_collisions(obstacle_group, movement.x, "x")
        self.pos.y += movement.y
        self.sync_rect()
        self.resolve_axis_collisions(obstacle_group, movement.y, "y")
        self.dash_remaining = max(0.0, self.dash_remaining - step)

    def move_special_slash_dash(
        self,
        dt: float,
        obstacles: Sprite | Iterable[Sprite] | None,
    ) -> None:
        step = min(
            self.special_dash_remaining,
            WARRIOR_SPECIAL_SLASH_DASH_SPEED * dt,
        )
        direction = (
            self.special_attack_direction.normalize()
            if self.special_attack_direction.length_squared() > 0
            else pygame.Vector2(1, 0)
        )
        movement = direction * step
        obstacle_group = self.obstacle_group(obstacles)
        self.velocity = direction * WARRIOR_SPECIAL_SLASH_DASH_SPEED
        self.pos.x += movement.x
        self.sync_rect()
        self.resolve_axis_collisions(obstacle_group, movement.x, "x")
        self.pos.y += movement.y
        self.sync_rect()
        self.resolve_axis_collisions(obstacle_group, movement.y, "y")
        self.special_dash_remaining = max(
            0.0,
            self.special_dash_remaining - step,
        )
        if self.special_dash_remaining <= 0:
            self.velocity *= 0.10

    def resolve_portal(
        self,
        target: pygame.Vector2,
        obstacles: Sprite | Iterable[Sprite] | None,
    ) -> None:
        previous = self.pos.copy()
        self.rect.center = (round(target.x), round(target.y))
        self.pos.update(self.rect.topleft)
        self.clamp_to(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        obstacle_group = self.obstacle_group(obstacles)
        tower = next(
            (obstacle for obstacle in obstacle_group if isinstance(obstacle, Tower)),
            None,
        )
        for _ in range(max(SCREEN_WIDTH, SCREEN_HEIGHT) // PORTAL_RESOLVE_STEP):
            if not pygame.sprite.spritecollideany(
                self, obstacle_group, self.collide_obstacle
            ):
                self.velocity.update(0.0, 0.0)
                return
            origin = (
                tower.hitbox.center
                if tower is not None
                else (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
            )
            direction = pygame.Vector2(self.hitbox.center) - pygame.Vector2(origin)
            if direction.length_squared() == 0:
                direction.update(1.0, 0.0)
            old_pos = self.pos.copy()
            self.pos += direction.normalize() * PORTAL_RESOLVE_STEP
            self.clamp_to(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
            if self.pos == old_pos:
                break
        self.pos = previous
        self.sync_rect()

    def activate_mobility(self, mouse_position: tuple[int, int]) -> None:
        if self.mobility_cooldown > 0 or self.mobility_ability is None:
            return
        direction = pygame.Vector2(mouse_position) - pygame.Vector2(self.rect.center)
        if self.mobility_ability == "rocket" and direction.length_squared() > 0:
            self.dash_direction = direction.normalize()
            self.dash_remaining = ROCKET_BOOTS_DISTANCE
            self.mobility_cooldown = ROCKET_BOOTS_COOLDOWN
        elif self.mobility_ability == "portal":
            self.pending_portal_target = pygame.Vector2(mouse_position)
            self.mobility_cooldown = PORTAL_BOOTS_COOLDOWN

    def apply_knockback(
        self,
        direction: pygame.Vector2,
        distance: float,
        obstacles: Sprite | Iterable[Sprite] | None = None,
    ) -> None:
        if direction.length_squared() == 0 or distance <= 0:
            return
        movement = direction.normalize() * distance
        obstacle_group = self.obstacle_group(obstacles)
        self.pos.x += movement.x
        self.sync_rect()
        self.resolve_axis_collisions(obstacle_group, movement.x, "x")
        self.pos.y += movement.y
        self.sync_rect()
        self.resolve_axis_collisions(obstacle_group, movement.y, "y")
        self.clamp_to(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

    def action(self, events: list[pygame.event.Event]) -> None:
        if self.is_dead:
            return
        # Use current keyboard state for smooth movement (WASD).
        keys = pygame.key.get_pressed()
        self.move_dir.update(0.0, 0.0)
        if keys[pygame.K_a]:
            self.move_dir.x -= 1
        if keys[pygame.K_d]:
            self.move_dir.x += 1
        if keys[pygame.K_w]:
            self.move_dir.y -= 1
        if keys[pygame.K_s]:
            self.move_dir.y += 1
        self.attack_requested = False
        self.special_attack_requested = False
        self.requested_attack_direction = None
        self.requested_attack_target = None

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                self.interacting = not self.interacting
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.activate_mobility(display.mouse_position(clamp=True))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if event.pos[0] < 0 or event.pos[1] < 0:
                    continue
                offset = pygame.Vector2(event.pos) - pygame.Vector2(
                    self.rect.center
                )
                self.requested_attack_target = pygame.Vector2(event.pos)
                self.attack_requested = True
                if offset.length_squared() > 0:
                    self.requested_attack_direction = offset.normalize()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if event.pos[0] < 0 or event.pos[1] < 0:
                    continue
                offset = pygame.Vector2(event.pos) - pygame.Vector2(
                    self.rect.center
                )
                self.requested_attack_target = pygame.Vector2(event.pos)
                self.special_attack_requested = True
                if offset.length_squared() > 0:
                    self.requested_attack_direction = offset.normalize()

    def create_full_attack_sprite(self) -> pygame.sprite.Sprite:
        diameter = self.attack_radius * 2 + 1
        attack_surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        center = pygame.Vector2(self.attack_radius, self.attack_radius)
        direction_angle = math.atan2(
            self.attack_direction.y, self.attack_direction.x
        )
        total_steps = PLAYER_ATTACK_ARC_STEPS * self.attack_visual_frame_count
        points = [center]
        for step in range(total_steps + 1):
            progress = step / total_steps
            angle = (
                direction_angle
                - self.attack_half_angle
                + 2 * self.attack_half_angle * progress
            )
            points.append(
                center
                + pygame.Vector2(math.cos(angle), math.sin(angle))
                * self.attack_radius
            )

        pygame.draw.polygon(attack_surface, (255, 255, 255, 255), points)
        if self.HERO_ID == "warrior":
            # Keep the aimed sword swing while also protecting the Warrior's
            # immediate surroundings. Area upgrades still expand the outer
            # directional portion of the attack.
            pygame.draw.circle(
                attack_surface,
                (255, 255, 255, 255),
                center,
                max(1, round(self.attack_radius * 0.25)),
            )
        attack_rect = attack_surface.get_rect(center=self.rect.center)
        attack_sprite = pygame.sprite.Sprite()
        attack_sprite.image = attack_surface
        attack_sprite.rect = attack_rect
        attack_sprite.mask = pygame.mask.from_surface(attack_surface)
        return attack_sprite

    def special_slash_points(self) -> list[pygame.Vector2]:
        direction = (
            self.special_attack_direction.normalize()
            if self.special_attack_direction.length_squared() > 0
            else pygame.Vector2(1, 0)
        )
        perpendicular = pygame.Vector2(-direction.y, direction.x)
        center = pygame.Vector2(self.rect.center)
        slash_range = WARRIOR_SPECIAL_SLASH_RANGE * (
            self.attack_radius / PLAYER_ATTACK_RADIUS
        )
        return [
            center,
            center - perpendicular * (self.rect.height / 2),
            center + direction * slash_range,
        ]

    def create_special_slash_sprite(self) -> pygame.sprite.Sprite:
        points = self.special_slash_points()
        left = math.floor(min(point.x for point in points))
        top = math.floor(min(point.y for point in points))
        right = math.ceil(max(point.x for point in points))
        bottom = math.ceil(max(point.y for point in points))
        rect = pygame.Rect(left, top, max(1, right - left + 1), max(1, bottom - top + 1))
        image = pygame.Surface(rect.size, pygame.SRCALPHA)
        local_points = [(point.x - rect.left, point.y - rect.top) for point in points]
        pygame.draw.polygon(image, (255, 255, 255, 255), local_points)
        sprite = pygame.sprite.Sprite()
        sprite.image = image
        sprite.rect = rect
        sprite.mask = pygame.mask.from_surface(image)
        return sprite

    def update_special_attack(
        self,
        enemies: pygame.sprite.Group,
        dt: float,
    ) -> list[Enemy]:
        killed_enemies = []
        self.special_cooldown_timer = max(0.0, self.special_cooldown_timer - dt)
        self.special_attack_timer = max(0.0, self.special_attack_timer - dt)
        if self.warrior_branch is None:
            return killed_enemies

        if self.special_attack_requested and self.requested_attack_direction is not None:
            self.special_attack_direction = self.requested_attack_direction

        if (
            self.special_attack_requested
            and self.warrior_branch == "slash_and_dash"
            and self.special_cooldown_timer <= 1e-9
            and self.special_combo_ready
        ):
            audio.play_sound("player_attack")
            self.special_cooldown_timer = self.attack_speed * 2
            self.special_attack_timer = self.attack_animation_time
            self.special_hit_enemies.clear()
            self.special_combo_ready = False
            self.special_dash_remaining = WARRIOR_SPECIAL_SLASH_DASH_DISTANCE

        if self.warrior_branch != "slash_and_dash" or self.special_attack_timer <= 0:
            return killed_enemies
        attack_sprite = self.create_special_slash_sprite()
        for enemy in pygame.sprite.spritecollide(
            attack_sprite,
            enemies,
            False,
            pygame.sprite.collide_mask,
        ):
            if enemy in self.special_hit_enemies:
                continue
            critical = random.random() < self.crit_chance
            damage = (
                self.atkdmg
                * self.movement_damage_multiplier()
                * (self.crit_multiplier if critical else 1.0)
            )
            if self.damage_enemy(enemy, damage, critical, "right_click"):
                killed_enemies.append(enemy)
            self.special_hit_enemies.add(enemy)
        return killed_enemies

    def attack(self, enemies: pygame.sprite.Group, dt: float) -> list[Enemy]:
        killed_enemies = []
        if self.is_dead:
            return killed_enemies
        killed_enemies.extend(self.update_special_attack(enemies, dt))
        animation_was_active = self.attack_animation_timer > 0
        self.attack_cooldown_timer = max(0.0, self.attack_cooldown_timer - dt)
        self.attack_animation_timer = max(0.0, self.attack_animation_timer - dt)

        attack_started = (
            self.attack_requested and self.attack_cooldown_timer <= 1e-9
        )
        if attack_started:
            audio.play_sound("player_attack")
            if self.requested_attack_direction is not None:
                self.attack_direction = self.requested_attack_direction
            self.facing = self.facing_from_vector(self.attack_direction)
            self.attack_cooldown_timer = self.attack_speed
            self.attack_animation_timer = self.attack_animation_time
            self.attack_hit_enemies.clear()
            self.attack_is_critical = random.random() < self.crit_chance
            self.animation_state = "attack"
            self.animation_elapsed = 0.0
            self.update_animation(0.0)
            if self.warrior_branch == "slash_and_dash":
                self.special_combo_ready = True

        if not animation_was_active and not attack_started:
            return killed_enemies

        attack_sprite = self.create_full_attack_sprite()
        collided_enemies = pygame.sprite.spritecollide(
            attack_sprite,
            enemies,
            False,
            pygame.sprite.collide_mask,
        )
        for enemy in collided_enemies:
            if enemy in self.attack_hit_enemies:
                continue
            damage = self.atkdmg * self.movement_damage_multiplier() * (
                self.crit_multiplier if self.attack_is_critical else 1.0
            )
            if self.damage_enemy(enemy, damage, self.attack_is_critical):
                killed_enemies.append(enemy)
            self.attack_hit_enemies.add(enemy)

        return killed_enemies

    def damage_enemy(
        self,
        enemy: Enemy,
        damage: float,
        critical: bool = False,
        kill_tag: str | None = None,
    ) -> bool:
        """Apply hero damage and emit one floating-damage event."""
        was_alive = enemy.is_alive
        enemy.take_damage(damage)
        self.damage_events.append((enemy.rect.center, damage, critical))
        killed = was_alive and not enemy.is_alive
        if killed and kill_tag is not None:
            self.combat_quest_events.append(kill_tag)
        return killed

    def consume_combat_quest_events(self) -> list[str]:
        events = self.combat_quest_events
        self.combat_quest_events = []
        return events

    def consume_projectiles(self) -> list[pygame.sprite.Sprite]:
        return []

    def consume_damage_events(
        self,
    ) -> list[tuple[tuple[int, int], float, bool]]:
        events = self.damage_events
        self.damage_events = []
        return events

    def display_attack(self, surface: pygame.Surface) -> None:
        if self.special_attack_timer > 0 and self.warrior_branch == "slash_and_dash":
            pygame.draw.polygon(
                surface,
                WARRIOR_SPECIAL_SLASH_COLOR,
                self.special_slash_points(),
            )
        if self.attack_animation_timer <= 0:
            return

        center = pygame.Vector2(self.rect.center)
        direction_angle = math.atan2(
            self.attack_direction.y, self.attack_direction.x
        )
        elapsed = self.attack_animation_time - self.attack_animation_timer
        frame = self.animation_frame(
            elapsed,
            self.attack_animation_time,
            self.attack_visual_frame_count,
        )
        full_arc = 2 * self.attack_half_angle
        frame_arc = full_arc * self.attack_spin_count / self.attack_visual_frame_count
        frame_start = (
            direction_angle - self.attack_half_angle + frame * frame_arc
        )
        points = [center]
        arc_steps = PLAYER_ATTACK_ARC_STEPS
        for step in range(arc_steps + 1):
            progress = step / arc_steps
            angle = frame_start + frame_arc * progress
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            points.append(center + direction * self.attack_radius)

        pygame.draw.polygon(surface, PLAYER_ATTACK_COLOR, points)
        if self.HERO_ID == "warrior" and getattr(
            self,
            "show_proximity_radius",
            False,
        ):
            pygame.draw.circle(
                surface,
                PLAYER_ATTACK_COLOR,
                (round(center.x), round(center.y)),
                max(1, round(self.attack_radius * 0.25)),
                width=2,
            )

    def update(
        self,
        dt: float,
        obstacles: Sprite | Iterable[Sprite] | None = None,
        portal_obstacles: Sprite | Iterable[Sprite] | None = None,
    ) -> None:
        if self.is_dead:
            self.death_animation_elapsed = min(
                PLAYER_DEATH_ANIMATION_TIME,
                self.death_animation_elapsed + dt,
            )
            self.update_animation(dt)
            return
        self.mobility_cooldown = max(0.0, self.mobility_cooldown - dt)
        self.update_temporary_buffs(dt)
        if self.pending_portal_target is not None:
            self.resolve_portal(
                self.pending_portal_target,
                portal_obstacles if portal_obstacles is not None else obstacles,
            )
            self.pending_portal_target = None
        if self.special_dash_remaining > 0:
            self.move_special_slash_dash(dt, obstacles)
        elif self.dash_remaining > 0:
            self.move_dash(dt, obstacles)
        else:
            self.move(dt, obstacles)
        unclamped_pos = self.pos.copy()
        self.clamp_to(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
        if self.pos.x != unclamped_pos.x:
            self.velocity.x = 0.0
            self.acceleration.x = 0.0
        if self.pos.y != unclamped_pos.y:
            self.velocity.y = 0.0
            self.acceleration.y = 0.0
        self.face_mouse(display.mouse_position(clamp=True))
        self.update_animation(dt)
