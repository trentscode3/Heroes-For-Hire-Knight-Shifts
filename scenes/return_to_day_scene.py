import pygame

from core.game_state import GameState
from core.settings import (
    PLAYER_SIZE,
    PLAYER_SPEED,
    INCOMING_NIGHT_POP_DURATION,
    RETURN_DOOR_CLOSE_DURATION,
    RETURN_DOOR_OPEN_DURATION,
    RETURN_PLAYER_WALK_DURATION,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from sprites import create_player
from core.world_environment import (
    create_tower,
    draw_environment,
    draw_environment_border,
)
from .pause_scene import PauseScene
from .scene import Scene


SCREEN_CENTER = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)


class ReturnToDayScene(Scene):
    """Walk the hero back into the tower while night fades into day."""

    music_track = "night"

    def __init__(self, manager, screen, state: GameState, next_scene: str) -> None:
        super().__init__(manager, screen)
        self.state = state
        self.next_scene = next_scene
        self.elapsed = 0.0
        self.total_duration = (
            RETURN_DOOR_OPEN_DURATION
            + RETURN_PLAYER_WALK_DURATION
            + RETURN_DOOR_CLOSE_DURATION
        )
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
        fallback = (
            self.tower.rect.centerx - PLAYER_SIZE[0] / 2,
            self.tower.rect.bottom + 10,
        )
        self.player_start = pygame.Vector2(
            state.night_player_return_pos or fallback
        )
        self.player_front = pygame.Vector2(
            self.tower.rect.centerx - PLAYER_SIZE[0] / 2,
            self.tower.rect.bottom + 4,
        )
        self.player_end = pygame.Vector2(
            self.tower.rect.centerx - PLAYER_SIZE[0] / 2,
            self.door_rect.top - PLAYER_SIZE[1] + 18,
        )
        self.player = create_player(state.hero_id, tuple(self.player_start))
        self.state.apply_player_gear(self.player)
        self.state.apply_player_blessings(self.player)
        self.state.apply_player_knowledge(self.player)

    @staticmethod
    def ease(progress: float) -> float:
        progress = max(0.0, min(1.0, progress))
        return progress * progress * (3.0 - 2.0 * progress)

    @property
    def walk_progress(self) -> float:
        return max(
            0.0,
            min(
                1.0,
                (self.elapsed - RETURN_DOOR_OPEN_DURATION)
                / RETURN_PLAYER_WALK_DURATION,
            ),
        )

    def current_door_rect(self) -> pygame.Rect:
        if self.elapsed < RETURN_DOOR_OPEN_DURATION:
            progress = self.elapsed / RETURN_DOOR_OPEN_DURATION
        elif self.elapsed < RETURN_DOOR_OPEN_DURATION + RETURN_PLAYER_WALK_DURATION:
            progress = 1.0
        else:
            close_elapsed = (
                self.elapsed
                - RETURN_DOOR_OPEN_DURATION
                - RETURN_PLAYER_WALK_DURATION
            )
            progress = 1.0 - close_elapsed / RETURN_DOOR_CLOSE_DURATION
        height = max(0, round(self.door_rect.height * max(0.0, min(1.0, progress))))
        return pygame.Rect(
            self.door_rect.left,
            self.door_rect.bottom - height,
            self.door_rect.width,
            height,
        )

    def update_player_return(self, dt: float) -> None:
        progress = self.walk_progress
        approach_end = 0.32
        if progress < approach_end:
            approach = self.ease(progress / approach_end)
            self.player.pos = self.player_start.lerp(self.player_front, approach)
        else:
            enter = self.ease((progress - approach_end) / (1.0 - approach_end))
            self.player.pos = self.player_front.lerp(self.player_end, enter)
        self.player.sync_rect()
        if 0 < progress < 1:
            self.player.velocity.update(0.0, -PLAYER_SPEED)
            self.player.facing = "up"
        else:
            self.player.velocity.update(0.0, 0.0)
        self.player.update_animation(dt)

    def finish_return(self) -> None:
        self.state.night_player_return_pos = None
        self.manager.change(self.next_scene)

    def resume(self) -> None:
        self.set_subscene(None)

    def restart(self) -> None:
        self.state.start_new_run(self.state.hero_id)
        self.manager.change("day")

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.set_subscene(
                PauseScene(
                    self.manager,
                    self.screen,
                    self.resume,
                    self.restart,
                    self.state,
                )
            )

    def on_update(self, dt: float) -> None:
        self.elapsed += dt
        self.update_player_return(dt)
        if self.elapsed >= self.total_duration:
            self.finish_return()

    def draw(self) -> None:
        night_strength = 1.0 - min(
            1.0,
            self.elapsed / max(0.001, INCOMING_NIGHT_POP_DURATION),
        )
        draw_environment(
            self.world_surface,
            self.tower,
            night_strength,
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
        draw_environment_border(self.world_surface, night_strength)
        self.screen.blit(self.world_surface, (0, 0))
