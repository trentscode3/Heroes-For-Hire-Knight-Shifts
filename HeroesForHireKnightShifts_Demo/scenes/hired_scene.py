import random

import pygame

from core.settings import MENU_BG_COLOR, MENU_TEXT_COLOR, SCREEN_HEIGHT, SCREEN_WIDTH
from core.ui_font import ui_font
from .scene import Scene


class HiredScene(Scene):
    """Brief celebratory transition between hero selection and the first day."""

    music_track = "menu"
    DURATION = 2.1
    FADE_DURATION = 0.55

    def __init__(self, manager, screen: pygame.Surface, next_scene: str) -> None:
        super().__init__(manager, screen)
        self.next_scene = next_scene
        self.elapsed = 0.0
        self.title_font = ui_font(104)
        colors = ((245, 195, 65), (85, 170, 245), (235, 85, 110), (110, 215, 125))
        self.confetti = []
        for side in (-1, 1):
            origin_x = 26 if side < 0 else SCREEN_WIDTH - 26
            for _ in range(44):
                self.confetti.append(
                    {
                        "pos": pygame.Vector2(origin_x, SCREEN_HEIGHT - 20),
                        "velocity": pygame.Vector2(
                            -side * random.uniform(110, 390),
                            -random.uniform(320, 650),
                        ),
                        "color": random.choice(colors),
                        "size": random.randint(4, 9),
                    }
                )

    def finish(self) -> None:
        self.manager.change(self.next_scene)

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            self.finish()

    def on_update(self, dt: float) -> None:
        self.elapsed += dt
        for particle in self.confetti:
            particle["velocity"].y += 520 * dt
            particle["pos"] += particle["velocity"] * dt
        if self.elapsed >= self.DURATION:
            self.finish()

    def draw(self) -> None:
        self.screen.fill(MENU_BG_COLOR)
        fade = min(
            1.0,
            max(0.0, (self.DURATION - self.elapsed) / self.FADE_DURATION),
        )
        for particle in self.confetti:
            color = (*particle["color"], round(255 * fade))
            confetti = pygame.Surface(
                (particle["size"], particle["size"] * 2),
                pygame.SRCALPHA,
            )
            confetti.fill(color)
            self.screen.blit(confetti, particle["pos"])
        title = self.title_font.render("YOU'RE HIRED!", True, MENU_TEXT_COLOR)
        title.set_alpha(round(255 * fade))
        self.screen.blit(
            title,
            title.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 25)),
        )
