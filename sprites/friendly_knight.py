import random

import pygame

from core.settings import (
    FRIENDLY_KNIGHT_HOME_RADIUS,
    ELITE_FRIENDLY_KNIGHT_PALETTE,
    FRIENDLY_KNIGHT_PALETTE,
    FRIENDLY_KNIGHT_SPAWN_ANIMATION_TIME,
    FRIENDLY_KNIGHT_WANDER_INTERVAL,
    FRIENDLY_KNIGHT_WANDER_STRENGTH,
    ROCKET_BOOTS_DISTANCE,
    WARRIOR_WHISTLE_FOCUS_CRIT_BONUS,
    WARRIOR_WHISTLE_FOCUS_DURATION,
    WARRIOR_WHISTLE_FOCUS_MOVE_MULTIPLIER,
)
from .enemy import Enemy
from .friendly_learning import FriendlyKnightLearningPolicy
from .knight import Knight
from .sprite import collide_hitboxes, sprites_collide


class FriendlyKnight(Knight):
    """Tower-spawned Knight that seeks and attacks hostile enemies."""

    PALETTE = FRIENDLY_KNIGHT_PALETTE

    def __init__(self, start_pos: tuple[float, float], speed: float) -> None:
        super().__init__(start_pos, speed)
        self.damage_events: list[tuple[tuple[int, int], float]] = []
        self.received_damage_events: list[tuple[tuple[int, int], float]] = []
        self.wander_timer = 0.0
        self.wander_direction = pygame.Vector2()
        self.crit_chance = 0.0
        self.crit_multiplier = 2.0
        self.command_target: pygame.Vector2 | None = None
        self.focus_timer = 0.0
        self.mobility_ability: str | None = None
        self.boss_damage_reduction = 0.0
        self.melee_range_multiplier = 1.0
        self.active_item_timer = 1.0
        self.elite_strategy = False
        self.spawn_elapsed = FRIENDLY_KNIGHT_SPAWN_ANIMATION_TIME
        self.spawn_start = pygame.Vector2(start_pos)
        self.spawn_end = pygame.Vector2(start_pos)
        self.learning_policy: FriendlyKnightLearningPolicy | None = None
        self.rl_state: str | None = None
        self.rl_action: str | None = None
        self.rl_reward = 0.0
        self.rl_decision_timer = 0.0

    def begin_spawn(
        self,
        start_pos: tuple[float, float],
        end_pos: tuple[float, float],
    ) -> None:
        self.spawn_elapsed = 0.0
        self.spawn_start = pygame.Vector2(start_pos)
        self.spawn_end = pygame.Vector2(end_pos)
        self.pos.update(self.spawn_start)
        self.sync_rect()

    def become_elite(self) -> None:
        self.elite_strategy = True
        self.PALETTE = ELITE_FRIENDLY_KNIGHT_PALETTE
        self.animations = self.load_animations()
        self.image = self.animations[("down", "idle")][0]

    def target_score(
        self,
        enemy: Enemy,
        home: pygame.Vector2,
        strategy: str | None = None,
    ) -> float:
        distance = pygame.Vector2(self.hitbox.center).distance_to(enemy.hitbox.center)
        tower_distance = home.distance_to(enemy.hitbox.center)
        threat = max(1.0, float(enemy.damage)) / max(0.25, float(enemy.attack_speed))
        health_factor = max(1.0, float(enemy.health))
        if strategy == "weakest":
            return health_factor * 8.0 + distance * 0.35
        if strategy == "highest_threat":
            return distance * 0.45 + tower_distance * 0.15 - threat * 28.0
        if strategy == "tower_guard":
            return tower_distance * 0.75 + distance * 0.25
        if strategy == "finisher":
            return health_factor * 14.0 + distance * 0.25 - threat * 5.0
        if not self.elite_strategy:
            return distance
        return distance * 0.55 + tower_distance * 0.25 + health_factor * 0.08 - threat * 18

    def update_learning(
        self,
        dt: float,
        enemies: pygame.sprite.AbstractGroup,
        home: pygame.Vector2,
    ) -> str | None:
        if self.learning_policy is None:
            return None
        next_state = self.learning_policy.state_for(self, enemies, home)
        self.rl_decision_timer -= dt
        if self.rl_action is None or self.rl_decision_timer <= 0:
            self.learning_policy.learn(
                self.rl_state,
                self.rl_action,
                self.rl_reward,
                next_state,
            )
            self.rl_state = next_state
            self.rl_action = self.learning_policy.choose_action(next_state)
            self.rl_reward = 0.0
            self.rl_decision_timer = 0.75
        return self.rl_action

    def reward_current_strategy(self, amount: float) -> None:
        if self.learning_policy is not None and self.rl_action is not None:
            self.rl_reward += amount

    def direct_to(self, target: tuple[float, float]) -> None:
        self.command_target = pygame.Vector2(target)
        self.focus_timer = WARRIOR_WHISTLE_FOCUS_DURATION

    @property
    def focused(self) -> bool:
        return self.focus_timer > 0

    def take_damage(self, amount: float, attacker=None) -> None:
        if attacker is not None and getattr(attacker, "IS_BOSS", False):
            amount *= 1.0 - self.boss_damage_reduction
        previous_health = self.health
        super().take_damage(amount, attacker)
        health_lost = previous_health - self.health
        if health_lost > 0:
            self.received_damage_events.append((self.rect.center, health_lost))
            self.reward_current_strategy(-health_lost * 0.7)

    def attack_enemy(self, enemy: Enemy, dt: float) -> None:
        self.attack_timer += dt
        attack_delay = self.attack_speed / 4 if self.first_attack_pending else self.attack_speed
        while self.attack_timer >= attack_delay and enemy.is_alive:
            critical_chance = self.crit_chance + (
                WARRIOR_WHISTLE_FOCUS_CRIT_BONUS if self.focused else 0.0
            )
            damage = self.damage * (
                self.crit_multiplier if random.random() < critical_chance else 1.0
            )
            previous_health = enemy.health
            enemy.take_damage(damage)
            dealt = max(0.0, previous_health - enemy.health)
            self.damage_events.append((enemy.rect.center, dealt or damage))
            self.reward_current_strategy(dealt)
            if previous_health > 0 and not enemy.is_alive:
                self.reward_current_strategy(10.0)
            self.attack_timer -= attack_delay
            self.first_attack_pending = False
            attack_delay = self.attack_speed

    def consume_damage_events(self) -> list[tuple[tuple[int, int], float]]:
        events = self.damage_events
        self.damage_events = []
        return events

    def consume_received_damage_events(self) -> list[tuple[tuple[int, int], float]]:
        events = self.received_damage_events
        self.received_damage_events = []
        return events

    def update_wander(self, dt: float) -> None:
        self.wander_timer -= dt
        if self.wander_timer > 0:
            return
        self.wander_timer = random.uniform(*FRIENDLY_KNIGHT_WANDER_INTERVAL)
        self.wander_direction = pygame.Vector2(1, 0).rotate(
            random.uniform(0, 360)
        )

    def collides_with_ally(self, allies: pygame.sprite.AbstractGroup) -> bool:
        return any(
            ally is not self
            and ally.is_alive
            and sprites_collide(self, ally, collide_hitboxes)
            for ally in allies
        )

    def move_around_allies(
        self,
        dt: float,
        allies: pygame.sprite.AbstractGroup,
    ) -> None:
        direction = (
            self.move_dir.normalize()
            if self.move_dir.length_squared() > 0
            else self.move_dir
        )
        speed = self.speed * (
            WARRIOR_WHISTLE_FOCUS_MOVE_MULTIPLIER if self.focused else 1.0
        )
        movement = direction * speed * dt
        original = self.pos.copy()

        self.pos.x += movement.x
        self.sync_rect()
        if self.collides_with_ally(allies):
            self.pos.x = original.x
            self.sync_rect()

        self.pos.y += movement.y
        self.sync_rect()
        if self.collides_with_ally(allies):
            self.pos.y = original.y
            self.sync_rect()

    def update(
        self,
        dt: float,
        enemies: pygame.sprite.AbstractGroup,
        allies: pygame.sprite.AbstractGroup,
        home_center: tuple[float, float],
    ) -> None:
        if self.update_death(dt):
            self.update_animation(dt, False)
            return

        self.focus_timer = max(0.0, self.focus_timer - dt)
        if self.spawn_elapsed < FRIENDLY_KNIGHT_SPAWN_ANIMATION_TIME:
            self.spawn_elapsed = min(
                FRIENDLY_KNIGHT_SPAWN_ANIMATION_TIME,
                self.spawn_elapsed + dt,
            )
            progress = self.spawn_elapsed / FRIENDLY_KNIGHT_SPAWN_ANIMATION_TIME
            eased = 1 - (1 - progress) ** 3
            self.pos = self.spawn_start.lerp(self.spawn_end, eased)
            self.sync_rect()
            self.velocity = self.spawn_end - self.spawn_start
            self.facing = self.facing_from_vector(self.velocity)
            self.update_animation(dt, False)
            return

        self.shake_timer = max(0.0, self.shake_timer - dt)
        home = pygame.Vector2(home_center)
        strategy = self.update_learning(dt, enemies, home)
        current_center = pygame.Vector2(self.hitbox.center)
        from_home = current_center - home
        home_distance = from_home.length()
        if self.command_target is not None:
            to_command = self.command_target - current_center
            if to_command.length() > 12:
                self.move_dir = to_command.normalize()
                self.facing = self.facing_from_vector(to_command)
                self.move_around_allies(dt, allies)
                self.update_animation(dt, False)
                return
            self.command_target = None
        target = min(
            (
                enemy
                for enemy in enemies
                if enemy.is_alive
                and home.distance_to(enemy.hitbox.center)
                <= FRIENDLY_KNIGHT_HOME_RADIUS
            ),
            key=lambda enemy: self.target_score(enemy, home, strategy),
            default=None,
        )
        if target is None:
            self.update_wander(dt)
            inward = pygame.Vector2()
            soft_edge = FRIENDLY_KNIGHT_HOME_RADIUS * 0.80
            if home_distance > soft_edge and home_distance > 0:
                edge_progress = min(
                    1.0,
                    (home_distance - soft_edge)
                    / (FRIENDLY_KNIGHT_HOME_RADIUS - soft_edge),
                )
                inward = -from_home.normalize() * (1.0 + edge_progress * 2.0)
            self.move_dir = self.wander_direction + inward
            self.move_around_allies(dt, allies)
            self.attack_timer = 0.0
            self.first_attack_pending = True
            if home_distance > FRIENDLY_KNIGHT_HOME_RADIUS * 0.90:
                self.reward_current_strategy(-dt)
            self.update_animation(dt, False)
            return

        self.active_item_timer -= dt
        if self.active_item_timer <= 0:
            self.active_item_timer += 1.0
            if self.mobility_ability is not None and random.random() < 0.20:
                to_target_item = pygame.Vector2(target.hitbox.center) - pygame.Vector2(
                    self.hitbox.center
                )
                if to_target_item.length_squared() > 0:
                    distance = min(ROCKET_BOOTS_DISTANCE, to_target_item.length())
                    if self.mobility_ability == "portal":
                        distance = max(0.0, to_target_item.length() - self.rect.width)
                    self.pos += to_target_item.normalize() * distance
                    self.sync_rect()

        self.update_wander(dt)
        to_target = pygame.Vector2(target.hitbox.center) - pygame.Vector2(
            self.hitbox.center
        )
        if to_target.length_squared() > 0:
            self.facing = self.facing_from_vector(to_target)
        touching = sprites_collide(self, target, collide_hitboxes)
        if not touching and self.melee_range_multiplier > 1.0:
            extended_reach = self.rect.width * (self.melee_range_multiplier - 1.0)
            touching = to_target.length() <= extended_reach + self.rect.width * 0.5
        if touching:
            self.move_dir.update(0.0, 0.0)
            self.attack_enemy(target, dt)
        else:
            self.attack_timer = 0.0
            self.first_attack_pending = True
            target_direction = to_target.normalize()
            inward = pygame.Vector2()
            soft_edge = FRIENDLY_KNIGHT_HOME_RADIUS * 0.80
            if home_distance > soft_edge and home_distance > 0:
                inward = -from_home.normalize() * 1.5
            separation = pygame.Vector2()
            for ally in allies:
                if ally is self or not ally.is_alive:
                    continue
                away = pygame.Vector2(self.hitbox.center) - pygame.Vector2(
                    ally.hitbox.center
                )
                if 0 < away.length_squared() < self.rect.width**2:
                    separation += away.normalize()
            self.move_dir = (
                target_direction
                + self.wander_direction * FRIENDLY_KNIGHT_WANDER_STRENGTH
                + separation * 0.75
                + inward
            )
            self.move_around_allies(dt, allies)
            target_tower_distance = home.distance_to(target.hitbox.center)
            if target_tower_distance < FRIENDLY_KNIGHT_HOME_RADIUS * 0.35:
                self.reward_current_strategy(-dt * 0.5)
        self.update_animation(dt, touching)
