from collections.abc import Callable

import pygame

from core.game_state import GameState
from core.settings import (
    BUTTON_FONT_SIZE,
    BUTTON_SIZE,
    MENU_BG_COLOR,
    MENU_TEXT_COLOR,
    PROMOTION_COLORS,
    SCENE_TITLE_FONT_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from core.ui_font import ui_font
from .button import Button
from .detail_panel import wrap_text
from .scene import Scene


class PromotionsScene(Scene):
    music_track = "menu"

    HEROES = (
        ("warrior", "Warrior"),
        ("robin_hood", "Robin Hood"),
        ("nimbus", "Nimbus"),
    )

    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        state: GameState,
        back_action: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(manager, screen)
        self.state = state
        self.back_action = back_action or (
            lambda: self.manager.change("main_menu")
        )
        self.title_font = ui_font(SCENE_TITLE_FONT_SIZE)
        self.hero_font = ui_font(32)
        self.tier_font = ui_font(25)
        self.quest_font = ui_font(23)
        back_rect = pygame.Rect(0, 0, *BUTTON_SIZE)
        back_rect.midbottom = (SCREEN_WIDTH / 2, SCREEN_HEIGHT - 24)
        self.back_button = Button(
            back_rect,
            "Back",
            ui_font(BUTTON_FONT_SIZE),
            self.back_action,
        )

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back_action()
        else:
            self.back_button.handle_event(event)

    def draw_badge(self, center: tuple[int, int], color) -> None:
        x, y = center
        ribbon_color = tuple(max(0, channel - 45) for channel in color)
        pygame.draw.polygon(
            self.screen,
            ribbon_color,
            (
                (x - 42, y + 30),
                (x - 18, y + 95),
                (x, y + 64),
                (x + 18, y + 95),
                (x + 42, y + 30),
            ),
        )
        pygame.draw.circle(self.screen, color, (x, y), 66)
        pygame.draw.circle(self.screen, (235, 235, 235), (x, y), 66, 4)
        star_points = []
        for index in range(10):
            radius = 26 if index % 2 == 0 else 12
            direction = pygame.Vector2(radius, 0).rotate(index * 36 - 90)
            star_points.append((x + round(direction.x), y + round(direction.y)))
        pygame.draw.polygon(
            self.screen,
            (245, 245, 245),
            star_points,
        )

    def draw(self) -> None:
        self.screen.fill(MENU_BG_COLOR)
        title = self.title_font.render("PROMOTIONS", True, MENU_TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH / 2, 70)))

        card_width, card_height = 350, 470
        gap = 32
        total_width = len(self.HEROES) * card_width + (len(self.HEROES) - 1) * gap
        first_left = (SCREEN_WIDTH - total_width) // 2
        for index, (hero_id, hero_name) in enumerate(self.HEROES):
            card = pygame.Rect(
                first_left + index * (card_width + gap),
                125,
                card_width,
                card_height,
            )
            pygame.draw.rect(self.screen, (32, 35, 43), card, border_radius=12)
            pygame.draw.rect(
                self.screen,
                (95, 102, 118),
                card,
                width=2,
                border_radius=12,
            )
            tier = self.state.hero_promotions.get(hero_id, "training")
            tier_name = tier.replace("_", " ").title()
            tier_label = self.tier_font.render(tier_name, True, PROMOTION_COLORS[tier])
            self.screen.blit(
                tier_label,
                tier_label.get_rect(midtop=(card.centerx, card.top + 20)),
            )
            lines = wrap_text(
                self.quest_font,
                self.state.quest_text(hero_id),
                card.width - 36,
            )
            for line_index, line in enumerate(lines):
                quest = self.quest_font.render(line, True, MENU_TEXT_COLOR)
                self.screen.blit(
                    quest,
                    quest.get_rect(
                        midtop=(card.centerx, card.top + 58 + line_index * 27)
                    ),
                )
            self.draw_badge((card.centerx, card.centery + 15), PROMOTION_COLORS[tier])
            hero = self.hero_font.render(hero_name, True, MENU_TEXT_COLOR)
            self.screen.blit(
                hero,
                hero.get_rect(midbottom=(card.centerx, card.bottom - 24)),
            )

        self.back_button.display(self.screen)
