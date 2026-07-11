import math

import pygame

from core.ui_font import ui_font

from core.settings import (
    BUTTON_FONT_SIZE,
    BUTTON_SIZE,
    BUTTON_SPACING,
    MENU_BG_COLOR,
    MENU_TEXT_COLOR,
    SCENE_TITLE_FONT_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from .button import Button
from .game_scene import WAVES
from .scene import Scene


class WaveSelectScene(Scene):
    """Dynamic debug menu with one button for every configured wave."""

    music_track = "menu"

    def __init__(self, manager, screen: pygame.Surface) -> None:
        super().__init__(manager, screen)
        self.title_font = ui_font(SCENE_TITLE_FONT_SIZE)
        button_font = ui_font(BUTTON_FONT_SIZE)

        wave_count = len(WAVES)
        max_rows = 5
        column_count = max(1, math.ceil(wave_count / max_rows))
        row_count = math.ceil(wave_count / column_count)
        total_width = (
            column_count * BUTTON_SIZE[0]
            + (column_count - 1) * BUTTON_SPACING
        )
        total_height = (
            row_count * BUTTON_SIZE[1]
            + (row_count - 1) * BUTTON_SPACING
        )
        first_center = pygame.Vector2(
            (SCREEN_WIDTH - total_width) / 2 + BUTTON_SIZE[0] / 2,
            (SCREEN_HEIGHT - total_height) / 2 + BUTTON_SIZE[1] / 2 + 40,
        )

        self.buttons = []
        for wave_index in range(wave_count):
            column = wave_index // row_count
            row = wave_index % row_count
            rect = pygame.Rect(0, 0, *BUTTON_SIZE)
            rect.center = (
                first_center.x + column * (BUTTON_SIZE[0] + BUTTON_SPACING),
                first_center.y + row * (BUTTON_SIZE[1] + BUTTON_SPACING),
            )
            self.buttons.append(
                Button(
                    rect,
                    f"Wave {wave_index + 1}",
                    button_font,
                    lambda wave_index=wave_index: self.manager.change(
                        f"debug_day_{wave_index}"
                    ),
                )
            )

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.change("main_menu")
            return
        for button in self.buttons:
            button.handle_event(event)

    def draw(self) -> None:
        self.screen.fill(MENU_BG_COLOR)
        title = self.title_font.render("DEBUG", True, MENU_TEXT_COLOR)
        self.screen.blit(
            title,
            title.get_rect(center=(SCREEN_WIDTH / 2, 100)),
        )
        for button in self.buttons:
            button.display(self.screen)
