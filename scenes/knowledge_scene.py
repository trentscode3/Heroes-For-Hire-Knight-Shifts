from collections.abc import Callable

import pygame

from core.audio_manager import audio
from core.display_manager import display
from core.game_state import GameState
from core.settings import KNOWLEDGE_BOOK_PATH, MENU_TEXT_COLOR, SCREEN_HEIGHT, SCREEN_WIDTH
from core.skill_tree import (
    WARRIOR_CONNECTIONS,
    WARRIOR_SKILLS,
    draw_book_icon,
    draw_skill_icon,
)
from core.ui_font import ui_font
from core.ui_assets import load_ui_image
from .detail_panel import draw_action_button, draw_panel, wrap_text
from .scene import Scene


SKILL_DESCRIPTIONS = {
    "conditioning": "Build the stamina needed to move and attack faster.",
    "new_sword": "A better blade improves every part of the Warrior's swing.",
    "slash_and_dash": "Dash a short distance while cutting through the path ahead.",
    "whistle": "Order reinforcements toward the pointer and grant them Focus.",
    "kinetic_conversion": "Convert the Warrior's current movement speed into damage.",
    "sword_spin": "Trade mobility during attacks for complete circular coverage.",
    "well_equipped_soldiers": "Unlock gear slots for tower reinforcements.",
    "energy_core": "Emits a strong electromagnetic field.",
    "heavier_sword": "Add another slower, larger, and more damaging sword rotation.",
    "elite_soldiers": "Much stronger reinforcements help the Hero defend the castle.",
}

NODE_POSITIONS = {
    "conditioning": (0, -310),
    "new_sword": (0, -155),
    "slash_and_dash": (-190, 0),
    "whistle": (190, 0),
    "kinetic_conversion": (-300, 165),
    "sword_spin": (0, 165),
    "well_equipped_soldiers": (300, 165),
    "energy_core": (-300, 330),
    "heavier_sword": (0, 330),
    "elite_soldiers": (300, 330),
}


class KnowledgeScene(Scene):
    """Pan-and-zoom Knowledge Tree with contextual learning controls."""

    MIN_ZOOM = 0.55
    MAX_ZOOM = 1.65
    NODE_SIZE = (178, 88)

    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        state: GameState,
        close_callback: Callable[[], None],
        access_mode: str = "day",
        hero_id: str | None = None,
    ) -> None:
        super().__init__(manager, screen)
        self.state = state
        self.close_callback = close_callback
        self.access_mode = access_mode
        self.hero_id = hero_id or state.hero_id
        self.title_font = ui_font(46)
        self.heading_font = ui_font(29)
        self.body_font = ui_font(21)
        self.small_font = ui_font(18)
        self.viewport = pygame.Rect(24, 92, 850, SCREEN_HEIGHT - 116)
        self.detail_rect = pygame.Rect(896, 92, SCREEN_WIDTH - 920, 620)
        self.close_rect = pygame.Rect(SCREEN_WIDTH - 142, 24, 118, 42)
        self.learn_rect = pygame.Rect(
            self.detail_rect.left + 24,
            self.detail_rect.bottom - 72,
            self.detail_rect.width - 48,
            44,
        )
        self.camera = pygame.Vector2(0, 35)
        self.zoom = 0.90
        self.selected_skill: str | None = None
        self.dragging = False
        self.drag_distance = 0.0
        self.status = "Scroll to zoom. Drag empty space to move."

    @property
    def skills(self) -> dict[str, tuple[str, str]]:
        return {
            skill_id: (name, effect)
            for skill_id, name, effect in WARRIOR_SKILLS
        }

    def world_to_screen(self, point: tuple[float, float]) -> pygame.Vector2:
        offset = (pygame.Vector2(point) - self.camera) * self.zoom
        return pygame.Vector2(self.viewport.center) + offset

    def screen_to_world(self, point: tuple[float, float]) -> pygame.Vector2:
        offset = pygame.Vector2(point) - pygame.Vector2(self.viewport.center)
        return self.camera + offset / self.zoom

    def node_rect(self, skill_id: str) -> pygame.Rect:
        center = self.world_to_screen(NODE_POSITIONS[skill_id])
        size = (
            max(80, round(self.NODE_SIZE[0] * self.zoom)),
            max(42, round(self.NODE_SIZE[1] * self.zoom)),
        )
        rect = pygame.Rect((0, 0), size)
        rect.center = (round(center.x), round(center.y))
        return rect

    def skill_at(self, position: tuple[int, int]) -> str | None:
        if not self.viewport.collidepoint(position):
            return None
        for skill_id in NODE_POSITIONS:
            if self.node_rect(skill_id).collidepoint(position):
                return skill_id
        return None

    def skill_available(self, skill_id: str) -> bool:
        unlocked = self.state.hero_knowledge_skills(self.hero_id)
        if skill_id in unlocked:
            return False
        prerequisites = {
            "conditioning": set(),
            "new_sword": {"conditioning"},
            "slash_and_dash": {"conditioning", "new_sword"},
            "whistle": {"conditioning", "new_sword"},
            "kinetic_conversion": set(),
            "sword_spin": {"slash_and_dash"},
            "well_equipped_soldiers": {"whistle"},
            "energy_core": {"kinetic_conversion"},
            "heavier_sword": {"sword_spin"},
            "elite_soldiers": {"well_equipped_soldiers"},
        }
        if not prerequisites.get(skill_id, set()).issubset(unlocked):
            return False
        if skill_id == "kinetic_conversion" and not (
            {"slash_and_dash", "whistle"} & unlocked
        ):
            return False
        if skill_id in ("slash_and_dash", "whistle"):
            if not self.state.has_promotion("warrior", "shift_lead"):
                return False
            other_branch = "whistle" if skill_id == "slash_and_dash" else "slash_and_dash"
            branch_finished = (
                "heavier_sword" in unlocked
                if other_branch == "slash_and_dash"
                else "elite_soldiers" in unlocked
            )
            if other_branch in unlocked and not branch_finished:
                return False
        return True

    def disabled_reason(self, skill_id: str) -> str:
        unlocked = self.state.hero_knowledge_skills(self.hero_id)
        if skill_id in unlocked:
            return "This Knowledge has already been learned."
        if self.access_mode == "night":
            return "Knowledge can only be learned during the day."
        if self.access_mode == "character_select":
            return "The character screen is for previewing Knowledge only."
        if self.hero_id != "warrior":
            return "This Hero's Knowledge Tree is still being prepared."
        if not self.skill_available(skill_id):
            if (
                skill_id in ("slash_and_dash", "whistle")
                and not self.state.has_promotion("warrior", "shift_lead")
            ):
                return "Requires the Warrior Shift Lead promotion."
            return "Learn the connected Knowledge first."
        cost = self.state.knowledge_cost(skill_id)
        if self.state.hero_knowledge_points(self.hero_id) < cost:
            return f"Requires {cost} Knowledge points."
        return ""

    def can_learn(self, skill_id: str) -> bool:
        return (
            self.access_mode == "day"
            and self.hero_id == self.state.hero_id
            and self.skill_available(skill_id)
            and self.state.hero_knowledge_points(self.hero_id)
            >= self.state.knowledge_cost(skill_id)
        )

    def zoom_at(self, position: tuple[int, int], factor: float) -> None:
        if not self.viewport.collidepoint(position):
            return
        anchor = self.screen_to_world(position)
        self.zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self.zoom * factor))
        screen_offset = pygame.Vector2(position) - pygame.Vector2(
            self.viewport.center
        )
        self.camera = anchor - screen_offset / self.zoom

    def learn_selected(self) -> None:
        if self.selected_skill is None or not self.can_learn(self.selected_skill):
            return
        learned, message = self.state.unlock_knowledge(self.selected_skill)
        self.status = message
        if learned:
            audio.play_sound("level_up")

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close_callback()
            return
        if event.type == pygame.MOUSEWHEEL:
            self.zoom_at(display.mouse_position(), 1.12 ** event.y)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.close_rect.collidepoint(event.pos):
                audio.play_sound("menu_click")
                self.close_callback()
                return
            if self.learn_rect.collidepoint(event.pos):
                self.learn_selected()
                return
            skill_id = self.skill_at(event.pos)
            if skill_id is not None:
                audio.play_sound("menu_click")
                self.selected_skill = skill_id
                self.status = self.disabled_reason(skill_id)
                return
            if self.viewport.collidepoint(event.pos):
                self.dragging = True
                self.drag_distance = 0.0
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            movement = pygame.Vector2(event.rel)
            self.camera -= movement / self.zoom
            self.drag_distance += movement.length()
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

    def draw_node(self, skill_id: str) -> None:
        rect = self.node_rect(skill_id)
        if not rect.colliderect(self.viewport):
            return
        unlocked = self.state.hero_knowledge_skills(self.hero_id)
        learned = skill_id in unlocked
        available = self.skill_available(skill_id)
        selected = skill_id == self.selected_skill
        fill = (54, 126, 72) if learned else ((52, 70, 108) if available else (55, 55, 60))
        border = (135, 235, 150) if learned else ((130, 170, 230) if available else (95, 95, 102))
        if selected:
            border = (238, 202, 86)
        pygame.draw.rect(self.screen, fill, rect, border_radius=max(5, round(10 * self.zoom)))
        pygame.draw.rect(
            self.screen,
            border,
            rect,
            width=max(2, round(3 * self.zoom)),
            border_radius=max(5, round(10 * self.zoom)),
        )
        icon_size = max(24, round(38 * self.zoom))
        icon = pygame.Rect(0, 0, icon_size, icon_size)
        icon.midleft = (rect.left + max(8, round(12 * self.zoom)), rect.centery)
        draw_skill_icon(self.screen, icon, skill_id, border)
        name = self.skills[skill_id][0]
        label = self.small_font.render(name, True, MENU_TEXT_COLOR)
        max_width = rect.right - icon.right - 12
        if label.get_width() > max_width:
            height = max(1, round(label.get_height() * max_width / label.get_width()))
            label = pygame.transform.smoothscale(label, (max_width, height))
        self.screen.blit(label, label.get_rect(midleft=(icon.right + 8, rect.centery)))

    def draw_tree(self) -> None:
        draw_panel(self.screen, self.viewport, (17, 22, 31), (75, 96, 130))
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(self.viewport.inflate(-2, -2))
        for start, end in WARRIOR_CONNECTIONS:
            pygame.draw.line(
                self.screen,
                (90, 120, 165),
                self.world_to_screen(NODE_POSITIONS[start]),
                self.world_to_screen(NODE_POSITIONS[end]),
                max(2, round(4 * self.zoom)),
            )
        if self.hero_id == "warrior":
            for skill_id in NODE_POSITIONS:
                self.draw_node(skill_id)
        else:
            message = self.heading_font.render(
                "This Hero's Knowledge Tree is coming soon.",
                True,
                (175, 185, 205),
            )
            self.screen.blit(message, message.get_rect(center=self.viewport.center))
        self.screen.set_clip(previous_clip)

    def draw_detail(self) -> None:
        draw_panel(self.screen, self.detail_rect, (27, 30, 38), (105, 120, 148))
        if self.selected_skill is None:
            prompt = self.heading_font.render("Select Knowledge", True, MENU_TEXT_COLOR)
            self.screen.blit(prompt, prompt.get_rect(center=self.detail_rect.center))
            return
        name, effect = self.skills[self.selected_skill]
        title = self.heading_font.render(name, True, (238, 202, 86))
        self.screen.blit(title, (self.detail_rect.left + 24, self.detail_rect.top + 26))
        graphic = pygame.Rect(
            self.detail_rect.left + 24,
            self.detail_rect.top + 74,
            92,
            92,
        )
        pygame.draw.rect(self.screen, (42, 55, 82), graphic, border_radius=10)
        draw_skill_icon(self.screen, graphic.inflate(-22, -22), self.selected_skill)
        y = graphic.bottom + 24
        text_width = self.detail_rect.width - 48
        for line in wrap_text(
            self.body_font,
            SKILL_DESCRIPTIONS[self.selected_skill],
            text_width,
        ):
            self.screen.blit(
                self.body_font.render(line, True, MENU_TEXT_COLOR),
                (self.detail_rect.left + 24, y),
            )
            y += 24
        y += 16
        effect_heading = self.body_font.render("Effect", True, (238, 202, 86))
        self.screen.blit(effect_heading, (self.detail_rect.left + 24, y))
        y += 28
        for line in wrap_text(self.body_font, effect, text_width):
            self.screen.blit(
                self.body_font.render(line, True, (190, 208, 235)),
                (self.detail_rect.left + 24, y),
            )
            y += 24
        enabled = self.can_learn(self.selected_skill)
        if enabled:
            label = f"Learn - {self.state.knowledge_cost(self.selected_skill)} Knowledge"
        elif self.selected_skill in self.state.hero_knowledge_skills(self.hero_id):
            label = "Already Learned"
        elif self.access_mode == "night":
            label = "Unavailable During Night"
        elif self.access_mode == "character_select":
            label = "Character Preview Only"
        else:
            label = "Locked"
        draw_action_button(
            self.screen,
            self.learn_rect,
            label,
            self.small_font,
            enabled,
        )
        reason = self.disabled_reason(self.selected_skill)
        if reason:
            reason_lines = wrap_text(self.small_font, reason, self.learn_rect.width)
            for index, line in enumerate(reason_lines[-2:]):
                text = self.small_font.render(line, True, (175, 175, 180))
                self.screen.blit(
                    text,
                    text.get_rect(
                        midbottom=(
                            self.learn_rect.centerx,
                            self.learn_rect.top - 8 - (len(reason_lines[-2:]) - 1 - index) * 20,
                        )
                    ),
                )

    def draw(self) -> None:
        self.screen.fill((12, 15, 22))
        title = self.title_font.render("THE KNOWLEDGE TREE", True, MENU_TEXT_COLOR)
        self.screen.blit(title, (30, 22))
        book = pygame.Rect(title.get_width() + 52, 21, 44, 44)
        book_image = load_ui_image(KNOWLEDGE_BOOK_PATH, book.size)
        if book_image is not None:
            self.screen.blit(book_image, book)
        else:
            draw_book_icon(
                self.screen,
                book,
                color=(55, 125, 225),
                outline_color=(245, 245, 250),
                accent_color=(245, 195, 70),
            )
        points = self.heading_font.render(
            str(self.state.hero_knowledge_points(self.hero_id)),
            True,
            (238, 202, 86),
        )
        self.screen.blit(points, points.get_rect(midleft=(book.right + 10, book.centery)))
        draw_action_button(
            self.screen,
            self.close_rect,
            "Close",
            self.small_font,
            True,
        )
        self.draw_tree()
        self.draw_detail()
        hint = self.small_font.render(self.status, True, (175, 185, 205))
        self.screen.blit(hint, (self.viewport.left + 8, self.viewport.bottom - 28))
