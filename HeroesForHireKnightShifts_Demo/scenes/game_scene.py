import math
import random
from collections.abc import Callable

import pygame

from core.ui_font import ui_font

from core.audio_manager import audio
from core.enemy_groups import CLASSIC, get_enemy_group
from core.game_state import GameState
from items import Item
from core.save_manager import save_manager
from core.settings import (
    BG_COLOR,
    BOSS_INTRO_ENTER_DURATION,
    BOSS_INTRO_EXIT_DURATION,
    BOSS_INTRO_HOLD_DURATION,
    BOSS_INTRO_TIME_SCALE,
    BOSS_INTRO_ZOOM,
    BOSS_TITLE_CARD_BORDER_COLOR,
    BOSS_TITLE_CARD_COLOR,
    BOSS_TITLE_CARD_EDGE_FADE,
    BOSS_TITLE_CARD_SIZE,
    BOSS_TITLE_CARD_Y,
    BOSS_TITLE_FONT_SIZE,
    BOSS_TITLE_TEXT_COLOR,
    DAMAGE_INDICATOR_CRIT_COLOR,
    DAMAGE_INDICATOR_MONSTER_COLOR,
    DAMAGE_INDICATOR_PLAYER_COLOR,
    DEATH_FADE_DELAY,
    DEATH_FADE_DURATION,
    DEATH_TIME_SCALE,
    ENEMY_SIZE,
    ENEMY_SPAWN_PADDING,
    ENEMY_TRAVEL_TIME,
    ELITE_SOLDIER_ATTACK_RATE_MULTIPLIER,
    ELITE_SOLDIER_DAMAGE_MULTIPLIER,
    ELITE_SOLDIER_HEALTH_MULTIPLIER,
    ELITE_SOLDIER_SPAWN_INTERVAL,
    ELITE_SOLDIER_SPEED_MULTIPLIER,
    FIREBALL_EXPLOSION_DAMAGE_MULTIPLIER,
    FIREBALL_EXPLOSION_RADIUS,
    FRIENDLY_KNIGHT_HOME_RADIUS,
    FRIENDLY_KNIGHT_SPAWN_INTERVAL,
    FRIENDLY_KNIGHT_SPEED,
    HUD_MARGIN,
    HUD_CONTROL_COOLDOWN_COLOR,
    HUD_CONTROL_KEY_COLOR,
    HUD_CONTROL_PANEL_COLOR,
    HUD_CONTROL_READY_COLOR,
    HUD_SPACING,
    HUD_TEXT_COLOR,
    HUD_TOWER_HEALTH_BAR_BG_COLOR,
    HUD_TOWER_HEALTH_BAR_COLOR,
    HUD_TOWER_HEALTH_BAR_SIZE,
    HUD_XP_BAR_BG_COLOR,
    HUD_XP_BAR_COLOR,
    HUD_XP_BAR_SIZE,
    HUD_XP_SEGMENT_GAP,
    MONSTER_LOOT_COIN_CHANCE,
    MONSTER_LOOT_TWO_COIN_CHANCE,
    NIGHT_ENEMY_COUNT_BONUS,
    NIGHT_ENEMY_STAT_BONUS,
    NIGHT_WAVE_DURATION_GAIN,
    NIGHT_XP_REWARD_PER_TEN_NIGHTS,
    MONSTER_LOOT_DROP_CHANCE,
    ORC_DEFENSE_RANGE,
    ORC_STOMP_MAX_KNOCKBACK,
    ORC_STOMP_MIN_KNOCKBACK,
    PLAYER_START_LEVEL,
    ROBIN_HOOD_LONG_RANGE_KILL_DISTANCE,
    SCREEN_HEIGHT,
    SCREEN_SHAKE_BASE_DISTANCE,
    SCREEN_SHAKE_DAMAGE_SCALE,
    SCREEN_SHAKE_DURATION,
    SCREEN_SHAKE_FREQUENCY,
    SCREEN_SHAKE_MAX_DISTANCE,
    SCREEN_WIDTH,
    LAGER_LAUNCHER_COOLDOWN,
    LAGER_LAUNCHER_BUFF_COLORS,
    TOWER_ARCHER_ATTACK_SPEED,
    TOWER_ARCHER_DAMAGE,
    TOWER_ARCHER_RANGE,
    TURRET_ATTACK_SPEED,
    TURRET_DAMAGE,
    TURRET_RANGE,
    WAVE_ANNOUNCEMENT_COLOR,
    WAVE_ANNOUNCEMENT_DURATION,
    WAVE_ANNOUNCEMENT_FADE_DURATION,
    WAVE_ANNOUNCEMENT_FONT_SIZE,
    WAVE_BREAK_DURATION,
    WAVE_DURATION,
    WAVE_TIMER_FONT_SIZE,
    WARRIOR_REINFORCEMENT_POWER_MULTIPLIER,
    WARRIOR_REINFORCEMENT_SPAWN_MULTIPLIER,
    WARRIOR_ENERGY_CORE_PULL_SPEED,
    WARRIOR_WHISTLE_RADIUS,
    WARRIOR_WHISTLE_STUN_DURATION,
    XP_VALUES,
)
from sprites import (
    Archer,
    Arrow,
    Boss,
    DamageIndicator,
    Enemy,
    Fireball,
    FriendlyKnight,
    HeroArrow,
    LagerBeer,
    CoinPickup,
    GearPickup,
    Orc,
    Shaman,
    TowerBullet,
    XPSprite,
    create_player,
)
from sprites.sprite import collide_hitboxes, collide_rect_hitbox
from .level_up_scene import LevelUpScene
from .inventory_scene import InventoryScene
from .death_scene import DeathScene
from .pause_scene import PauseScene
from .scene import Scene
from core.user_preferences import preferences
from core.world_environment import (
    create_tower,
    draw_environment,
    draw_environment_border,
    draw_tower_with_reveal,
)


SCREEN_CENTER = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
EnemyFactory = Callable[[tuple[float, float], float], Enemy]

# Default wave shape used by the dynamic three-wave debug selector.
WAVES = CLASSIC.waves


class GameScene(Scene):
    music_track = "night"
    DEBUG_MODE = False

    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        state: GameState,
    ) -> None:
        super().__init__(manager, screen)
        self.state = state
        self.outgoing_scene_name = "outgoing"
        self.font = ui_font(30)
        self.control_font = ui_font(22)
        self.control_key_font = ui_font(19)
        self.wave_timer_font = ui_font(WAVE_TIMER_FONT_SIZE)
        self.wave_announcement_font = ui_font(WAVE_ANNOUNCEMENT_FONT_SIZE)
        self.boss_title_font = ui_font(BOSS_TITLE_FONT_SIZE)
        self.world_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.tower_layer = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.SRCALPHA,
        )
        self.tower_alpha_mask = self.tower_layer.copy()
        self.enemies = pygame.sprite.Group()
        self.friendly_knights = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.hero_projectiles = pygame.sprite.Group()
        self.xp_sprites = pygame.sprite.Group()
        self.loot_pickups = pygame.sprite.Group()
        self.lager_beers = pygame.sprite.Group()
        self.damage_indicators = pygame.sprite.Group()
        self.blood_particles = pygame.sprite.Group()
        self.player_obstacles = pygame.sprite.Group()
        self.pending_events: list[pygame.event.Event] = []
        self.reset_game()

    def reset_game(self) -> None:
        saved_snapshot = (
            self.state.night_snapshot
            if self.state.resume_scene == "game"
            else {}
        )
        self.set_subscene(None)
        self.enemies.empty()
        self.stuck_enemy_offsets: dict[Enemy, pygame.Vector2] = {}
        self.friendly_knights.empty()
        self.projectiles.empty()
        self.hero_projectiles.empty()
        self.xp_sprites.empty()
        self.loot_pickups.empty()
        self.lager_beers.empty()
        self.damage_indicators.empty()
        self.blood_particles.empty()
        self.enemy_group = get_enemy_group(self.state.current_enemy_group_id)
        self.waves = self.enemy_group.waves
        self.player = create_player(
            self.state.hero_id,
            self.state.night_player_start_pos,
        )
        self.state.night_player_start_pos = None
        self.player.show_proximity_radius = self.DEBUG_MODE
        self.state.apply_player_gear(self.player)
        self.state.apply_player_blessings(self.player)
        self.state.apply_player_knowledge(self.player)
        self.tower = create_tower(self.state, SCREEN_CENTER)
        self.player_obstacles.empty()
        self.player_obstacles.add(self.tower)
        self.wave_index = 0
        self.wave_elapsed = 0.0
        self.break_elapsed = 0.0
        self.in_wave_break = False
        self.spawned_this_wave = 0
        self.spawn_plan = self.build_spawn_plan(self.wave_index)
        self.observed_level = self.player.level
        self.pending_level_ups = 0
        self.announced_wave = 1
        self.wave_announcement_elapsed = 0.0
        self.boss_intro: dict | None = None
        self.pending_boss_intros: list[Boss] = []
        self.lager_launcher_cooldown = LAGER_LAUNCHER_COOLDOWN
        self.friendly_knight_spawn_timer = FRIENDLY_KNIGHT_SPAWN_INTERVAL
        self.death_sequence_active = False
        self.death_sequence_elapsed = 0.0
        self.nights_lasted = 0
        self.screen_shake_timer = 0.0
        self.screen_shake_intensity = 0.0
        self.awaiting_tower_return = False
        self.orc_stomp_impacts: set[Orc] = set()
        if saved_snapshot:
            self.restore_night_snapshot(saved_snapshot)

    def enemy_type_map(self) -> dict[str, type[Enemy]]:
        return {
            enemy_type.__name__: enemy_type
            for wave in self.waves
            for enemy_type, _count in wave["enemies"]
        }

    @staticmethod
    def combatant_snapshot(combatant: Enemy) -> dict:
        snapshot = {
            "type": type(combatant).__name__,
            "pos": [combatant.pos.x, combatant.pos.y],
            "speed": combatant.speed,
            "health": combatant.health,
            "max_health": combatant.max_health,
            "damage": combatant.damage,
            "attack_speed": combatant.attack_speed,
            "xp_reward": combatant.xp_reward,
            "attack_timer": combatant.attack_timer,
            "first_attack_pending": combatant.first_attack_pending,
        }
        for field in (
            "attack_cooldown",
            "attack_windup",
            "is_attacking",
            "in_attack_range",
            "sling_timer",
            "attack_cycle_timer",
            "attack_animation_elapsed",
            "first_boss_attack",
            "defense_cooldown",
        ):
            if hasattr(combatant, field):
                snapshot[field] = getattr(combatant, field)
        return snapshot

    def capture_state(self) -> None:
        if self.state.resume_scene != "game" or not self.state.run_active:
            self.state.night_snapshot.clear()
            return
        player_fields = (
            "damage_upgrade_count",
            "attack_speed_upgrade_count",
            "attack_radius_upgrade_count",
            "sword_arc_upgrade_count",
            "reinforcement_spawn_upgrade_count",
            "reinforcement_power_upgrade_count",
        )
        self.state.night_snapshot = {
            "wave_index": self.wave_index,
            "wave_elapsed": self.wave_elapsed,
            "break_elapsed": self.break_elapsed,
            "in_wave_break": self.in_wave_break,
            "spawned_this_wave": self.spawned_this_wave,
            "spawn_plan": [enemy_type.__name__ for enemy_type in self.spawn_plan],
            "announced_wave": self.announced_wave,
            "wave_announcement_elapsed": self.wave_announcement_elapsed,
            "pending_level_ups": self.pending_level_ups,
            "friendly_spawn_timer": self.friendly_knight_spawn_timer,
            "lager_launcher_cooldown": self.lager_launcher_cooldown,
            "tower_health": self.tower.health,
            "awaiting_tower_return": self.awaiting_tower_return,
            "player": {
                "pos": [self.player.pos.x, self.player.pos.y],
                "level": self.player.level,
                "xp": self.player.xp,
                **{
                    field: getattr(self.player, field)
                    for field in player_fields
                },
            },
            "enemies": [
                self.combatant_snapshot(enemy)
                for enemy in self.enemies
                if enemy.is_alive
            ],
            "friendlies": [
                self.combatant_snapshot(knight)
                for knight in self.friendly_knights
                if knight.is_alive
            ],
        }

    @staticmethod
    def restore_combatant(combatant: Enemy, data: dict) -> None:
        combatant.speed = float(data.get("speed", combatant.speed))
        combatant.max_health = float(data.get("max_health", combatant.max_health))
        combatant.health = max(
            0.0,
            min(combatant.max_health, float(data.get("health", combatant.health))),
        )
        combatant.damage = float(data.get("damage", combatant.damage))
        combatant.attack_speed = float(
            data.get("attack_speed", combatant.attack_speed)
        )
        combatant.xp_reward = int(data.get("xp_reward", combatant.xp_reward))
        combatant.attack_timer = max(0.0, float(data.get("attack_timer", 0.0)))
        combatant.first_attack_pending = bool(
            data.get("first_attack_pending", True)
        )
        for field in (
            "attack_cooldown",
            "attack_windup",
            "is_attacking",
            "in_attack_range",
            "sling_timer",
            "attack_cycle_timer",
            "attack_animation_elapsed",
            "first_boss_attack",
            "defense_cooldown",
        ):
            if field in data and hasattr(combatant, field):
                setattr(combatant, field, data[field])

    def restore_night_snapshot(self, snapshot: dict) -> None:
        self.wave_index = max(
            0,
            min(len(self.waves), int(snapshot.get("wave_index", 0))),
        )
        self.wave_elapsed = max(0.0, float(snapshot.get("wave_elapsed", 0.0)))
        self.break_elapsed = max(0.0, float(snapshot.get("break_elapsed", 0.0)))
        self.in_wave_break = bool(snapshot.get("in_wave_break", False))
        self.spawned_this_wave = max(0, int(snapshot.get("spawned_this_wave", 0)))
        enemy_types = self.enemy_type_map()
        saved_plan = [
            enemy_types[name]
            for name in snapshot.get("spawn_plan", [])
            if name in enemy_types
        ]
        if saved_plan:
            self.spawn_plan = saved_plan
        self.announced_wave = max(1, int(snapshot.get("announced_wave", 1)))
        self.wave_announcement_elapsed = max(
            0.0,
            float(snapshot.get("wave_announcement_elapsed", 0.0)),
        )
        self.pending_level_ups = max(
            0,
            int(snapshot.get("pending_level_ups", 0)),
        )
        self.friendly_knight_spawn_timer = float(
            snapshot.get("friendly_spawn_timer", FRIENDLY_KNIGHT_SPAWN_INTERVAL)
        )
        self.lager_launcher_cooldown = float(
            snapshot.get("lager_launcher_cooldown", LAGER_LAUNCHER_COOLDOWN)
        )
        self.tower.health = max(
            0.0,
            min(
                self.tower.max_health,
                float(snapshot.get("tower_health", self.tower.health)),
            ),
        )
        self.tower.refresh_health_frame()
        self.awaiting_tower_return = bool(
            snapshot.get("awaiting_tower_return", False)
        )

        player_data = snapshot.get("player", {})
        position = player_data.get("pos")
        if isinstance(position, list) and len(position) == 2:
            self.player.pos.update(float(position[0]), float(position[1]))
            self.player.sync_rect()
        for field in (
            "damage_upgrade_count",
            "attack_speed_upgrade_count",
            "attack_radius_upgrade_count",
            "sword_arc_upgrade_count",
            "reinforcement_spawn_upgrade_count",
            "reinforcement_power_upgrade_count",
        ):
            setattr(self.player, field, max(0, int(player_data.get(field, 0))))
        self.player.refresh_progression_stats()
        self.player.level = max(
            PLAYER_START_LEVEL,
            int(player_data.get("level", PLAYER_START_LEVEL)),
        )
        self.player.xpmax = self.player.calculate_xpmax()
        self.player.xp = max(
            0.0,
            min(float(player_data.get("xp", 0.0)), self.player.xpmax),
        )
        self.observed_level = self.player.level

        self.enemies.empty()
        for enemy_data in snapshot.get("enemies", []):
            enemy_type = enemy_types.get(enemy_data.get("type"))
            position = enemy_data.get("pos")
            if enemy_type is None or not isinstance(position, list) or len(position) != 2:
                continue
            enemy = enemy_type((float(position[0]), float(position[1])), 0.0)
            self.restore_combatant(enemy, enemy_data)
            self.enemies.add(enemy)

        self.friendly_knights.empty()
        for knight_data in snapshot.get("friendlies", []):
            position = knight_data.get("pos")
            if not isinstance(position, list) or len(position) != 2:
                continue
            knight = FriendlyKnight(
                (float(position[0]), float(position[1])),
                FRIENDLY_KNIGHT_SPEED,
            )
            if self.player.elite_soldiers_unlocked:
                knight.become_elite()
            if self.player.well_equipped_soldiers_unlocked:
                self.state.apply_reinforcement_gear(knight)
            self.restore_combatant(knight, knight_data)
            self.friendly_knights.add(knight)
        self.refresh_player_obstacles()
        if self.pending_level_ups > 0:
            self.show_next_level_up()

    def player_reached_tower(self) -> bool:
        return self.tower_return_zone().collidepoint(self.player.hitbox.center)

    def tower_return_zone(self) -> pygame.Rect:
        zone = pygame.Rect(0, 0, max(80, self.tower.rect.width - 24), 46)
        zone.midtop = (self.tower.rect.centerx, self.tower.rect.bottom - 8)
        return zone

    def trigger_screen_shake(self, damage: float) -> None:
        if damage <= 0 or preferences.screen_shake_strength <= 0:
            return
        added_intensity = (
            SCREEN_SHAKE_BASE_DISTANCE + damage * SCREEN_SHAKE_DAMAGE_SCALE
        )
        if self.screen_shake_timer <= 0:
            self.screen_shake_timer = SCREEN_SHAKE_DURATION
            self.screen_shake_intensity = min(
                SCREEN_SHAKE_MAX_DISTANCE,
                added_intensity,
            )
            return
        # Hits within the active window strengthen the existing shake without
        # restarting it as a separate effect.
        self.screen_shake_intensity = min(
            SCREEN_SHAKE_MAX_DISTANCE,
            self.screen_shake_intensity + added_intensity,
        )

    def update_screen_shake(self, dt: float) -> None:
        self.screen_shake_timer = max(0.0, self.screen_shake_timer - dt)
        if self.screen_shake_timer <= 0:
            self.screen_shake_intensity = 0.0

    def screen_shake_offset(self) -> pygame.Vector2:
        if self.screen_shake_timer <= 0:
            return pygame.Vector2()
        envelope = self.screen_shake_timer / SCREEN_SHAKE_DURATION
        distance = (
            self.screen_shake_intensity
            * preferences.screen_shake_strength
            * envelope
        )
        phase = self.screen_shake_timer * SCREEN_SHAKE_FREQUENCY * math.tau
        return pygame.Vector2(
            math.sin(phase) * distance,
            math.cos(phase * 1.37) * distance * 0.65,
        )

    def show_next_level_up(self) -> None:
        audio.play_sound("level_up")
        self.set_subscene(
            LevelUpScene(
                self.manager,
                self.screen,
                self.player,
                self.complete_level_up,
                self.state,
            )
        )

    def complete_level_up(self) -> None:
        self.pending_level_ups -= 1
        self.set_subscene(None)
        if self.pending_level_ups > 0:
            self.show_next_level_up()

    def resume_game(self) -> None:
        self.set_subscene(None)

    def open_inventory(self) -> None:
        self.set_subscene(
            InventoryScene(
                self.manager,
                self.screen,
                self.state,
                self.resume_game,
                self.refresh_equipment,
                self.player,
                knowledge_access_mode="night",
            )
        )

    def refresh_equipment(self) -> None:
        self.state.apply_player_gear(self.player)
        self.state.apply_player_blessings(self.player)
        self.state.apply_player_knowledge(self.player)
        self.state.apply_tower_upgrades(self.tower)
        self.refresh_player_obstacles()

    def refresh_player_obstacles(self) -> None:
        self.player_obstacles.empty()
        self.player_obstacles.add(self.tower)
        for enemy in self.enemies:
            if (
                enemy.is_alive
                and (not self.player.enemies_stick_to_player or isinstance(enemy, Boss))
                and not collide_hitboxes(self.player, enemy)
            ):
                self.player_obstacles.add(enemy)

    def update_sticky_enemies(self) -> None:
        if not self.player.enemies_stick_to_player:
            self.stuck_enemy_offsets.clear()
            return
        for enemy in pygame.sprite.spritecollide(
            self.player,
            self.enemies,
            False,
            collide_hitboxes,
        ):
            if not isinstance(enemy, Boss) and enemy.is_alive:
                self.stuck_enemy_offsets.setdefault(
                    enemy,
                    enemy.pos - self.player.pos,
                )
        for enemy, offset in list(self.stuck_enemy_offsets.items()):
            if not enemy.is_alive or enemy not in self.enemies:
                del self.stuck_enemy_offsets[enemy]
                continue
            enemy.pos = self.player.pos + offset
            enemy.sync_rect()

    def update_orc_defenses(self) -> None:
        for orc in (enemy for enemy in self.enemies if isinstance(enemy, Orc)):
            if not orc.stomp_active:
                self.orc_stomp_impacts.discard(orc)
                continue
            if not orc.stomp_impact_ready() or orc in self.orc_stomp_impacts:
                continue
            self.orc_stomp_impacts.add(orc)
            self.trigger_screen_shake(orc.damage)
            self.blood_particles.add(*orc.consume_dirt_particles())
            origin = pygame.Vector2(orc.hitbox.center)
            for target in (self.player, *self.friendly_knights):
                if not getattr(target, "is_alive", True):
                    continue
                to_target = pygame.Vector2(target.hitbox.center) - origin
                distance = to_target.length()
                if distance <= 0 or distance > ORC_DEFENSE_RANGE:
                    continue
                proximity = 1.0 - distance / ORC_DEFENSE_RANGE
                knockback = (
                    ORC_STOMP_MIN_KNOCKBACK
                    + (ORC_STOMP_MAX_KNOCKBACK - ORC_STOMP_MIN_KNOCKBACK)
                    * proximity
                )
                if target is self.player:
                    knockback *= 1.0 - self.player.boss_damage_reduction
                    obstacles = pygame.sprite.Group(
                        self.tower,
                        *(enemy for enemy in self.enemies if enemy is not orc),
                    )
                    self.player.apply_knockback(to_target, knockback, obstacles)
                else:
                    self.apply_sprite_knockback(target, to_target, knockback)

    @staticmethod
    def apply_sprite_knockback(sprite, direction: pygame.Vector2, distance: float) -> None:
        if direction.length_squared() == 0 or distance <= 0:
            return
        sprite.pos += direction.normalize() * distance
        sprite.sync_rect()
        if hasattr(sprite, "command_target"):
            sprite.command_target = None

    def effective_wave_duration(self) -> float:
        return (
            WAVE_DURATION
            + max(0, self.state.night_count - 1) * NIGHT_WAVE_DURATION_GAIN
        )

    def scaled_xp_reward(self, base_xp: int) -> int:
        scale = 1 + self.state.night_count * NIGHT_XP_REWARD_PER_TEN_NIGHTS
        return max(1, round(base_xp * scale))

    def apply_whistle_stun(self) -> None:
        origin = pygame.Vector2(self.player.hitbox.center)
        for enemy in self.enemies:
            if (
                enemy.is_alive
                and origin.distance_to(enemy.hitbox.center) <= WARRIOR_WHISTLE_RADIUS
            ):
                enemy.stun(WARRIOR_WHISTLE_STUN_DURATION)

    def apply_energy_core_pull(self, dt: float) -> None:
        if not self.player.energy_core_unlocked:
            return
        origin = pygame.Vector2(self.player.hitbox.center)
        for enemy in self.enemies:
            if not enemy.is_alive or isinstance(enemy, Boss) or enemy.stun_timer > 0:
                continue
            direction = origin - pygame.Vector2(enemy.hitbox.center)
            if direction.length_squared() == 0:
                continue
            enemy.pos += direction.normalize() * WARRIOR_ENERGY_CORE_PULL_SPEED * dt
            enemy.sync_rect()

    def collect_damage_events(self) -> None:
        for center, damage, critical in self.player.consume_damage_events():
            color = (
                DAMAGE_INDICATOR_CRIT_COLOR
                if critical
                else DAMAGE_INDICATOR_PLAYER_COLOR
            )
            self.damage_indicators.add(DamageIndicator(center, damage, color))
        for center, damage, source in self.tower.consume_damage_events():
            color = (
                DAMAGE_INDICATOR_MONSTER_COLOR
                if source == "monster"
                else DAMAGE_INDICATOR_PLAYER_COLOR
            )
            self.damage_indicators.add(DamageIndicator(center, damage, color))
            if source == "monster":
                self.trigger_screen_shake(damage)

    def update_hero_projectiles(self, dt: float) -> None:
        """Advance hero and tower projectiles and resolve collisions."""
        self.hero_projectiles.add(*self.player.consume_projectiles())
        self.hero_projectiles.update(dt)
        for projectile in list(self.hero_projectiles):
            if isinstance(projectile, HeroArrow):
                collisions = pygame.sprite.spritecollide(
                    projectile,
                    self.enemies,
                    False,
                    collide_rect_hitbox,
                )
                enemy = next(
                    (
                        candidate
                        for candidate in collisions
                        if candidate not in projectile.hit_enemies
                        and candidate.is_alive
                    ),
                    None,
                )
                if enemy is None:
                    continue
                projectile.hit_enemies.add(enemy)
                distance = projectile.origin.distance_to(enemy.hitbox.center)
                # Tower archers also use HeroArrow. Only Robin Hood's own
                # arrows use distance-based critical chance and hero quests.
                fired_by_player = projectile.source is self.player
                distance_crit = getattr(
                    projectile.source,
                    "critical_chance_for_distance",
                    None,
                )
                critical = projectile.critical
                if fired_by_player and callable(distance_crit):
                    critical = random.random() < distance_crit(distance)
                damage = projectile.base_damage * (
                    self.player.crit_multiplier if critical else 1.0
                )
                killed = self.player.damage_enemy(
                    enemy,
                    damage,
                    critical,
                )
                if killed:
                    if (
                        fired_by_player
                        and distance >= ROBIN_HOOD_LONG_RANGE_KILL_DISTANCE
                    ):
                        self.state.record_robin_long_range_kill()
                    projectile.kill_count += 1
                    if fired_by_player and projectile.kill_count > 1:
                        self.state.record_robin_collateral_kill()
                continue
            enemy = pygame.sprite.spritecollideany(
                projectile,
                self.enemies,
                collide_rect_hitbox,
            )
            if enemy is None:
                continue
            projectile.kill()
            self.player.damage_enemy(
                enemy,
                projectile.damage,
                projectile.critical,
            )

    def retry_game(self) -> None:
        self.state.start_new_run(self.state.hero_id)
        save_manager.save_profile(self.state)
        self.manager.change("day")

    def reapply(self) -> None:
        self.state.start_new_run(self.state.hero_id)
        save_manager.save_profile(self.state)
        self.manager.change("hired")

    def start_death_sequence(self) -> None:
        if self.death_sequence_active:
            return
        self.death_sequence_active = True
        self.death_sequence_elapsed = 0.0
        self.nights_lasted = self.state.night_count
        self.state.record_employment_end(self.nights_lasted)
        self.state.clear_items_after_death()
        save_manager.save_profile(self.state)
        self.player.die()

    def update_lager_launcher(self, dt: float) -> None:
        if not self.tower.lager_launcher_enabled:
            return
        wave_active = (
            self.wave_index < len(self.waves)
            and not self.in_wave_break
            and self.wave_elapsed > 0
        )
        if not wave_active:
            return
        self.lager_launcher_cooldown -= dt
        if self.lager_launcher_cooldown > 0:
            return
        buff_type = random.choice(tuple(LAGER_LAUNCHER_BUFF_COLORS))
        launch_center = self.tower.lager_launch_center()
        self.lager_beers.add(
            LagerBeer(launch_center, self.player.hitbox.center, buff_type)
        )
        self.lager_launcher_cooldown += LAGER_LAUNCHER_COOLDOWN

    def closest_enemy_in_range(self, radius: float):
        origin = pygame.Vector2(self.tower.rect.center)
        candidates = [
            enemy
            for enemy in self.enemies
            if origin.distance_to(enemy.hitbox.center) <= radius
        ]
        return min(
            candidates,
            key=lambda enemy: origin.distance_squared_to(enemy.hitbox.center),
            default=None,
        )

    def update_tower_weapons(self, dt: float) -> None:
        origin = self.tower.rect.midtop
        if self.tower.turret_enabled:
            self.tower.turret_cooldown = max(
                0.0, self.tower.turret_cooldown - dt
            )
            target = self.closest_enemy_in_range(TURRET_RANGE)
            if target is not None and self.tower.turret_cooldown <= 0:
                self.hero_projectiles.add(
                    TowerBullet(origin, target.hitbox.center, TURRET_DAMAGE, self.tower)
                )
                self.tower.turret_cooldown = TURRET_ATTACK_SPEED

        if self.tower.archer_enabled:
            self.tower.archer_cooldown = max(
                0.0, self.tower.archer_cooldown - dt
            )
            target = self.closest_enemy_in_range(TOWER_ARCHER_RANGE)
            if target is not None and self.tower.archer_cooldown <= 0:
                self.hero_projectiles.add(
                    HeroArrow(
                        origin,
                        target.hitbox.center,
                        TOWER_ARCHER_DAMAGE,
                        self.tower,
                        False,
                    )
                )
                self.tower.archer_cooldown = TOWER_ARCHER_ATTACK_SPEED

    def update_friendly_knights(self, dt: float) -> None:
        """Spawn tower Knights and advance their melee combat."""
        wave_active = (
            self.wave_index < len(self.waves)
            and not self.in_wave_break
            and self.wave_elapsed > 0
        )
        if wave_active and self.tower.is_alive:
            self.friendly_knight_spawn_timer -= dt
            while self.friendly_knight_spawn_timer <= 0:
                spawn_radius = max(self.tower.hitbox.size) / 2 + 20
                candidate = FriendlyKnight((0, 0), FRIENDLY_KNIGHT_SPEED)
                if self.player.elite_soldiers_unlocked:
                    candidate.become_elite()
                    candidate.speed *= ELITE_SOLDIER_SPEED_MULTIPLIER
                    candidate.attack_speed /= ELITE_SOLDIER_ATTACK_RATE_MULTIPLIER
                power_multiplier = (
                    WARRIOR_REINFORCEMENT_POWER_MULTIPLIER
                    ** self.player.reinforcement_power_upgrade_count
                )
                if self.player.elite_soldiers_unlocked:
                    power_multiplier *= ELITE_SOLDIER_HEALTH_MULTIPLIER
                if self.player.warrior_branch == "whistle":
                    power_multiplier *= 1.50
                candidate.max_health = round(candidate.max_health * power_multiplier)
                candidate.health = candidate.max_health
                candidate.damage *= power_multiplier
                if self.player.elite_soldiers_unlocked:
                    candidate.damage *= ELITE_SOLDIER_DAMAGE_MULTIPLIER
                if self.player.well_equipped_soldiers_unlocked:
                    self.state.apply_reinforcement_gear(candidate)
                angles = list(range(0, 360, 45))
                random.shuffle(angles)
                for angle in angles:
                    spawn_center = pygame.Vector2(self.tower.hitbox.center)
                    spawn_center += pygame.Vector2(spawn_radius, 0).rotate(angle)
                    door_pos = (
                        self.tower.rect.centerx - candidate.rect.width / 2,
                        self.tower.rect.bottom - candidate.rect.height + 12,
                    )
                    target_pos = (
                        spawn_center.x - candidate.rect.width / 2,
                        spawn_center.y - candidate.rect.height / 2,
                    )
                    candidate.pos.update(
                        target_pos[0],
                        target_pos[1],
                    )
                    candidate.sync_rect()
                    if not pygame.sprite.spritecollideany(
                        candidate,
                        self.friendly_knights,
                        collide_hitboxes,
                    ):
                        candidate.begin_spawn(door_pos, target_pos)
                        self.friendly_knights.add(candidate)
                        break
                base_interval = (
                    ELITE_SOLDIER_SPAWN_INTERVAL
                    if self.player.elite_soldiers_unlocked
                    else FRIENDLY_KNIGHT_SPAWN_INTERVAL
                )
                spawn_interval = base_interval * (
                    WARRIOR_REINFORCEMENT_SPAWN_MULTIPLIER
                    ** self.player.reinforcement_spawn_upgrade_count
                )
                self.friendly_knight_spawn_timer += spawn_interval

        for knight in list(self.friendly_knights):
            knight.update(
                dt,
                self.enemies,
                self.friendly_knights,
                self.tower.hitbox.center,
            )
            for center, damage in knight.consume_damage_events():
                self.damage_indicators.add(
                    DamageIndicator(center, damage, DAMAGE_INDICATOR_PLAYER_COLOR)
                )
            for center, damage in knight.consume_received_damage_events():
                self.damage_indicators.add(
                    DamageIndicator(center, damage, DAMAGE_INDICATOR_MONSTER_COLOR)
                )
            self.blood_particles.add(*knight.consume_blood_particles())

    def hostile_target_for(self, enemy: Enemy):
        targets = [self.tower]
        targets.extend(
            knight for knight in self.friendly_knights if knight.is_alive
        )
        return min(
            targets,
            key=lambda target: pygame.Vector2(enemy.hitbox.center).distance_squared_to(
                target.hitbox.center
            ),
        )

    def build_spawn_plan(self, wave_index: int) -> list[EnemyFactory]:
        normal_enemies = []
        bosses = []
        normal_types = []
        for enemy_type, count in self.waves[wave_index]["enemies"]:
            target = bosses if issubclass(enemy_type, Boss) else normal_enemies
            target.extend([enemy_type] * count)
            if target is normal_enemies:
                normal_types.extend([enemy_type] * count)
        if normal_types:
            count_scale = (1 + NIGHT_ENEMY_COUNT_BONUS) ** max(
                0,
                self.state.night_count - 1,
            )
            scaled_total = max(
                len(normal_enemies),
                math.ceil(len(normal_enemies) * count_scale),
            )
            choices = tuple(set(normal_types))
            while len(normal_enemies) < scaled_total:
                normal_enemies.append(random.choice(choices))
        random.shuffle(normal_enemies)
        random.shuffle(bosses)
        return normal_enemies + bosses

    def start_boss_intro(self, boss: Boss) -> None:
        audio.play_music("boss")
        card_image = None
        if boss.TITLE_CARD_PATH is not None:
            loaded_image = pygame.image.load(str(boss.TITLE_CARD_PATH))
            card_image = pygame.transform.smoothscale(
                loaded_image,
                BOSS_TITLE_CARD_SIZE,
            ).convert_alpha()
            self.fade_title_card_edges(card_image)
        self.boss_intro = {
            "boss": boss,
            "elapsed": 0.0,
            "card_image": card_image,
        }

    @staticmethod
    def fade_title_card_edges(card_image: pygame.Surface) -> None:
        """Blend a title card's hard edges into the nighttime background."""
        width, height = card_image.get_size()
        fade_width = min(
            BOSS_TITLE_CARD_EDGE_FADE,
            width // 2,
            height // 2,
        )
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        for inset in range(fade_width):
            progress = inset / max(1, fade_width - 1)
            alpha = round(255 * (1.0 - progress) ** 2)
            pygame.draw.rect(
                overlay,
                (*BG_COLOR, alpha),
                pygame.Rect(
                    inset,
                    inset,
                    width - inset * 2,
                    height - inset * 2,
                ),
                width=1,
            )
        card_image.blit(overlay, (0, 0))

    def check_pending_boss_intro(self) -> None:
        if self.boss_intro is not None:
            return

        screen_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        for boss in self.pending_boss_intros.copy():
            if not boss.alive():
                self.pending_boss_intros.remove(boss)
            elif screen_rect.contains(boss.rect):
                self.pending_boss_intros.remove(boss)
                self.start_boss_intro(boss)
                return

    def update_boss_intro(self, dt: float) -> None:
        if self.boss_intro is None:
            return
        self.boss_intro["elapsed"] += dt
        total_duration = (
            BOSS_INTRO_ENTER_DURATION
            + BOSS_INTRO_HOLD_DURATION
            + BOSS_INTRO_EXIT_DURATION
        )
        if self.boss_intro["elapsed"] >= total_duration:
            self.boss_intro = None

    def spawn_enemy(self, enemy_type: EnemyFactory) -> None:
        enemy_size = getattr(enemy_type, "SIZE", ENEMY_SIZE)
        if issubclass(enemy_type, Boss):
            spawn_center = pygame.Vector2(
                (
                    -enemy_size[0] / 2 - ENEMY_SPAWN_PADDING
                    if random.choice((True, False))
                    else SCREEN_WIDTH
                    + enemy_size[0] / 2
                    + ENEMY_SPAWN_PADDING
                ),
                random.uniform(
                    enemy_size[1] / 2,
                    SCREEN_HEIGHT - enemy_size[1] / 2,
                ),
            )
        else:
            angle = random.uniform(0.0, math.tau)
            radius_x = (
                SCREEN_WIDTH / 2 + enemy_size[0] / 2 + ENEMY_SPAWN_PADDING
            ) * math.sqrt(2)
            radius_y = (
                SCREEN_HEIGHT / 2 + enemy_size[1] / 2 + ENEMY_SPAWN_PADDING
            ) * math.sqrt(2)
            spawn_center = pygame.Vector2(
                SCREEN_CENTER[0] + radius_x * math.cos(angle),
                SCREEN_CENTER[1] + radius_y * math.sin(angle),
            )
        start_pos = (
            spawn_center.x - enemy_size[0] / 2,
            spawn_center.y - enemy_size[1] / 2,
        )

        distance = spawn_center.distance_to(self.tower.hitbox.center)
        enemy = enemy_type(start_pos, distance / ENEMY_TRAVEL_TIME)
        self.apply_wave_modifiers(enemy, self.waves[self.wave_index]["modifiers"])
        self.apply_persistent_enemy_upgrades(enemy)
        enemy.xp_reward = self.scaled_xp_reward(enemy.xp_reward)
        self.enemies.add(enemy)
        if not self.player.enemies_stick_to_player or isinstance(enemy, Boss):
            self.player_obstacles.add(enemy)
        if isinstance(enemy, Boss):
            self.pending_boss_intros.append(enemy)

    def spawn_xp_reward(
        self, center: tuple[float, float], total_xp: int
    ) -> None:
        """Split an XP reward into 8/4/2/1-value particle pickups."""
        remaining_xp = total_xp
        for value in XP_VALUES:
            count, remaining_xp = divmod(remaining_xp, value)
            for _ in range(count):
                self.xp_sprites.add(XPSprite(center, value))

        if remaining_xp != 0:
            raise ValueError(f"Could not split XP reward: {total_xp}")

    def spawn_monster_loot(self, position: tuple[float, float]) -> None:
        if random.random() >= MONSTER_LOOT_DROP_CHANCE:
            return
        loot_roll = random.random()
        if loot_roll < MONSTER_LOOT_COIN_CHANCE:
            self.loot_pickups.add(CoinPickup(position))
        elif loot_roll < MONSTER_LOOT_COIN_CHANCE + MONSTER_LOOT_TWO_COIN_CHANCE:
            self.loot_pickups.add(CoinPickup(position), CoinPickup(position))
        else:
            gear = Item.random("gear")
            if gear is not None:
                self.loot_pickups.add(GearPickup(position, gear))

    @staticmethod
    def apply_wave_modifiers(enemy: Enemy, modifiers: dict[str, float]) -> None:
        enemy.speed *= modifiers.get("speed_multiplier", 1.0)
        enemy.max_health = max(
            1, round(enemy.max_health * modifiers.get("health_multiplier", 1.0))
        )
        enemy.health = enemy.max_health
        enemy.damage = max(
            0, round(enemy.damage * modifiers.get("damage_multiplier", 1.0))
        )
        enemy.attack_speed *= modifiers.get("attack_interval_multiplier", 1.0)

    def apply_persistent_enemy_upgrades(self, enemy: Enemy) -> None:
        factor = (1 + NIGHT_ENEMY_STAT_BONUS) ** max(
            0,
            self.state.night_count - 1,
        )
        enemy.max_health = max(1, round(enemy.max_health * factor))
        enemy.health = enemy.max_health
        enemy.damage *= factor

    def update_waves(self, dt: float) -> None:
        if self.wave_index >= len(self.waves):
            return

        if self.in_wave_break:
            self.break_elapsed += dt
            if self.break_elapsed >= WAVE_BREAK_DURATION:
                self.wave_index += 1
                self.wave_elapsed = 0.0
                self.break_elapsed = 0.0
                self.in_wave_break = False
                self.spawned_this_wave = 0
                self.spawn_plan = self.build_spawn_plan(self.wave_index)
                self.announced_wave = self.wave_index + 1
                self.wave_announcement_elapsed = 0.0
            return

        self.wave_elapsed += dt
        normal_enemy_count = sum(
            1 for enemy_type in self.spawn_plan if not issubclass(enemy_type, Boss)
        )
        wave_duration = self.effective_wave_duration()
        spawn_interval = wave_duration / normal_enemy_count if normal_enemy_count else 0.0
        while self.spawned_this_wave < normal_enemy_count:
            spawn_time = self.spawned_this_wave * spawn_interval
            if self.wave_elapsed < spawn_time:
                break
            self.spawn_enemy(self.spawn_plan[self.spawned_this_wave])
            self.spawned_this_wave += 1

        # Bosses are kept at the tail and enter with the final normal spawn.
        if self.spawned_this_wave >= normal_enemy_count:
            while self.spawned_this_wave < len(self.spawn_plan):
                self.spawn_enemy(self.spawn_plan[self.spawned_this_wave])
                self.spawned_this_wave += 1

        if self.wave_elapsed >= wave_duration:
            if self.wave_index == len(self.waves) - 1:
                self.wave_index = len(self.waves)
            else:
                self.in_wave_break = True

    def on_event(self, event: pygame.event.Event) -> None:
        if self.death_sequence_active:
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_i:
            self.open_inventory()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.set_subscene(
                PauseScene(
                    self.manager,
                    self.screen,
                    self.resume_game,
                    self.retry_game,
                    self.state,
                )
            )
        else:
            self.pending_events.append(event)

    def on_update(self, dt: float) -> None:
        self.update_screen_shake(dt)
        if self.death_sequence_active:
            self.death_sequence_elapsed += dt
            self.player.update(dt * DEATH_TIME_SCALE)
            fade_finished = (
                self.death_sequence_elapsed
                >= DEATH_FADE_DELAY + DEATH_FADE_DURATION
            )
            if (
                self.player.death_animation_finished
                and fade_finished
                and self.subscene is None
            ):
                self.set_subscene(
                    DeathScene(
                        self.manager,
                        self.screen,
                        self.reapply,
                        self.nights_lasted,
                    )
                )
            return

        self.check_pending_boss_intro()
        intro_was_active = self.boss_intro is not None
        self.update_boss_intro(dt)
        game_dt = dt * BOSS_INTRO_TIME_SCALE if intro_was_active else dt

        self.wave_announcement_elapsed += game_dt
        events = self.pending_events
        self.pending_events = []
        self.player.action(events)
        whistle_target = self.player.consume_whistle_target()
        if whistle_target is not None:
            self.apply_whistle_stun()
            tower_center = pygame.Vector2(self.tower.hitbox.center)
            from_tower = whistle_target - tower_center
            if from_tower.length() > FRIENDLY_KNIGHT_HOME_RADIUS:
                whistle_target = (
                    tower_center
                    + from_tower.normalize() * FRIENDLY_KNIGHT_HOME_RADIUS
                )
            for knight in self.friendly_knights:
                if knight.is_alive:
                    knight.direct_to(whistle_target)
        # Enemies remain solid when approached, but an enemy that has moved
        # into the player is temporarily excluded so it cannot pin the player
        # against the tower. It becomes solid again after they separate.
        self.refresh_player_obstacles()
        portal_obstacles = pygame.sprite.Group(self.tower, *self.enemies)
        self.player.update(game_dt, self.player_obstacles, portal_obstacles)
        self.update_waves(game_dt)
        self.update_lager_launcher(game_dt)
        self.update_tower_weapons(game_dt)
        self.update_friendly_knights(game_dt)
        enemy_previous_positions = {
            enemy: enemy.pos.copy() for enemy in self.enemies
        }
        for enemy in self.enemies:
            target = self.hostile_target_for(enemy)
            enemy.current_target = target
            enemy.update(game_dt, target)
        self.apply_energy_core_pull(game_dt)
        self.update_sticky_enemies()
        self.update_orc_defenses()
        for enemy in self.enemies:
            if isinstance(enemy, Shaman):
                for damage, _critical in enemy.consume_pending_shots():
                    target = getattr(enemy, "current_target", self.tower)
                    projectile = Fireball(
                        enemy.projectile_origin(),
                        target.hitbox.center,
                        damage,
                        enemy,
                    )
                    projectile.intended_target = target
                    self.projectiles.add(projectile)
            elif isinstance(enemy, Archer):
                for damage, _critical in enemy.consume_pending_shots():
                    target = getattr(enemy, "current_target", self.tower)
                    projectile = Arrow(
                        enemy.projectile_origin(),
                        target.hitbox.center,
                        damage,
                        enemy,
                    )
                    projectile.intended_target = target
                    self.projectiles.add(projectile)
        self.projectiles.update(game_dt)
        hostile_targets = pygame.sprite.Group(
            self.tower,
            *(knight for knight in self.friendly_knights if knight.is_alive),
        )
        active_projectiles = pygame.sprite.Group(
            *(
                projectile
                for projectile in self.projectiles
                if getattr(projectile, "active", True)
            )
        )
        projectile_hits = pygame.sprite.groupcollide(
            active_projectiles,
            hostile_targets,
            False,
            False,
            collide_rect_hitbox,
        )
        for projectile, targets in projectile_hits.items():
            target = targets[0]
            target.take_damage(projectile.damage, projectile.source)
            if isinstance(projectile, Fireball):
                impact_center = pygame.Vector2(projectile.rect.center)
                splash_damage = projectile.damage * FIREBALL_EXPLOSION_DAMAGE_MULTIPLIER
                for splash_target in hostile_targets:
                    if splash_target is target:
                        continue
                    splash_distance = impact_center.distance_to(
                        splash_target.hitbox.center
                    )
                    if splash_distance <= FIREBALL_EXPLOSION_RADIUS:
                        splash_target.take_damage(splash_damage, projectile.source)
                projectile.explode()
            else:
                projectile.kill()
        self.player.attack(self.enemies, game_dt)
        self.update_hero_projectiles(game_dt)
        for quest_event in self.player.consume_combat_quest_events():
            if quest_event == "right_click":
                self.state.record_right_click_kill()
        self.collect_damage_events()
        for enemy in enemy_previous_positions:
            self.blood_particles.add(*enemy.consume_blood_particles())
            if isinstance(enemy, Orc):
                self.blood_particles.add(*enemy.consume_dirt_particles())
            if not enemy.is_alive and not enemy.defeat_recorded:
                self.spawn_xp_reward(enemy.rect.center, enemy.xp_reward)
                self.spawn_monster_loot(enemy.rect.center)
                self.state.record_enemy_defeat(enemy)
                enemy.defeat_recorded = True
                self.player_obstacles.remove(enemy)
        if (
            audio.current_music_key == "boss"
            and not any(isinstance(enemy, Boss) for enemy in self.enemies)
            and not self.pending_boss_intros
        ):
            audio.play_music("night")
        self.xp_sprites.update(game_dt, self.player)
        self.loot_pickups.update(game_dt, self.player, self.state)
        self.lager_beers.update(game_dt, self.player)
        self.damage_indicators.update(game_dt)
        self.blood_particles.update(game_dt)
        self.tower.update(game_dt)
        self.state.tower_health = self.tower.health

        if not self.tower.is_alive:
            self.start_death_sequence()
            return

        gained_levels = self.player.level - self.observed_level
        if gained_levels > 0:
            self.observed_level = self.player.level
            self.pending_level_ups += gained_levels
            if self.subscene is None:
                self.show_next_level_up()
            return

        if self.wave_index >= len(self.waves) and not self.enemies:
            self.awaiting_tower_return = True
            if self.player_reached_tower():
                levels_gained = self.player.level - PLAYER_START_LEVEL
                self.state.night_player_return_pos = tuple(self.player.pos)
                self.state.add_knowledge_points(1)
                self.state.finish_night(levels_gained)
                self.player.reset_progression()
                self.state.resume_scene = self.outgoing_scene_name
                self.manager.change(self.outgoing_scene_name)
            return

    def boss_intro_effect(self) -> float:
        if self.boss_intro is None:
            return 0.0

        elapsed = self.boss_intro["elapsed"]
        if elapsed < BOSS_INTRO_ENTER_DURATION:
            progress = elapsed / BOSS_INTRO_ENTER_DURATION
        elif elapsed < BOSS_INTRO_ENTER_DURATION + BOSS_INTRO_HOLD_DURATION:
            return 1.0
        else:
            exit_elapsed = (
                elapsed
                - BOSS_INTRO_ENTER_DURATION
                - BOSS_INTRO_HOLD_DURATION
            )
            progress = 1.0 - exit_elapsed / BOSS_INTRO_EXIT_DURATION

        progress = max(0.0, min(1.0, progress))
        return progress * progress * (3 - 2 * progress)

    def draw_world(self, surface: pygame.Surface) -> None:
        draw_environment(
            surface,
            self.tower,
            1.0,
            include_border=False,
            background_sprites=self.blood_particles,
            draw_tower=False,
        )
        self.lager_beers.draw(surface)

        if self.awaiting_tower_return:
            zone = pygame.Surface(self.tower_return_zone().size, pygame.SRCALPHA)
            pygame.draw.rect(zone, (110, 220, 145, 45), zone.get_rect(), border_radius=12)
            pygame.draw.rect(
                zone,
                (150, 245, 175, 170),
                zone.get_rect(),
                width=2,
                border_radius=12,
            )
            surface.blit(zone, self.tower_return_zone())

        world_sprites = [
            *self.enemies,
            *self.friendly_knights,
            self.player,
        ]
        world_sprites.sort(key=lambda sprite: sprite.rect.centery)
        tower_depth = self.tower.hitbox.centery
        behind_tower = [
            sprite
            for sprite in world_sprites
            if sprite.hitbox.centery <= tower_depth
        ]
        in_front = [
            sprite
            for sprite in world_sprites
            if sprite.hitbox.centery > tower_depth
        ]
        for sprite in behind_tower:
            sprite.display(surface)
        draw_tower_with_reveal(
            surface,
            self.tower,
            behind_tower,
            self.tower_layer,
            self.tower_alpha_mask,
        )
        for sprite in in_front:
            sprite.display(surface)

        self.projectiles.draw(surface)
        self.hero_projectiles.draw(surface)
        self.xp_sprites.draw(surface)
        self.loot_pickups.draw(surface)
        self.player.display_attack(surface)
        self.damage_indicators.draw(surface)
        draw_environment_border(surface, 1.0)

    def draw_boss_intro(self, effect: float) -> None:
        if self.boss_intro is None:
            return

        card_width, card_height = BOSS_TITLE_CARD_SIZE
        hidden_y = -card_height / 2
        card_center_y = hidden_y + (BOSS_TITLE_CARD_Y - hidden_y) * effect
        card_rect = pygame.Rect(0, 0, card_width, card_height)
        card_rect.center = (SCREEN_WIDTH / 2, card_center_y)
        card_image = self.boss_intro["card_image"]
        if card_image is not None:
            self.screen.blit(card_image, card_rect)
            return

        pygame.draw.rect(
            self.screen, BOSS_TITLE_CARD_COLOR, card_rect, border_radius=10
        )
        pygame.draw.rect(
            self.screen,
            BOSS_TITLE_CARD_BORDER_COLOR,
            card_rect,
            width=4,
            border_radius=10,
        )
        title = self.boss_title_font.render(
            self.boss_intro["boss"].TITLE,
            True,
            BOSS_TITLE_TEXT_COLOR,
        )
        self.screen.blit(title, title.get_rect(center=card_rect.center))

    def draw_control_hud(self) -> None:
        rows = [
            (
                "LMB",
                self.player.ATTACK_STYLE,
                self.player.attack_cooldown_timer,
                self.player.attack_speed,
                self.player.attack_cooldown_timer <= 1e-9,
                None,
            )
        ]
        if self.player.warrior_branch == "slash_and_dash":
            ready = (
                self.player.special_cooldown_timer <= 1e-9
                and self.player.special_combo_ready
            )
            message = None
            if self.player.special_cooldown_timer <= 1e-9 and not ready:
                message = "Use LMB first"
            rows.append(
                (
                    "RMB",
                    "Slash and Dash",
                    self.player.special_cooldown_timer,
                    self.player.attack_speed * 2,
                    ready,
                    message,
                )
            )
        elif self.player.warrior_branch == "whistle":
            rows.append(
                (
                    "RMB",
                    "Whistle: direct reinforcements",
                    0.0,
                    1.0,
                    True,
                    None,
                )
            )

        row_height = 44
        panel = pygame.Surface((320, len(rows) * row_height + 12), pygame.SRCALPHA)
        panel.fill(HUD_CONTROL_PANEL_COLOR)
        for index, (key, label, remaining, duration, ready, message) in enumerate(rows):
            y = 6 + index * row_height
            key_rect = pygame.Rect(7, y + 4, 48, 28)
            pygame.draw.rect(panel, HUD_CONTROL_KEY_COLOR, key_rect, border_radius=5)
            pygame.draw.rect(panel, (185, 190, 205), key_rect, width=2, border_radius=5)
            key_text = self.control_key_font.render(key, True, HUD_TEXT_COLOR)
            panel.blit(key_text, key_text.get_rect(center=key_rect.center))

            label_text = self.control_font.render(label, True, HUD_TEXT_COLOR)
            panel.blit(label_text, (64, y + 1))
            if message is not None:
                status_text = message
            elif ready:
                status_text = "Ready"
            else:
                status_text = f"{remaining:.1f}s"
            status = self.control_key_font.render(
                status_text,
                True,
                HUD_CONTROL_READY_COLOR if ready else (205, 210, 220),
            )
            panel.blit(status, status.get_rect(topright=(312, y + 3)))

            bar = pygame.Rect(64, y + 26, 248, 7)
            pygame.draw.rect(panel, (32, 35, 43), bar, border_radius=3)
            if ready:
                progress = 1.0
                color = HUD_CONTROL_READY_COLOR
            elif message is not None:
                progress = 0.0
                color = HUD_CONTROL_COOLDOWN_COLOR
            else:
                progress = 1.0 - min(1.0, remaining / max(0.001, duration))
                color = HUD_CONTROL_COOLDOWN_COLOR
            fill = bar.copy()
            fill.width = round(bar.width * progress)
            if fill.width > 0:
                pygame.draw.rect(panel, color, fill, border_radius=3)

        self.screen.blit(
            panel,
            (HUD_MARGIN, SCREEN_HEIGHT - HUD_MARGIN - panel.get_height()),
        )

    def draw(self) -> None:
        self.draw_world(self.world_surface)
        shake = self.screen_shake_offset()
        effect = self.boss_intro_effect()
        if self.boss_intro is not None and effect > 0:
            zoom = 1.0 + (BOSS_INTRO_ZOOM - 1.0) * effect
            scaled_size = (
                round(SCREEN_WIDTH * zoom),
                round(SCREEN_HEIGHT * zoom),
            )
            scaled_world = pygame.transform.smoothscale(
                self.world_surface, scaled_size
            )
            boss_center = pygame.Vector2(self.boss_intro["boss"].rect.center)
            boss_center.x = max(0, min(SCREEN_WIDTH, boss_center.x))
            boss_center.y = max(0, min(SCREEN_HEIGHT, boss_center.y))
            focus = pygame.Vector2(SCREEN_CENTER).lerp(boss_center, effect)
            offset = focus * (1 - zoom) + shake
            self.screen.fill(BG_COLOR)
            self.screen.blit(scaled_world, (round(offset.x), round(offset.y)))
        else:
            self.screen.fill(BG_COLOR)
            self.screen.blit(
                self.world_surface,
                (round(shake.x), round(shake.y)),
            )

        night_text = self.wave_timer_font.render(
            f"Night {self.state.night_count}", True, HUD_TEXT_COLOR
        )
        night_rect = night_text.get_rect(topleft=(HUD_MARGIN, HUD_MARGIN))
        self.screen.blit(night_text, night_rect)

        xp_bar_width, xp_bar_height = HUD_XP_BAR_SIZE
        xp_bar_rect = pygame.Rect(
            SCREEN_WIDTH - HUD_MARGIN - xp_bar_width,
            HUD_MARGIN,
            xp_bar_width,
            xp_bar_height,
        )
        pygame.draw.rect(self.screen, HUD_XP_BAR_BG_COLOR, xp_bar_rect)

        segment_width = xp_bar_width / self.player.xpmax
        for segment in range(min(self.player.xpmax, math.ceil(self.player.xp))):
            segment_left = round(xp_bar_rect.left + segment * segment_width)
            segment_right = round(
                xp_bar_rect.left + (segment + 1) * segment_width
            )
            segment_rect = pygame.Rect(
                segment_left,
                xp_bar_rect.top,
                max(1, segment_right - segment_left - HUD_XP_SEGMENT_GAP),
                xp_bar_height,
            )
            if (
                segment == int(self.player.xp)
                and not float(self.player.xp).is_integer()
            ):
                segment_rect.width = max(
                    1, round(segment_rect.width * (self.player.xp % 1))
                )
            pygame.draw.rect(self.screen, HUD_XP_BAR_COLOR, segment_rect)

        level_text = self.font.render(
            f"Level {self.player.level}", True, HUD_TEXT_COLOR
        )
        level_rect = level_text.get_rect(
            midright=(xp_bar_rect.left - HUD_SPACING, xp_bar_rect.centery)
        )
        self.screen.blit(level_text, level_rect)

        bar_width, bar_height = HUD_TOWER_HEALTH_BAR_SIZE
        health_bar_rect = pygame.Rect(
            SCREEN_WIDTH - HUD_MARGIN - bar_width,
            xp_bar_rect.bottom + HUD_SPACING,
            bar_width,
            bar_height,
        )
        pygame.draw.rect(
            self.screen, HUD_TOWER_HEALTH_BAR_BG_COLOR, health_bar_rect
        )
        health_ratio = self.tower.health / self.tower.max_health
        current_health_rect = health_bar_rect.copy()
        current_health_rect.width = round(bar_width * health_ratio)
        pygame.draw.rect(
            self.screen, HUD_TOWER_HEALTH_BAR_COLOR, current_health_rect
        )

        if self.in_wave_break:
            remaining = max(0.0, WAVE_BREAK_DURATION - self.break_elapsed)
            wave_time_label = f"Next wave: {remaining:04.1f}s"
        elif self.wave_index < len(self.waves):
            remaining = max(0.0, self.effective_wave_duration() - self.wave_elapsed)
            wave_time_label = (
                f"Wave {self.wave_index + 1}/{len(self.waves)}: {remaining:04.1f}s"
            )
        else:
            wave_time_label = (
                "Return to the tower"
                if self.awaiting_tower_return
                else f"Wave {len(self.waves)}/{len(self.waves)}: clear enemies"
            )

        wave_time = self.wave_timer_font.render(
            wave_time_label, True, HUD_TEXT_COLOR
        )
        self.screen.blit(
            wave_time,
            (HUD_MARGIN, night_rect.bottom + HUD_SPACING),
        )

        if self.wave_announcement_elapsed < WAVE_ANNOUNCEMENT_DURATION:
            elapsed = self.wave_announcement_elapsed
            fade = WAVE_ANNOUNCEMENT_FADE_DURATION
            if elapsed < fade:
                opacity = elapsed / fade
            elif elapsed > WAVE_ANNOUNCEMENT_DURATION - fade:
                opacity = (WAVE_ANNOUNCEMENT_DURATION - elapsed) / fade
            else:
                opacity = 1.0
            announcement = self.wave_announcement_font.render(
                f"WAVE {self.announced_wave}",
                True,
                WAVE_ANNOUNCEMENT_COLOR,
            )
            announcement.set_alpha(round(255 * max(0.0, min(1.0, opacity))))
            self.screen.blit(
                announcement,
                announcement.get_rect(
                    center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 3)
                ),
            )

        self.draw_control_hud()
        if self.awaiting_tower_return:
            return_text = self.wave_announcement_font.render(
                "RETURN TO THE TOWER",
                True,
                WAVE_ANNOUNCEMENT_COLOR,
            )
            self.screen.blit(
                return_text,
                return_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4)),
            )
        self.draw_boss_intro(effect)
        if self.death_sequence_active:
            fade_progress = max(
                0.0,
                min(
                    1.0,
                    (self.death_sequence_elapsed - DEATH_FADE_DELAY)
                    / DEATH_FADE_DURATION,
                ),
            )
            fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            fade.fill((0, 0, 0, round(255 * fade_progress)))
            self.screen.blit(fade, (0, 0))
