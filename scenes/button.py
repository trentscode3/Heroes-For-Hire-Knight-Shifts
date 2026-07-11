from collections.abc import Callable

import pygame

from core.audio_manager import audio
from core.display_manager import display
from core.settings import (
    BUTTON_COLOR,
    BUTTON_HOVER_COLOR,
    BUTTON_TEXT_COLOR,
)


class Button:
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        action: Callable[[], None],
        *,
        color: tuple[int, int, int] = BUTTON_COLOR,
        hover_color: tuple[int, int, int] = BUTTON_HOVER_COLOR,
        text_color: tuple[int, int, int] = BUTTON_TEXT_COLOR,
        border_color: tuple[int, int, int] | None = None,
        border_width: int = 0,
    ) -> None:
        self.rect = rect
        self.text = text
        self.font = font
        self.action = action
        self.text_offset_x = 0
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_color = border_color
        self.border_width = border_width

    def handle_event(self, event: pygame.event.Event) -> None:
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            audio.play_sound("menu_click")
            self.action()

    def display(self, surface: pygame.Surface) -> None:
        color = (
            self.hover_color
            if self.rect.collidepoint(display.mouse_position())
            else self.color
        )
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        if self.border_color is not None and self.border_width > 0:
            pygame.draw.rect(
                surface,
                self.border_color,
                self.rect,
                width=self.border_width,
                border_radius=8,
            )
        label = self.font.render(self.text, True, self.text_color)
        max_width = self.rect.width - 20
        max_height = self.rect.height - 14
        scale = min(
            1.0,
            max_width / max(1, label.get_width()),
            max_height / max(1, label.get_height()),
        )
        if scale < 1.0:
            label = pygame.transform.smoothscale(
                label,
                (
                    max(1, round(label.get_width() * scale)),
                    max(1, round(label.get_height() * scale)),
                ),
            )
        surface.blit(
            label,
            label.get_rect(
                center=(self.rect.centerx + self.text_offset_x, self.rect.centery)
            ),
        )
