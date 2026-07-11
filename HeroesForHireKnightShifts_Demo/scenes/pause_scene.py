from collections.abc import Callable

import pygame

from core.ui_font import ui_font

from core.settings import (
    BUTTON_FONT_SIZE,
    BUTTON_SIZE,
    BUTTON_SPACING,
    MENU_TEXT_COLOR,
    PAUSE_OVERLAY_COLOR,
    PAUSE_TITLE_FONT_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from .button import Button
from .scene import Scene
from .settings_scene import SettingsScene
from .promotions_scene import PromotionsScene
from core.game_state import GameState


class PauseScene(Scene):
    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        resume_action: Callable[[], None],
        restart_action: Callable[[], None],
        state: GameState,
    ) -> None:
        super().__init__(manager, screen)
        self.resume_action = resume_action
        self.restart_action = restart_action
        self.state = state
        self.title_font = ui_font(PAUSE_TITLE_FONT_SIZE)
        button_font = ui_font(BUTTON_FONT_SIZE)

        labels_and_actions = (
            ("Return to Shift", self.resume_action),
            ("Restart Shift", self.restart_action),
            ("Workplace Settings", self.open_settings),
            ("Promotions", self.open_promotions),
            ("Clock Out", lambda: self.manager.change("main_menu")),
        )
        total_height = (
            len(labels_and_actions) * BUTTON_SIZE[1]
            + (len(labels_and_actions) - 1) * BUTTON_SPACING
        )
        first_y = SCREEN_HEIGHT / 2 - total_height / 2 + 60
        self.buttons = []
        for index, (label, action) in enumerate(labels_and_actions):
            rect = pygame.Rect(0, 0, *BUTTON_SIZE)
            rect.center = (
                SCREEN_WIDTH / 2,
                first_y + index * (BUTTON_SIZE[1] + BUTTON_SPACING),
            )
            self.buttons.append(Button(rect, label, button_font, action))

    def close_nested_scene(self) -> None:
        self.set_subscene(None)

    def open_settings(self) -> None:
        self.set_subscene(
            SettingsScene(
                self.manager,
                self.screen,
                back_action=self.close_nested_scene,
            )
        )

    def open_promotions(self) -> None:
        self.set_subscene(
            PromotionsScene(
                self.manager,
                self.screen,
                self.state,
                back_action=self.close_nested_scene,
            )
        )

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.resume_action()
            return
        for button in self.buttons:
            button.handle_event(event)

    def draw(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(PAUSE_OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))

        title = self.title_font.render("PAUSED", True, MENU_TEXT_COLOR)
        title_rect = title.get_rect(
            center=(SCREEN_WIDTH / 2, self.buttons[0].rect.top - 70)
        )
        self.screen.blit(title, title_rect)
        for button in self.buttons:
            button.display(self.screen)
