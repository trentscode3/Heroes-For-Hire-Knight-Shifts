import pygame

from core.ui_font import ui_font

from core.audio_manager import audio
from core.settings import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TITLE_FONT_SIZE,
    TITLE_PROMPT_FONT_SIZE,
    TITLE_TEXT_COLOR,
)
from .menu_backgrounds import draw_title_battle_background
from .scene import Scene


class TitleScene(Scene):
    music_track = "menu"

    def __init__(self, manager, screen: pygame.Surface) -> None:
        super().__init__(manager, screen)
        self.prompt_font = ui_font(TITLE_PROMPT_FONT_SIZE)

    def render_centered_text(
        self,
        text: str,
        size: int,
        center: tuple[float, float],
        max_width: int,
    ) -> pygame.Rect:
        font = ui_font(size)
        rendered = font.render(text, True, TITLE_TEXT_COLOR)
        if rendered.get_width() > max_width:
            ratio = max_width / rendered.get_width()
            rendered = pygame.transform.smoothscale(
                rendered,
                (max_width, max(1, round(rendered.get_height() * ratio))),
            )
        rect = rendered.get_rect(center=center)
        self.screen.blit(rendered, rect)
        return rect

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            audio.play_sound("menu_click")
            self.manager.change("main_menu")

    def draw(self) -> None:
        draw_title_battle_background(self.screen)
        title_plate = pygame.Rect(0, 0, 880, 178)
        title_plate.center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.23)
        shadow = pygame.Surface(title_plate.inflate(28, 28).size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 95), shadow.get_rect(), border_radius=24)
        self.screen.blit(shadow, title_plate.inflate(28, 28).move(0, 10))
        plate = pygame.Surface(title_plate.size, pygame.SRCALPHA)
        pygame.draw.rect(plate, (239, 226, 184, 232), plate.get_rect(), border_radius=20)
        pygame.draw.rect(
            plate,
            (68, 43, 25, 245),
            plate.get_rect(),
            width=6,
            border_radius=20,
        )
        pygame.draw.rect(
            plate,
            (191, 143, 63, 210),
            plate.get_rect().inflate(-18, -18),
            width=2,
            border_radius=14,
        )
        self.screen.blit(plate, title_plate)
        self.render_centered_text(
            "Heroes for Hire:",
            TITLE_FONT_SIZE,
            (SCREEN_WIDTH / 2, title_plate.centery - 35),
            title_plate.width - 60,
        )
        self.render_centered_text(
            "Knight Shifts",
            TITLE_FONT_SIZE,
            (SCREEN_WIDTH / 2, title_plate.centery + 39),
            title_plate.width - 60,
        )
        prompt = self.prompt_font.render(
            "Click anywhere to start", True, TITLE_TEXT_COLOR
        )
        prompt_bg = prompt.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.80))
        prompt_bg.inflate_ip(46, 22)
        pygame.draw.rect(self.screen, (0, 0, 0, 90), prompt_bg.move(0, 5), border_radius=12)
        pygame.draw.rect(self.screen, (236, 226, 185), prompt_bg, border_radius=12)
        pygame.draw.rect(self.screen, (68, 43, 25), prompt_bg, width=3, border_radius=12)
        self.screen.blit(
            prompt,
            prompt.get_rect(center=prompt_bg.center),
        )
