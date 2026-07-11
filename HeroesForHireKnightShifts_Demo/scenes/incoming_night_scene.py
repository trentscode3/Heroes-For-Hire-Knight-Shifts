import pygame

from core.ui_font import ui_font

from core.enemy_groups import get_enemy_group
from core.game_state import GameState
from core.settings import (
    INCOMING_DOOR_CLOSE_DURATION,
    INCOMING_NIGHT_DURATION,
    INCOMING_NIGHT_FONT_SIZE,
    INCOMING_NIGHT_POP_DURATION,
    INCOMING_PLAYER_WALK_DURATION,
    INCOMING_PLAYER_WALK_START,
    PLAYER_SIZE,
    PLAYER_SPEED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from sprites import create_player
from core.world_environment import (
    create_tower,
    draw_environment,
    draw_environment_border,
)
from .scene import Scene
from .pause_scene import PauseScene


SCREEN_CENTER = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)


class IncomingNightScene(Scene):
    """Atmospheric transition from the daytime market into nighttime combat."""

    music_track = "night"

    def __init__(self, manager, screen, state: GameState, next_scene: str) -> None:
        super().__init__(manager, screen)
        self.state = state
        self.next_scene = next_scene
        self.elapsed = 0.0
        self.text = get_enemy_group(state.current_enemy_group_id).incoming_text
        self.text_font = ui_font(INCOMING_NIGHT_FONT_SIZE)
        self.world_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.tower = create_tower(self.state, SCREEN_CENTER)
        self.door_rect = pygame.Rect(
            0,
            0,
            round(self.tower.rect.width * 0.28),
            round(self.tower.rect.height * 0.29),
        )
        self.door_rect.midbottom = (
            self.tower.rect.centerx,
            self.tower.rect.bottom,
        )
        start_pos = (
            self.tower.rect.centerx - PLAYER_SIZE[0] / 2,
            self.door_rect.top - PLAYER_SIZE[1] + 18,
        )
        self.player = create_player(state.hero_id, start_pos)
        self.state.apply_player_gear(self.player)
        self.state.apply_player_blessings(self.player)
        self.state.apply_player_knowledge(self.player)
        self.player_start = pygame.Vector2(start_pos)
        self.player_end = pygame.Vector2(
            self.tower.rect.centerx - PLAYER_SIZE[0] / 2,
            self.tower.rect.bottom + 10,
        )

    @property
    def walk_progress(self) -> float:
        return max(
            0.0,
            min(
                1.0,
                (self.elapsed - INCOMING_PLAYER_WALK_START)
                / INCOMING_PLAYER_WALK_DURATION,
            ),
        )

    @property
    def door_close_progress(self) -> float:
        close_start = INCOMING_PLAYER_WALK_START + INCOMING_PLAYER_WALK_DURATION
        return max(
            0.0,
            min(
                1.0,
                (self.elapsed - close_start) / INCOMING_DOOR_CLOSE_DURATION,
            ),
        )

    def update_player_exit(self, dt: float) -> None:
        progress = self.walk_progress
        eased = progress * progress * (3.0 - 2.0 * progress)
        self.player.pos = self.player_start.lerp(self.player_end, eased)
        self.player.sync_rect()
        if 0 < progress < 1:
            self.player.velocity.update(0.0, PLAYER_SPEED)
            self.player.facing = "down"
        else:
            self.player.velocity.update(0.0, 0.0)
        self.player.update_animation(dt)

    def finish_intro(self) -> None:
        self.state.night_player_start_pos = tuple(self.player_end)
        self.manager.change(self.next_scene)

    def on_update(self, dt: float) -> None:
        self.elapsed += dt
        self.update_player_exit(dt)
        if self.elapsed >= INCOMING_NIGHT_DURATION:
            self.finish_intro()

    def resume(self) -> None:
        self.set_subscene(None)

    def restart(self) -> None:
        self.state.start_new_run(self.state.hero_id)
        self.manager.change("day")

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.set_subscene(
                PauseScene(self.manager, self.screen, self.resume, self.restart, self.state)
            )

    def current_door_rect(self) -> pygame.Rect:
        progress = self.door_close_progress
        height = max(0, round(self.door_rect.height * (1.0 - progress)))
        return pygame.Rect(
            self.door_rect.left,
            self.door_rect.bottom - height,
            self.door_rect.width,
            height,
        )

    def draw(self) -> None:
        shader_progress = min(
            1.0,
            self.elapsed / max(0.001, INCOMING_NIGHT_POP_DURATION),
        )
        draw_environment(
            self.world_surface,
            self.tower,
            shader_progress,
            include_border=False,
        )

        door = self.current_door_rect()
        if door.height > 0:
            pygame.draw.rect(self.world_surface, (2, 3, 7), door)

        previous_clip = self.world_surface.get_clip()
        self.world_surface.set_clip(
            pygame.Rect(
                0,
                self.door_rect.top,
                SCREEN_WIDTH,
                SCREEN_HEIGHT - self.door_rect.top,
            )
        )
        self.player.display(self.world_surface)
        self.world_surface.set_clip(previous_clip)
        draw_environment_border(self.world_surface, shader_progress)
        self.screen.blit(self.world_surface, (0, 0))

        fade_in = min(1.0, self.elapsed / INCOMING_NIGHT_POP_DURATION)
        fade_out = min(1.0, max(0.0, INCOMING_NIGHT_DURATION - self.elapsed) / 0.35)
        opacity = round(255 * min(fade_in, fade_out))
        text = self.text_font.render(self.text, True, (255, 255, 255))
        max_width = SCREEN_WIDTH - 100
        if text.get_width() > max_width:
            text = pygame.transform.smoothscale(
                text,
                (
                    max_width,
                    max(1, round(text.get_height() * max_width / text.get_width())),
                ),
            )
        text.set_alpha(opacity)
        self.screen.blit(
            text,
            text.get_rect(center=(SCREEN_WIDTH / 2, 145)),
        )
