from collections.abc import Callable

import pygame

from core.ui_font import ui_font

from core.save_manager import SAVE_SLOT_COUNT, save_manager
from core.settings import (
    BUTTON_FONT_SIZE,
    MENU_BG_COLOR,
    MENU_TEXT_COLOR,
    SCENE_TITLE_FONT_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from .button import Button
from .scene import Scene


class SaveSlotsScene(Scene):
    """Four independent progression slots with one paused run per slot."""

    music_track = "menu"

    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        select_callback: Callable[[int], None],
        delete_callback: Callable[[int], bool],
    ) -> None:
        super().__init__(manager, screen)
        self.select_callback = select_callback
        self.delete_callback = delete_callback
        self.title_font = ui_font(SCENE_TITLE_FONT_SIZE)
        self.slot_font = ui_font(37)
        self.info_font = ui_font(25)
        button_font = ui_font(29)
        self.pending_delete_slot: int | None = None
        self.status = ""

        card_width, card_height = 520, 230
        centers = (
            (SCREEN_WIDTH // 2 - 280, 245),
            (SCREEN_WIDTH // 2 + 280, 245),
            (SCREEN_WIDTH // 2 - 280, 505),
            (SCREEN_WIDTH // 2 + 280, 505),
        )
        self.cards: list[pygame.Rect] = []
        self.load_buttons: list[Button] = []
        self.delete_buttons: list[Button] = []
        for slot, center in enumerate(centers, start=1):
            card = pygame.Rect(0, 0, card_width, card_height)
            card.center = center
            self.cards.append(card)
            load_rect = pygame.Rect(card.left + 22, card.bottom - 62, 310, 44)
            delete_rect = pygame.Rect(card.right - 164, card.bottom - 62, 142, 44)
            self.load_buttons.append(
                Button(
                    load_rect,
                    "Load",
                    button_font,
                    lambda slot=slot: self.select_slot(slot),
                )
            )
            self.delete_buttons.append(
                Button(
                    delete_rect,
                    "Delete",
                    button_font,
                    lambda slot=slot: self.request_delete(slot),
                )
            )

        back_rect = pygame.Rect(0, 0, 270, 48)
        back_rect.midbottom = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 14)
        self.back_button = Button(
            back_rect,
            "Back",
            ui_font(BUTTON_FONT_SIZE),
            lambda: self.manager.change("main_menu"),
        )
        self.refresh()

    def refresh(self) -> None:
        self.summaries = [
            save_manager.slot_summary(slot)
            for slot in range(1, SAVE_SLOT_COUNT + 1)
        ]
        for index, summary in enumerate(self.summaries):
            self.load_buttons[index].text = "Create" if summary is None else "Load"
            self.delete_buttons[index].text = (
                "Confirm"
                if self.pending_delete_slot == index + 1
                else "Delete"
            )

    def select_slot(self, slot: int) -> None:
        self.pending_delete_slot = None
        self.select_callback(slot)

    def request_delete(self, slot: int) -> None:
        if slot == save_manager.active_slot:
            self.pending_delete_slot = None
            self.status = "Select another slot before deleting the active progression."
            self.refresh()
            return
        if self.summaries[slot - 1] is None:
            self.status = "That slot is already empty."
            return
        if self.pending_delete_slot != slot:
            self.pending_delete_slot = slot
            self.status = f"Click Confirm to permanently delete Slot {slot}."
            self.refresh()
            return
        if self.delete_callback(slot):
            self.status = f"Slot {slot} deleted."
        self.pending_delete_slot = None
        self.refresh()

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.change("main_menu")
            return
        for button in (*self.load_buttons, *self.delete_buttons):
            button.handle_event(event)
        self.back_button.handle_event(event)

    @staticmethod
    def scene_label(scene_name: str) -> str:
        return {
            "day": "Day preparations",
            "incoming": "Night incoming",
            "outgoing": "Returning at dawn",
            "game": "Night battle",
        }.get(scene_name, "Day preparations")

    def draw(self) -> None:
        self.screen.fill(MENU_BG_COLOR)
        title = self.title_font.render("PERSONNEL FILES", True, MENU_TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 65)))

        for index, (card, summary) in enumerate(zip(self.cards, self.summaries)):
            slot = index + 1
            active = slot == save_manager.active_slot
            pygame.draw.rect(self.screen, (35, 38, 46), card, border_radius=12)
            pygame.draw.rect(
                self.screen,
                (245, 205, 80) if active else (105, 115, 135),
                card,
                width=3,
                border_radius=12,
            )
            heading = f"SLOT {slot}" + ("  •  ACTIVE" if active else "")
            heading_text = self.slot_font.render(heading, True, MENU_TEXT_COLOR)
            self.screen.blit(heading_text, (card.left + 22, card.top + 18))

            if summary is None:
                lines = ("EMPTY", "Create a new Warrior progression")
            else:
                hero_name = summary["hero_id"].replace("_", " ").title()
                run_status = (
                    f"Paused: {self.scene_label(summary['resume_scene'])}"
                    if summary["run_active"]
                    else "No active run"
                )
                lines = (
                    f"Hero: {hero_name}   •   Night: {summary['night_count']}",
                    f"Games played: {summary['games_played']}",
                    run_status,
                )
            for line_index, line in enumerate(lines):
                color = (235, 210, 110) if line == "EMPTY" else MENU_TEXT_COLOR
                text = self.info_font.render(line, True, color)
                self.screen.blit(text, (card.left + 24, card.top + 72 + line_index * 29))

            self.load_buttons[index].display(self.screen)
            self.delete_buttons[index].display(self.screen)

        if self.status:
            status = self.info_font.render(self.status, True, (235, 205, 115))
            self.screen.blit(status, status.get_rect(center=(SCREEN_WIDTH // 2, 650)))
        self.back_button.display(self.screen)
