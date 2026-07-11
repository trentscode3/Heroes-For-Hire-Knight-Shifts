import pygame

from core.display_manager import display
from core.game_state import GameState
from core.settings import (
    BUTTON_FONT_SIZE,
    BUTTON_SIZE,
    BUTTON_SPACING,
    DEMO_BUILD,
    DEBUG_BUTTON_FONT_SIZE,
    DEBUG_BUTTON_MARGIN,
    DEBUG_BUTTON_SIZE,
    GAME_TITLE,
    MENU_TEXT_COLOR,
    MENU_TITLE_FONT_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from core.ui_font import ui_font
from .button import Button
from .menu_backgrounds import draw_employment_center_background
from .scene import Scene


class MainMenuScene(Scene):
    music_track = "menu"

    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        state: GameState | None = None,
    ) -> None:
        super().__init__(manager, screen)
        self.state = state
        self.title_font = ui_font(MENU_TITLE_FONT_SIZE)
        button_font = ui_font(BUTTON_FONT_SIZE)

        labels_and_actions = []
        if self.state is not None and self.state.run_active:
            labels_and_actions.append(("Clock Back In", self.resume_game))
        labels_and_actions.extend((
            ("Submit Application", lambda: self.manager.change("hero_select")),
            ("Workplace Settings", lambda: self.manager.change("settings")),
            ("Promotions", lambda: self.manager.change("promotions")),
            ("Personnel Files", lambda: self.manager.change("save_slots")),
            ("Resign", self.manager.quit),
        ))
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

        debug_rect = pygame.Rect(0, 0, *DEBUG_BUTTON_SIZE)
        debug_rect.bottomright = (
            SCREEN_WIDTH - DEBUG_BUTTON_MARGIN,
            SCREEN_HEIGHT - DEBUG_BUTTON_MARGIN,
        )
        self.debug_button = Button(
            debug_rect,
            "Debug",
            ui_font(DEBUG_BUTTON_FONT_SIZE),
            lambda: self.manager.change("hero_select_debug"),
        )

    def resume_game(self) -> None:
        resume_scene = self.state.resume_scene if self.state is not None else "day"
        if resume_scene not in ("day", "incoming", "game", "outgoing"):
            resume_scene = "day"
        self.manager.change(resume_scene)

    def on_event(self, event: pygame.event.Event) -> None:
        for button in self.buttons:
            button.handle_event(event)
        if not DEMO_BUILD:
            self.debug_button.handle_event(event)

    def draw_button_bubble(self) -> None:
        top = min(button.rect.top for button in self.buttons)
        bottom = max(button.rect.bottom for button in self.buttons)
        bubble_rect = pygame.Rect(0, top - 28, BUTTON_SIZE[0] + 86, bottom - top + 56)
        bubble_rect.centerx = SCREEN_WIDTH // 2

        shadow = pygame.Surface(bubble_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 125), shadow.get_rect(), border_radius=28)
        self.screen.blit(shadow, bubble_rect.move(0, 8))

        bubble = pygame.Surface(bubble_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bubble, (24, 28, 34, 205), bubble.get_rect(), border_radius=28)
        pygame.draw.rect(
            bubble,
            (224, 178, 92, 170),
            bubble.get_rect(),
            width=4,
            border_radius=28,
        )
        pygame.draw.rect(
            bubble,
            (84, 58, 36, 190),
            bubble.get_rect().inflate(-16, -16),
            width=2,
            border_radius=20,
        )
        self.screen.blit(bubble, bubble_rect)

    def draw_title(self) -> None:
        title = self.title_font.render(GAME_TITLE, True, MENU_TEXT_COLOR)
        if title.get_width() > SCREEN_WIDTH - 120:
            ratio = (SCREEN_WIDTH - 120) / title.get_width()
            title = pygame.transform.smoothscale(
                title,
                (SCREEN_WIDTH - 120, max(1, round(title.get_height() * ratio))),
            )
        title_rect = title.get_rect(
            center=(SCREEN_WIDTH / 2, self.buttons[0].rect.top - 70)
        )
        title_back = title_rect.inflate(38, 18)
        pygame.draw.rect(
            self.screen,
            (0, 0, 0, 105),
            title_back.move(0, 5),
            border_radius=12,
        )
        pygame.draw.rect(self.screen, (52, 35, 24), title_back, border_radius=12)
        pygame.draw.rect(
            self.screen,
            (216, 164, 78),
            title_back,
            width=4,
            border_radius=12,
        )
        pygame.draw.rect(
            self.screen,
            (118, 77, 38),
            title_back.inflate(-14, -14),
            width=2,
            border_radius=8,
        )
        self.screen.blit(title, title_rect)

    def draw(self) -> None:
        draw_employment_center_background(self.screen, display.mouse_position(True))
        self.draw_button_bubble()
        self.draw_title()
        for button in self.buttons:
            button.display(self.screen)
        if not DEMO_BUILD:
            self.debug_button.display(self.screen)
