from collections.abc import Callable

import pygame

from core.ui_font import ui_font

from core.settings import (
    BUTTON_FONT_SIZE,
    BUTTON_SIZE,
    BUTTON_SPACING,
    DEATH_OVERLAY_COLOR,
    DEATH_TITLE_COLOR,
    MENU_TEXT_COLOR,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from .button import Button
from .scene import Scene


class DeathScene(Scene):
    """Game-over overlay shown after the player death animation."""

    music_track = "death"
    changes_music_as_subscene = True

    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        retry_callback: Callable[[], None],
        nights_lasted: int = 0,
    ) -> None:
        super().__init__(manager, screen)
        self.title_font = ui_font(110)
        self.nights_lasted = max(0, nights_lasted)
        button_font = ui_font(BUTTON_FONT_SIZE)
        first_rect = pygame.Rect(0, 0, *BUTTON_SIZE)
        first_rect.center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100)
        menu_rect = first_rect.move(0, BUTTON_SIZE[1] + BUTTON_SPACING)
        self.buttons = (
            Button(first_rect, "Reapply", button_font, retry_callback),
            Button(
                menu_rect,
                "Employment Office",
                button_font,
                lambda: self.manager.change("main_menu"),
            ),
        )

    def on_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            button.handle_event(event)

    def draw(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(DEATH_OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))
        title = self.title_font.render("YOU'RE FIRED!", True, DEATH_TITLE_COLOR)
        self.screen.blit(
            title,
            title.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 145)),
        )
        subtitle = ui_font(34).render(
            "The tower has fallen",
            True,
            MENU_TEXT_COLOR,
        )
        self.screen.blit(
            subtitle,
            subtitle.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 55)),
        )
        nights = ui_font(30).render(
            f"Nights lasted on the job: {self.nights_lasted}",
            True,
            MENU_TEXT_COLOR,
        )
        self.screen.blit(
            nights,
            nights.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 10)),
        )
        for button in self.buttons:
            button.display(self.screen)
