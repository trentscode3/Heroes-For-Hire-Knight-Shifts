import math
from collections.abc import Callable

import pygame

from core.ui_font import ui_font
from core.ui_assets import load_ui_image
from core.units import meters_label

from core.audio_manager import audio
from core.display_manager import display
from core.game_state import GameState
from items import Blessing, Gear, Item, TowerUpgrade
from core.skill_tree import draw_book_icon, draw_knowledge_tree
from sprites import Player, create_player
from core.settings import (
    BLESSING_SLOT_COUNT,
    INVENTORY_EQUIPPED_GEAR_PATH,
    INVENTORY_EQUIPMENT_VIEW_SIZE,
    INVENTORY_ITEM_GAP,
    INVENTORY_ITEM_SIZE,
    KNOWLEDGE_BOOK_PATH,
    INVENTORY_OVERLAY_COLOR,
    INVENTORY_PANEL_COLOR,
    INVENTORY_SECTION_COLOR,
    INVENTORY_SLOT_BORDER_COLOR,
    INVENTORY_SLOT_COLOR,
    MENU_TEXT_COLOR,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TOWER_SPRITE_PATH,
    TOWER_SHEET_FRAME_SIZE,
)
from .scene import Scene
from .item_detail import ItemDetailPanel
from .knowledge_scene import KnowledgeScene


class InventoryScene(Scene):
    """Paused drag-and-drop inventory shared by day and night scenes."""

    TABS = ("hero", "gear", "tower", "blessings")
    GEAR_SLOT_ORDER = ("head", "chest", "gloves", "boots")
    GEAR_SLOT_RECTS = (
        pygame.Rect(178, 4, 51, 49),
        pygame.Rect(178, 58, 51, 52),
        pygame.Rect(178, 116, 51, 50),
        pygame.Rect(178, 172, 51, 49),
    )

    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        state: GameState,
        close_callback: Callable[[], None],
        equipment_changed_callback: Callable[[], None] | None = None,
        player: Player | None = None,
        knowledge_access_mode: str = "day",
    ) -> None:
        super().__init__(manager, screen)
        self.state = state
        self.close_callback = close_callback
        self.equipment_changed_callback = equipment_changed_callback
        self.active_tab = "hero"
        self.player = player if player is not None else create_player(state.hero_id)
        self.knowledge_access_mode = knowledge_access_mode
        self.uses_preview_player = player is None
        if self.uses_preview_player:
            self.state.apply_player_gear(self.player)
            self.state.apply_player_blessings(self.player)
            self.state.apply_player_knowledge(self.player)
        self.dragged_item: Item | None = None
        self.drag_origin: tuple[str, object] | None = None
        self.status = "Drag to equip, or Shift-click for quick equip"
        self.detail_item: Item | None = None
        self.detail_panel = ItemDetailPanel()
        self.scroll_offsets = {tab: 0 for tab in self.TABS}
        self.scroll_dragging = False
        self.scroll_drag_offset = 0

        self.title_font = ui_font(50)
        self.tab_font = ui_font(30)
        self.item_font = ui_font(20)
        self.small_font = ui_font(18)

        self.panel_rect = pygame.Rect(70, 45, SCREEN_WIDTH - 140, SCREEN_HEIGHT - 90)
        self.inventory_rect = pygame.Rect(95, 135, 500, 555)
        self.sort_rect = pygame.Rect(
            self.inventory_rect.right - 158,
            self.inventory_rect.top + 10,
            142,
            32,
        )
        self.equipment_rect = pygame.Rect(620, 135, 565, 555)
        self.view_rect = pygame.Rect(0, 0, *INVENTORY_EQUIPMENT_VIEW_SIZE)
        self.view_rect.center = (self.equipment_rect.centerx, 390)

        self.tab_rects = {}
        tab_width = 122
        for index, tab in enumerate(self.TABS):
            rect = pygame.Rect(0, 0, tab_width, 42)
            rect.midtop = (
                self.equipment_rect.left + 69 + index * (tab_width + 12),
                150,
            )
            self.tab_rects[tab] = rect

        self.gear_view = self.load_scaled_image(
            INVENTORY_EQUIPPED_GEAR_PATH,
            self.view_rect.size,
        )
        tower_image = self.load_image(TOWER_SPRITE_PATH)
        if tower_image is not None:
            frame_width, frame_height = TOWER_SHEET_FRAME_SIZE
            tower_image = tower_image.subsurface(
                (0, 0, frame_width, frame_height)
            ).copy()
            tower_height = 180
            tower_width = round(
                tower_image.get_width() * tower_height / tower_image.get_height()
            )
            self.tower_image = pygame.transform.smoothscale(
                tower_image,
                (tower_width, tower_height),
            )
        else:
            self.tower_image = None

    @staticmethod
    def load_image(path) -> pygame.Surface | None:
        try:
            return pygame.image.load(path).convert_alpha()
        except (FileNotFoundError, pygame.error):
            return None

    @classmethod
    def load_scaled_image(
        cls,
        path,
        size: tuple[int, int],
    ) -> pygame.Surface | None:
        image = cls.load_image(path)
        return pygame.transform.smoothscale(image, size) if image else None

    def inventory_content_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.inventory_rect.left + 12,
            self.inventory_rect.top + 52,
            self.inventory_rect.width - 34,
            self.inventory_rect.height - 66,
        )

    def visible_inventory_items(self, tab: str | None = None) -> list[Item]:
        tab = tab or self.active_tab
        if tab == "hero":
            visible_items = list(self.state.inventory)
        elif tab == "gear":
            visible_items = [item for item in self.state.inventory if isinstance(item, Gear)]
        elif tab == "tower":
            visible_items = [
                item for item in self.state.inventory if isinstance(item, TowerUpgrade)
            ]
        else:
            visible_items = [
                item for item in self.state.inventory if isinstance(item, Blessing)
            ]
        if self.state.inventory_sort == "rarity":
            visible_items.sort(
                key=lambda item: (-self.state.rarity_rank(item), item.name.casefold())
            )
        else:
            visible_items.sort(key=lambda item: item.name.casefold())
        return visible_items

    def inventory_sections(
        self,
        tab: str | None = None,
    ) -> tuple[tuple[str, list[Item]], tuple[str, list[Item]]]:
        items = self.visible_inventory_items(tab)
        equipped = [item for item in items if self.is_equipped(item)]
        unequipped = [item for item in items if not self.is_equipped(item)]
        return (("Equipped:", equipped), ("Unequipped:", unequipped))

    @staticmethod
    def section_height(item_count: int) -> int:
        rows = math.ceil(item_count / 4)
        return 28 + rows * (INVENTORY_ITEM_SIZE[1] + INVENTORY_ITEM_GAP)

    def inventory_content_height(self, tab: str | None = None) -> int:
        sections = self.inventory_sections(tab)
        return sum(self.section_height(len(items)) for _, items in sections) + 8

    def maximum_scroll(self, tab: str | None = None) -> int:
        tab = tab or self.active_tab
        return max(
            0,
            self.inventory_content_height(tab) - self.inventory_content_rect().height,
        )

    def set_scroll(self, value: float) -> None:
        self.scroll_offsets[self.active_tab] = max(
            0,
            min(self.maximum_scroll(), round(value)),
        )

    def scroll_track_rect(self) -> pygame.Rect:
        content = self.inventory_content_rect()
        return pygame.Rect(self.inventory_rect.right - 17, content.top, 8, content.height)

    def scroll_thumb_rect(self) -> pygame.Rect:
        track = self.scroll_track_rect()
        maximum = self.maximum_scroll()
        if maximum <= 0:
            return track.copy()
        total_height = max(1, self.inventory_content_height())
        thumb_height = max(36, round(track.height * track.height / total_height))
        travel = track.height - thumb_height
        top = track.top + round(
            travel * self.scroll_offsets[self.active_tab] / maximum
        )
        return pygame.Rect(track.left, top, track.width, thumb_height)

    def item_visible_in_tab(self, item: Item, tab: str) -> bool:
        if tab == "hero":
            return True
        if tab == "gear":
            return isinstance(item, Gear)
        if tab == "tower":
            return isinstance(item, TowerUpgrade)
        return isinstance(item, Blessing)

    def select_tab(self, tab: str) -> None:
        self.active_tab = tab
        self.set_scroll(self.scroll_offsets[tab])
        if self.detail_item is not None and not self.item_visible_in_tab(
            self.detail_item,
            tab,
        ):
            self.detail_item = None

    def detail_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.inventory_rect.left + 18,
            self.inventory_rect.bottom - 305,
            self.inventory_rect.width - 36,
            285,
        )

    def detail_close_rect(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, 28, 28)
        rect.topright = (
            self.detail_rect().right - 8,
            self.detail_rect().top + 8,
        )
        return rect

    def knowledge_preview_rect(self) -> pygame.Rect:
        content = self.equipment_rect.inflate(-28, -92)
        content.top += 45
        return pygame.Rect(
            content.centerx + 16,
            content.top + 16,
            content.width // 2 - 32,
            content.height - 32,
        )

    def close_knowledge_view(self) -> None:
        self.set_subscene(None)

    def open_knowledge_view(self) -> None:
        self.set_subscene(
            KnowledgeScene(
                self.manager,
                self.screen,
                self.state,
                self.close_knowledge_view,
                access_mode=self.knowledge_access_mode,
                hero_id=self.player.HERO_ID,
            )
        )

    def inventory_layout(
        self,
    ) -> tuple[list[tuple[str, pygame.Rect]], list[tuple[Item, pygame.Rect]]]:
        item_width, item_height = INVENTORY_ITEM_SIZE
        columns = 4
        first_x = self.inventory_rect.left + 18
        cursor_y = self.inventory_content_rect().top - self.scroll_offsets[self.active_tab]
        headings: list[tuple[str, pygame.Rect]] = []
        item_rects: list[tuple[Item, pygame.Rect]] = []
        for heading, items in self.inventory_sections():
            headings.append(
                (heading, pygame.Rect(first_x, cursor_y, self.inventory_rect.width - 52, 24))
            )
            cursor_y += 28
            for index, item in enumerate(items):
                item_rects.append((
                    item,
                    pygame.Rect(
                    first_x + (index % columns) * (item_width + INVENTORY_ITEM_GAP),
                    cursor_y + (index // columns) * (item_height + INVENTORY_ITEM_GAP),
                    item_width,
                    item_height,
                    ),
                ))
            cursor_y += math.ceil(len(items) / columns) * (
                item_height + INVENTORY_ITEM_GAP
            )
        return headings, item_rects

    def inventory_item_rects(self) -> list[tuple[Item, pygame.Rect]]:
        return self.inventory_layout()[1]

    def gear_slots(self) -> dict[str, pygame.Rect]:
        scale_x = self.view_rect.width / 253
        scale_y = self.view_rect.height / 243
        slots = {}
        for gear_type, source in zip(self.GEAR_SLOT_ORDER, self.GEAR_SLOT_RECTS):
            slots[gear_type] = pygame.Rect(
                self.view_rect.left + round(source.x * scale_x),
                self.view_rect.top + round(source.y * scale_y),
                round(source.width * scale_x),
                round(source.height * scale_y),
            )
        return slots

    def reinforcement_gear_slots(self) -> dict[str, pygame.Rect]:
        slots = {}
        for index, gear_type in enumerate(self.GEAR_SLOT_ORDER):
            slots[gear_type] = pygame.Rect(
                self.view_rect.left + 12 + index * 48,
                self.view_rect.bottom - 52,
                42,
                42,
            )
        return slots

    def reinforcement_gear_unlocked(self) -> bool:
        return (
            "well_equipped_soldiers"
            in self.state.hero_knowledge_skills("warrior")
        )

    def upgrade_slots(self) -> list[pygame.Rect]:
        slot_count = len(self.state.equipped_upgrades)
        if (
            self.state.tower_upgrade_weight
            < self.state.effective_tower_upgrade_weight_cap
        ):
            slot_count += 1
        slots = []
        for index in range(slot_count):
            column = index // 5
            row = index % 5
            slots.append(
                pygame.Rect(
                    self.view_rect.right - 70 - column * 64,
                    self.view_rect.top + 18 + row * 64,
                    54,
                    54,
                )
            )
        return slots

    def blessing_slots(self) -> list[pygame.Rect]:
        center_x = self.view_rect.centerx
        centers = (
            (center_x, self.view_rect.top + 85),
            (center_x - 100, self.view_rect.top + 235),
            (center_x + 100, self.view_rect.top + 235),
        )
        return [pygame.Rect(0, 0, 78, 78) for _ in centers]

    def positioned_blessing_slots(self) -> list[pygame.Rect]:
        slots = self.blessing_slots()
        centers = (
            (self.view_rect.centerx, self.view_rect.top + 85),
            (self.view_rect.centerx - 100, self.view_rect.top + 235),
            (self.view_rect.centerx + 100, self.view_rect.top + 235),
        )
        for rect, center in zip(slots, centers):
            rect.center = center
        return slots

    def is_equipped(self, item: Item) -> bool:
        if isinstance(item, Gear):
            return (
                self.state.equipped_gear.get(item.gear_type) is item
                or self.state.equipped_reinforcement_gear.get(item.gear_type) is item
            )
        if isinstance(item, TowerUpgrade):
            return any(equipped is item for equipped in self.state.equipped_upgrades)
        if isinstance(item, Blessing):
            return any(
                equipped is item
                for equipped in self.state.blessings
                if equipped is not None
            )
        return False

    def start_drag(self, item: Item, origin: tuple[str, object]) -> None:
        self.dragged_item = item
        self.drag_origin = origin

    def quick_equip(self, item: Item) -> None:
        """Equip an inventory item and select any gear it displaced."""
        displaced = None
        if isinstance(item, Gear):
            displaced = self.state.equipped_gear.get(item.gear_type)

        if self.state.auto_equip(item):
            self.dragged_item = None
            self.drag_origin = None
            if displaced is not None and displaced is not item:
                self.detail_item = displaced
                self.status = (
                    f"Equipped {item.name}; selected {displaced.name}"
                )
            else:
                self.detail_item = item
                self.status = f"Equipped {item.name}"
            self.notify_equipment_changed()
            return

        if isinstance(item, TowerUpgrade):
            self.status = "Tower weight capacity exceeded"
        elif isinstance(item, Blessing):
            self.status = "No empty blessing slots"
        else:
            self.status = "That item cannot be equipped"

    def equipped_item_at(self, position: tuple[int, int]) -> tuple[Item, tuple[str, object]] | None:
        if self.active_tab == "gear":
            for gear_type, rect in self.gear_slots().items():
                item = self.state.equipped_gear.get(gear_type)
                if item is not None and rect.collidepoint(position):
                    return item, ("gear", gear_type)
            if self.reinforcement_gear_unlocked():
                for gear_type, rect in self.reinforcement_gear_slots().items():
                    item = self.state.equipped_reinforcement_gear.get(gear_type)
                    if item is not None and rect.collidepoint(position):
                        return item, ("reinforcement_gear", gear_type)
        elif self.active_tab == "tower":
            for index, item in enumerate(self.state.equipped_upgrades):
                if self.upgrade_slots()[index].collidepoint(position):
                    return item, ("tower", index)
        elif self.active_tab == "blessings":
            for index, item in enumerate(self.state.blessings):
                slot = self.positioned_blessing_slots()[index]
                if item is not None and slot.collidepoint(position):
                    return item, ("blessings", index)
        return None

    def finish_drag(self, position: tuple[int, int]) -> None:
        item = self.dragged_item
        origin = self.drag_origin
        self.dragged_item = None
        self.drag_origin = None
        if item is None:
            return

        if self.inventory_rect.collidepoint(position):
            if origin is not None and origin[0] != "inventory":
                if self.state.unequip(item):
                    self.status = f"Unequipped {item.name}"
                    self.notify_equipment_changed()
            return

        equipped = False
        if self.active_tab == "gear" and isinstance(item, Gear):
            hero_slot = self.gear_slots().get(item.gear_type)
            reinforcement_slot = (
                self.reinforcement_gear_slots().get(item.gear_type)
                if self.reinforcement_gear_unlocked()
                else None
            )
            if hero_slot is not None and hero_slot.collidepoint(position):
                equipped = self.state.equip_gear(item)
            elif (
                reinforcement_slot is not None
                and reinforcement_slot.collidepoint(position)
            ):
                equipped = self.state.equip_reinforcement_gear(item)
                if not equipped:
                    self.status = "Learn Well Equipped Soldiers first"
        elif self.active_tab == "tower" and isinstance(item, TowerUpgrade):
            slots = self.upgrade_slots()
            if slots and slots[-1].collidepoint(position):
                equipped = self.state.equip_upgrade(item)
                if not equipped:
                    self.status = "Tower weight capacity exceeded"
        elif self.active_tab == "blessings" and isinstance(item, Blessing):
            for index, slot in enumerate(self.positioned_blessing_slots()):
                if slot.collidepoint(position):
                    equipped = self.state.equip_blessing(item, index)
                    break

        if equipped:
            self.status = f"Equipped {item.name}"
            self.notify_equipment_changed()
        elif "exceeded" not in self.status and "Well Equipped" not in self.status:
            self.status = "That item cannot be placed there"

    def notify_equipment_changed(self) -> None:
        if self.equipment_changed_callback is not None:
            self.equipment_changed_callback()
        if self.uses_preview_player:
            self.state.apply_player_gear(self.player)
            self.state.apply_player_blessings(self.player)
            self.state.apply_player_knowledge(self.player)
        self.set_scroll(self.scroll_offsets[self.active_tab])

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_i, pygame.K_ESCAPE):
            self.close_callback()
            return

        if event.type == pygame.MOUSEWHEEL:
            if self.inventory_rect.collidepoint(display.mouse_position()):
                self.set_scroll(
                    self.scroll_offsets[self.active_tab] - event.y * 60
                )
            return

        if event.type == pygame.MOUSEMOTION and self.scroll_dragging:
            track = self.scroll_track_rect()
            thumb = self.scroll_thumb_rect()
            travel = track.height - thumb.height
            if travel > 0:
                thumb_top = event.pos[1] - self.scroll_drag_offset
                progress = (thumb_top - track.top) / travel
                self.set_scroll(progress * self.maximum_scroll())
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if (
                self.active_tab == "hero"
                and self.knowledge_preview_rect().collidepoint(event.pos)
            ):
                audio.play_sound("menu_click")
                self.open_knowledge_view()
                return
            if (
                self.detail_item is not None
                and self.detail_close_rect().collidepoint(event.pos)
            ):
                audio.play_sound("menu_click")
                self.detail_item = None
                return
            if (
                self.detail_item is not None
                and self.detail_rect().collidepoint(event.pos)
            ):
                self.detail_item = None
                return
            thumb = self.scroll_thumb_rect()
            track = self.scroll_track_rect()
            if thumb.collidepoint(event.pos) and self.maximum_scroll() > 0:
                self.scroll_dragging = True
                self.scroll_drag_offset = event.pos[1] - thumb.top
                return
            if track.collidepoint(event.pos) and self.maximum_scroll() > 0:
                travel = track.height - thumb.height
                if travel > 0:
                    progress = (event.pos[1] - track.top - thumb.height / 2) / travel
                    self.set_scroll(progress * self.maximum_scroll())
                return
            if self.sort_rect.collidepoint(event.pos):
                audio.play_sound("menu_click")
                self.state.inventory_sort = (
                    "rarity" if self.state.inventory_sort == "name" else "name"
                )
                self.status = f"Sorted by {self.state.inventory_sort}"
                return
            for tab, rect in self.tab_rects.items():
                if rect.collidepoint(event.pos):
                    audio.play_sound("menu_click")
                    self.select_tab(tab)
                    return
            if self.inventory_content_rect().collidepoint(event.pos):
                for item, rect in reversed(self.inventory_item_rects()):
                    if not rect.collidepoint(event.pos):
                        continue
                    audio.play_sound("menu_click")
                    if self.detail_item is item:
                        self.detail_item = None
                        self.dragged_item = None
                        self.drag_origin = None
                        return
                    self.detail_item = item
                    modifiers = getattr(event, "mod", pygame.key.get_mods())
                    if modifiers & pygame.KMOD_SHIFT:
                        if self.is_equipped(item):
                            self.state.unequip(item)
                            self.status = f"Unequipped {item.name}"
                            self.notify_equipment_changed()
                        else:
                            self.quick_equip(item)
                        return
                    self.start_drag(item, ("inventory", item))
                    return
            equipped = self.equipped_item_at(event.pos)
            if equipped is not None:
                audio.play_sound("menu_click")
                if self.detail_item is equipped[0]:
                    self.detail_item = None
                    self.dragged_item = None
                    self.drag_origin = None
                    return
                self.detail_item = equipped[0]
                modifiers = getattr(event, "mod", pygame.key.get_mods())
                if modifiers & pygame.KMOD_SHIFT:
                    self.state.unequip(equipped[0])
                    self.status = f"Unequipped {equipped[0].name}"
                    self.notify_equipment_changed()
                    return
                self.start_drag(*equipped)
                return
            if self.panel_rect.collidepoint(event.pos):
                self.detail_item = None
                self.dragged_item = None
                self.drag_origin = None
                return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.scroll_dragging = False
            self.finish_drag(event.pos)

    def draw_slot(self, rect: pygame.Rect, item: Item | None = None) -> None:
        pygame.draw.rect(self.screen, INVENTORY_SLOT_COLOR, rect, border_radius=6)
        pygame.draw.rect(
            self.screen,
            INVENTORY_SLOT_BORDER_COLOR,
            rect,
            width=2,
            border_radius=6,
        )
        if item is not None:
            item.draw(self.screen, rect.inflate(-6, -6), self.small_font)

    def draw_inventory(self) -> None:
        pygame.draw.rect(
            self.screen,
            INVENTORY_SECTION_COLOR,
            self.inventory_rect,
            border_radius=10,
        )
        heading = "ALL ITEMS" if self.active_tab == "hero" else "INVENTORY"
        title = self.tab_font.render(heading, True, MENU_TEXT_COLOR)
        self.screen.blit(title, (self.inventory_rect.left + 18, self.inventory_rect.top + 14))
        pygame.draw.rect(self.screen, (52, 58, 68), self.sort_rect, border_radius=6)
        pygame.draw.rect(
            self.screen,
            INVENTORY_SLOT_BORDER_COLOR,
            self.sort_rect,
            width=2,
            border_radius=6,
        )
        sort_label = self.small_font.render(
            f"Sort: {self.state.inventory_sort.title()}", True, MENU_TEXT_COLOR
        )
        self.screen.blit(sort_label, sort_label.get_rect(center=self.sort_rect.center))
        content = self.inventory_content_rect()
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(content)
        headings, item_rects = self.inventory_layout()
        for heading, rect in headings:
            text = self.small_font.render(heading, True, (190, 198, 215))
            self.screen.blit(text, (rect.left, rect.top + 2))
            pygame.draw.line(
                self.screen,
                (70, 78, 92),
                (rect.left + text.get_width() + 8, rect.centery),
                (rect.right, rect.centery),
                1,
            )
        for item, rect in item_rects:
            if not rect.colliderect(content):
                continue
            item.draw(self.screen, rect, self.item_font)
            if item is self.detail_item:
                pygame.draw.rect(
                    self.screen,
                    (255, 215, 60),
                    rect,
                    width=3,
                    border_radius=8,
                )
        self.screen.set_clip(previous_clip)

        track = self.scroll_track_rect()
        thumb = self.scroll_thumb_rect()
        pygame.draw.rect(self.screen, (35, 39, 48), track, border_radius=4)
        pygame.draw.rect(
            self.screen,
            (115, 126, 150) if self.maximum_scroll() > 0 else (65, 70, 82),
            thumb,
            border_radius=4,
        )

    def draw_gear_view(self) -> None:
        if self.gear_view is not None:
            self.screen.blit(self.gear_view, self.view_rect)
        else:
            pygame.draw.rect(self.screen, (8, 8, 12), self.view_rect)
        for gear_type, rect in self.gear_slots().items():
            self.draw_slot(rect, self.state.equipped_gear.get(gear_type))
        reinforcement_unlocked = self.reinforcement_gear_unlocked()
        if not reinforcement_unlocked:
            return
        panel = pygame.Rect(
            self.view_rect.left + 5,
            self.view_rect.bottom - 82,
            205,
            78,
        )
        pygame.draw.rect(self.screen, (18, 28, 43), panel, border_radius=8)
        label = self.small_font.render(
            "REINFORCEMENTS",
            True,
            (125, 185, 235),
        )
        self.screen.blit(label, (panel.left + 7, panel.top + 3))
        for gear_type, rect in self.reinforcement_gear_slots().items():
            self.draw_slot(
                rect,
                self.state.equipped_reinforcement_gear.get(gear_type),
            )

    def draw_hero_view(self) -> None:
        content = self.equipment_rect.inflate(-28, -92)
        content.top += 45
        pygame.draw.rect(self.screen, (18, 20, 26), content, border_radius=10)
        stats_x = content.left + 18
        stats_y = content.top + 18
        stats_width = content.width // 2 - 42
        heading = self.tab_font.render("CURRENT STATS", True, (235, 210, 120))
        self.screen.blit(heading, (stats_x, stats_y))
        stats_y += 38
        attack_area = round(math.degrees(self.player.attack_half_angle * 2))
        stats = (
            f"Level: {self.player.level}",
            f"XP: {self.player.xp:g} / {self.player.xpmax} XP",
            f"Damage: {self.player.atkdmg:.1f} HP",
            f"Attack cooldown: {self.player.attack_speed:.2f} s",
            f"Attack rate: {1 / self.player.attack_speed:.2f} attacks/s",
            f"Move speed: {meters_label(self.player.move_speed, 'm/s')}",
            f"Attack range: {meters_label(self.player.attack_radius)}",
            f"Attack area: {attack_area} degrees",
            (
                f"Critical chance: {self.player.crit_chance:.0%}-100% by range"
                if self.player.HERO_ID == "robin_hood"
                else f"Critical chance: {self.player.crit_chance:.0%}"
            ),
            f"Critical damage: x{self.player.crit_multiplier:g}",
        )
        for stat in stats:
            text = Item.fit_label(stat, self.small_font, stats_width)
            self.screen.blit(text, (stats_x, stats_y))
            stats_y += 25

        tree_rect = self.knowledge_preview_rect()
        pygame.draw.rect(self.screen, (24, 35, 58), tree_rect, border_radius=9)
        pygame.draw.rect(self.screen, (85, 130, 205), tree_rect, width=2, border_radius=9)
        book_rect = pygame.Rect(tree_rect.left + 12, tree_rect.top + 10, 38, 32)
        book_image = load_ui_image(KNOWLEDGE_BOOK_PATH, book_rect.size)
        if book_image is not None:
            self.screen.blit(book_image, book_rect)
        else:
            draw_book_icon(
                self.screen,
                book_rect,
                color=(55, 125, 225),
                outline_color=(245, 245, 250),
                accent_color=(245, 195, 70),
            )
        knowledge_text = self.small_font.render(
            f"Knowledge: {self.state.hero_knowledge_points(self.player.HERO_ID)}",
            True,
            (235, 210, 120),
        )
        self.screen.blit(
            knowledge_text,
            knowledge_text.get_rect(midleft=(book_rect.right + 8, book_rect.centery)),
        )
        if self.player.HERO_ID == "warrior":
            unlocked = self.state.hero_knowledge_skills(self.player.HERO_ID)
            draw_knowledge_tree(
                self.screen,
                tree_rect.inflate(-12, -52).move(0, 18),
                unlocked,
                self.state.has_promotion("warrior", "shift_lead"),
                compact=True,
                show_title=False,
            )
            prompt = self.small_font.render(
                "Click to view full tree",
                True,
                (235, 210, 120),
            )
            self.screen.blit(
                prompt,
                prompt.get_rect(midbottom=(tree_rect.centerx, tree_rect.bottom - 30)),
            )
        else:
            message = self.small_font.render(
                "Knowledge Tree coming soon", True, MENU_TEXT_COLOR
            )
            self.screen.blit(message, message.get_rect(center=tree_rect.center))

    def draw_tower_view(self) -> None:
        pygame.draw.rect(self.screen, (8, 8, 12), self.view_rect)
        if self.tower_image is not None:
            tower_rect = self.tower_image.get_rect(
                center=(self.view_rect.left + 115, self.view_rect.centery)
            )
            self.screen.blit(self.tower_image, tower_rect)
        for index, rect in enumerate(self.upgrade_slots()):
            item = (
                self.state.equipped_upgrades[index]
                if index < len(self.state.equipped_upgrades)
                else None
            )
            self.draw_slot(rect, item)
        weight = self.tab_font.render(
            "Weight: "
            f"{self.state.tower_upgrade_weight}/"
            f"{self.state.effective_tower_upgrade_weight_cap}",
            True,
            MENU_TEXT_COLOR,
        )
        self.screen.blit(
            weight,
            weight.get_rect(
                midbottom=(self.view_rect.centerx, self.view_rect.bottom - 8)
            ),
        )
        defense = self.tab_font.render(
            f"Defense: {self.state.tower_defense}",
            True,
            MENU_TEXT_COLOR,
        )
        self.screen.blit(defense, (self.view_rect.left + 14, self.view_rect.top + 12))

    def draw_blessing_view(self) -> None:
        pygame.draw.rect(self.screen, (8, 8, 12), self.view_rect)
        slots = self.positioned_blessing_slots()
        if len(slots) == BLESSING_SLOT_COUNT:
            pygame.draw.lines(
                self.screen,
                INVENTORY_SLOT_BORDER_COLOR,
                True,
                [rect.center for rect in slots],
                width=2,
            )
        for index, rect in enumerate(slots):
            item = self.state.blessings[index]
            self.draw_slot(rect, item)

    def draw(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(INVENTORY_OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, INVENTORY_PANEL_COLOR, self.panel_rect, border_radius=12)

        title = self.title_font.render("INVENTORY", True, MENU_TEXT_COLOR)
        self.screen.blit(title, title.get_rect(midtop=(self.panel_rect.centerx, 60)))
        hint = self.small_font.render("I / ESC: close", True, MENU_TEXT_COLOR)
        self.screen.blit(hint, (self.panel_rect.right - 100, self.panel_rect.top + 16))

        self.draw_inventory()
        pygame.draw.rect(
            self.screen,
            INVENTORY_SECTION_COLOR,
            self.equipment_rect,
            border_radius=10,
        )
        for tab, rect in self.tab_rects.items():
            color = (95, 105, 125) if tab == self.active_tab else INVENTORY_SLOT_COLOR
            pygame.draw.rect(self.screen, color, rect, border_radius=7)
            label = self.tab_font.render(tab.title(), True, MENU_TEXT_COLOR)
            self.screen.blit(label, label.get_rect(center=rect.center))

        if self.active_tab == "hero":
            self.draw_hero_view()
        elif self.active_tab == "gear":
            self.draw_gear_view()
        elif self.active_tab == "tower":
            self.draw_tower_view()
        else:
            self.draw_blessing_view()

        status = self.small_font.render(self.status, True, MENU_TEXT_COLOR)
        self.screen.blit(status, (self.equipment_rect.left + 20, self.equipment_rect.bottom - 28))

        if self.detail_item is not None:
            detail_rect = self.detail_rect()
            self.detail_panel.draw(self.screen, detail_rect, self.detail_item)
            close_rect = self.detail_close_rect()
            pygame.draw.rect(self.screen, (185, 48, 55), close_rect, border_radius=6)
            pygame.draw.line(
                self.screen,
                (255, 238, 238),
                (close_rect.left + 7, close_rect.top + 7),
                (close_rect.right - 7, close_rect.bottom - 7),
                3,
            )
            pygame.draw.line(
                self.screen,
                (255, 238, 238),
                (close_rect.right - 7, close_rect.top + 7),
                (close_rect.left + 7, close_rect.bottom - 7),
                3,
            )

        if self.dragged_item is not None:
            drag_rect = pygame.Rect(0, 0, *INVENTORY_ITEM_SIZE)
            drag_rect.center = display.mouse_position()
            self.dragged_item.draw(self.screen, drag_rect, self.item_font)
