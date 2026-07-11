import pygame

from core.ui_font import ui_font

from core.game_state import GameState
from core.settings import (
    NIMBUS_DEBUG_RING_COLOR,
    NIMBUS_DEBUG_RING_TEXT_COLOR,
    NIMBUS_MAX_DAMAGE_MULTIPLIER,
    NIMBUS_MULTIPLIER_RING_RADIUS,
    NIMBUS_MULTIPLIER_RING_STEP,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from sprites import Nimbus
from .game_scene import GameScene, WAVES


class DebugGame(GameScene):
    """Game scene that starts and resets at a selected wave."""

    DEBUG_MODE = True

    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        start_wave_index: int,
        state: GameState,
    ) -> None:
        if not 0 <= start_wave_index < len(WAVES):
            raise ValueError(f"Invalid wave index: {start_wave_index}")
        self.start_wave_index = start_wave_index
        super().__init__(manager, screen, state)
        self.outgoing_scene_name = f"debug_outgoing_{start_wave_index}"
        self.multiplier_font = ui_font(22)

    def reset_game(self) -> None:
        super().reset_game()
        self.wave_index = self.start_wave_index
        self.spawn_plan = self.build_spawn_plan(self.wave_index)
        self.announced_wave = self.wave_index + 1
        self.multiplier_debug_enemy = None

    def oldest_visible_enemy(self):
        screen_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        return next(
            (
                enemy
                for enemy in self.enemies
                if enemy.rect.colliderect(screen_rect)
            ),
            None,
        )

    def draw_multiplier_rings(self, surface: pygame.Surface) -> None:
        if not isinstance(self.player, Nimbus):
            return
        if (
            self.multiplier_debug_enemy is None
            or self.multiplier_debug_enemy not in self.enemies
        ):
            self.multiplier_debug_enemy = self.oldest_visible_enemy()
        if self.multiplier_debug_enemy is None:
            return

        center = self.multiplier_debug_enemy.hitbox.center
        multiplier = NIMBUS_MAX_DAMAGE_MULTIPLIER
        radius = NIMBUS_MULTIPLIER_RING_RADIUS
        minimum = self.player.minimum_damage_multiplier
        while True:
            pygame.draw.circle(
                surface,
                NIMBUS_DEBUG_RING_COLOR,
                center,
                radius,
                width=2,
            )
            label = self.multiplier_font.render(
                f"x{multiplier:.2f}",
                True,
                NIMBUS_DEBUG_RING_TEXT_COLOR,
            )
            label_pos = (
                max(
                    2,
                    min(
                        SCREEN_WIDTH - label.get_width() - 2,
                        center[0] + radius - label.get_width(),
                    ),
                ),
                max(
                    2,
                    min(SCREEN_HEIGHT - label.get_height() - 2, center[1] - 12),
                ),
            )
            surface.blit(label, label_pos)
            if multiplier <= minimum:
                break
            multiplier = max(minimum, multiplier - NIMBUS_MULTIPLIER_RING_STEP)
            radius += NIMBUS_MULTIPLIER_RING_RADIUS

    def draw_world(self, surface: pygame.Surface) -> None:
        super().draw_world(surface)
        self.draw_multiplier_rings(surface)
