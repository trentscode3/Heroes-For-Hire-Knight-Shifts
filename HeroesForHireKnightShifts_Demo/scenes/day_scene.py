import math
import random

import pygame

from core.ui_font import ui_font
from core.ui_assets import load_ui_image

from core.audio_manager import audio
from core.game_state import GameState
from items import BLESSING_CATALOG, GEAR_CATALOG, UPGRADE_CATALOG, Item
from items.factory import random_collector_item, rollover_order
from core.settings import (
    BUTTON_FONT_SIZE,
    DAY_CARD_COLOR,
    DAY_CARD_SIZE,
    DAY_CARD_SPACING,
    DAY_DURATION,
    DAY_RECEIPT_COLOR,
    DAY_RECEIPT_SIZE,
    DAY_RECEIPT_TEXT_COLOR,
    DAY_TIMER_FONT_SIZE,
    ITEM_REVEAL_OVERLAY_COLOR,
    ITEM_REVEAL_SQUARE_SIZE,
    ITEM_RARITIES,
    KNOWLEDGE_BOOK_PATH,
    MENU_TEXT_COLOR,
    SCENE_TITLE_FONT_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from core.world_environment import create_tower, draw_environment
from .button import Button
from .inventory_scene import InventoryScene
from .knowledge_scene import KnowledgeScene
from .item_detail import ItemDetailPanel
from .scene import Scene
from .pause_scene import PauseScene
from core.user_preferences import preferences


STORES = (
    ("Gear Store", "gear"),
    ("Tower Depot", "upgrade"),
    ("The Enchanter", "blessing"),
)

PACK_OPEN_DURATION = 2.35
PACK_REVEAL_DURATION = 1.0
PACK_SLIDE_DURATION = 0.75
PACK_RARITY_ORDER = ("common", "uncommon", "rare", "legendary")
COLLECTOR_WEIGHTS = {"uncommon": 30, "rare": 60, "legendary": 10}
COLLECTOR_ROLLOVER = {
    "uncommon": ("uncommon", "rare", "legendary", "common"),
    "rare": ("rare", "legendary", "uncommon", "common"),
    "legendary": ("legendary", "rare", "uncommon", "common"),
}


class DayScene(Scene):
    """Timed preparation menu for shopping before nighttime defense."""

    music_track = "day"

    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        state: GameState,
        next_scene: str = "game",
        debug_mode: bool = False,
    ) -> None:
        super().__init__(manager, screen)
        self.state = state
        self.next_scene = next_scene
        self.debug_mode = debug_mode
        self.is_first_day = self.state.night_count == 0
        continuing_day = self.state.day_active and bool(self.state.day_shop_offers)
        self.elapsed = self.state.day_elapsed if continuing_day else 0.0
        if self.debug_mode:
            self.state.populate_debug_inventory()
        self.state.start_day()
        self.tower = create_tower(
            self.state,
            (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2),
        )

        self.title_font = ui_font(SCENE_TITLE_FONT_SIZE)
        self.timer_font = ui_font(DAY_TIMER_FONT_SIZE)
        self.store_font = ui_font(32)
        self.item_font = ui_font(22)
        self.rate_font = ui_font(17)
        self.receipt_font = ui_font(23)
        button_font = ui_font(BUTTON_FONT_SIZE)

        excluded_names = (
            self.state.owned_item_names
            if self.state.anti_hoarding_enabled
            else set()
        )
        self.direct_offers = []
        self.mystery_offers = []
        for index, (_, item_type) in enumerate(STORES):
            old_collector_key = self.source_key((index, "collector"))
            mystery_key = self.source_key((index, "mystery"))
            if (
                old_collector_key in self.state.locked_shop_offers
                and mystery_key not in self.state.locked_shop_offers
            ):
                self.state.locked_shop_offers[mystery_key] = (
                    self.state.locked_shop_offers[old_collector_key]
                )
            self.state.locked_shop_offers.pop(old_collector_key, None)
            self.state.day_shop_offers.pop(old_collector_key, None)
            offers = []
            for kind in ("direct", "mystery"):
                key = self.source_key((index, kind))
                saved = self.state.day_shop_offers.get(key) if continuing_day else None
                locked = self.state.locked_shop_offers.get(key)
                item = self.state.item_from_data(saved or locked)
                if item is None:
                    if kind == "direct":
                        item = Item.random(item_type, excluded_names=excluded_names)
                    else:
                        if random.random() < 0.60:
                            item = Item.random(
                                item_type,
                                price=2,
                                excluded_names=excluded_names,
                            )
                        else:
                            item = random_collector_item(item_type, excluded_names)
                offers.append(item)
                if item is not None:
                    self.state.day_shop_offers[key] = self.state.item_to_data(item)
            self.direct_offers.append(offers[0])
            self.mystery_offers.append(offers[1])
        self.cart: list[tuple[tuple[int, str], Item]] = []
        self.sold_sources: set[tuple[int, str]] = {
            source
            for key in self.state.day_shop_sold
            if (source := self.parse_source_key(key))[1] in ("direct", "mystery")
        }
        self.option_rects: dict[tuple[int, str], pygame.Rect] = {}
        self.status = "Click a receipt item to remove it"
        self.reveal_queue: list[Item] = []
        self.reveal_item: Item | None = None
        self.reveal_elapsed = 0.0
        self.reveal_phase = "rip"
        self.tear_dragging = False
        self.tear_start_pos = pygame.Vector2()
        self.tear_progress = 0.0
        self.reveal_equip_status = ""
        self.pending_night = False
        self.detail_item: Item | None = None
        self.detail_mystery = False
        self.detail_source: tuple[int, str] | None = None
        self.detail_sold = False
        self.detail_panel = ItemDetailPanel()
        self.knowledge_rect = pygame.Rect(SCREEN_WIDTH - 202, 10, 174, 68)

        skip_rect = pygame.Rect(0, 0, 370, 72)
        skip_rect.bottomleft = (20, SCREEN_HEIGHT - 20)
        self.skip_button = Button(
            skip_rect,
            "Skip to Night",
            button_font,
            self.begin_night,
            color=(24, 35, 68),
            hover_color=(38, 55, 96),
            text_color=(255, 232, 150),
            border_color=(225, 190, 85),
            border_width=3,
        )
        self.skip_button.text_offset_x = 22

        receipt_width, receipt_height = DAY_RECEIPT_SIZE
        self.receipt_rect = pygame.Rect(
            SCREEN_WIDTH - receipt_width - 20,
            SCREEN_HEIGHT - receipt_height - 20,
            receipt_width,
            receipt_height,
        )
        self.checkout_rect = pygame.Rect(
            self.receipt_rect.right - 184,
            self.receipt_rect.bottom - 60,
            168,
            46,
        )
        self.build_store_rects()

    def build_store_rects(self) -> None:
        total_width = len(STORES) * DAY_CARD_SIZE[0] + (
            len(STORES) - 1
        ) * DAY_CARD_SPACING
        first_left = (SCREEN_WIDTH - total_width) / 2
        option_width = (DAY_CARD_SIZE[0] - 42) // 2
        for index in range(len(STORES)):
            card_left = first_left + index * (
                DAY_CARD_SIZE[0] + DAY_CARD_SPACING
            )
            option_top = 265
            self.option_rects[(index, "direct")] = pygame.Rect(
                card_left + 14,
                option_top,
                option_width,
                115,
            )
            self.option_rects[(index, "mystery")] = pygame.Rect(
                card_left + 28 + option_width,
                option_top,
                option_width,
                115,
            )

    @staticmethod
    def source_key(source: tuple[int, str]) -> str:
        return f"{source[0]}:{source[1]}"

    @staticmethod
    def parse_source_key(key: str) -> tuple[int, str]:
        index, kind = key.split(":", 1)
        return int(index), kind

    def offer_for(self, source: tuple[int, str]) -> Item | None:
        offers = {
            "direct": self.direct_offers,
            "mystery": self.mystery_offers,
        }
        return offers[source[1]][source[0]]

    def lock_rect(self, source: tuple[int, str]) -> pygame.Rect:
        rect = self.option_rects[source]
        return pygame.Rect(rect.right - 24, rect.top + 4, 20, 20)

    def mystery_label(self, store_index: int) -> str:
        item = self.mystery_offers[store_index]
        return "collector pack" if item is not None and item.price == 5 else "mystery item"

    def mystery_rates(self, item_type: str, collector: bool) -> dict[str, int]:
        catalogs = {
            "gear": GEAR_CATALOG,
            "upgrade": UPGRADE_CATALOG,
            "blessing": BLESSING_CATALOG,
        }
        excluded = {
            name.casefold()
            for name in (
                self.state.owned_item_names
                if self.state.anti_hoarding_enabled
                else set()
            )
        }
        available = {
            item.rarity
            for item in catalogs[item_type]
            if item.name.casefold() not in excluded
        }
        weights = COLLECTOR_WEIGHTS if collector else {
            rarity: int(data["weight"])
            for rarity, data in ITEM_RARITIES.items()
        }
        totals = {rarity: 0 for rarity in PACK_RARITY_ORDER}
        for rolled, weight in weights.items():
            order = COLLECTOR_ROLLOVER[rolled] if collector else rollover_order(rolled)
            resolved = next((rarity for rarity in order if rarity in available), None)
            if resolved is not None:
                totals[resolved] += weight
        return totals

    def select_detail(
        self,
        item: Item | None,
        *,
        source: tuple[int, str] | None = None,
        mystery: bool = False,
        sold: bool = False,
    ) -> None:
        self.detail_item = item
        self.detail_source = source
        self.detail_mystery = mystery
        self.detail_sold = sold

    def clear_detail(self) -> None:
        self.select_detail(None)

    def toggle_lock(self, source: tuple[int, str]) -> None:
        key = self.source_key(source)
        if key in self.state.locked_shop_offers:
            del self.state.locked_shop_offers[key]
            self.status = "Offer unlocked"
            return
        item = self.offer_for(source)
        if item is not None and source not in self.sold_sources:
            self.state.locked_shop_offers[key] = self.state.item_to_data(item)
            self.status = "Offer locked for the next day"

    @property
    def cart_total(self) -> int:
        return sum(item.price for _, item in self.cart)

    def cart_sources(self) -> set[tuple[int, str]]:
        return {source for source, _ in self.cart}

    def add_offer(self, source: tuple[int, str]) -> None:
        if source in self.sold_sources:
            return

        for index, (cart_source, item) in enumerate(self.cart):
            if cart_source == source:
                self.cart.pop(index)
                removed_name = (
                    self.mystery_label(source[0])
                    if source[1] == "mystery"
                    else item.name
                )
                self.status = f"Deselected {removed_name}"
                return

        store_index, offer_kind = source
        item = self.offer_for(source)
        if item is None:
            self.status = "No eligible items available"
            return
        if self.cart_total + item.price > self.state.gold:
            self.status = "Not enough Gold"
            return
        self.cart.append((source, item))
        if offer_kind == "mystery":
            self.status = f"Added {self.mystery_label(store_index)}"
        else:
            self.status = f"Added {item.name}"

    def receipt_row_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(
            self.receipt_rect.left + 12,
            self.receipt_rect.top + 48 + index * 36,
            self.receipt_rect.width - 24,
            34,
        )

    def checkout(self) -> None:
        if not self.cart:
            self.status = "Receipt is empty"
            return
        items = [item for _, item in self.cart]
        if not self.state.buy(items):
            self.status = "Not enough Gold"
            return
        audio.play_sound("money")
        mystery_items = [item for source, item in self.cart if source[1] != "direct"]
        self.sold_sources.update(source for source, _ in self.cart)
        for source, _ in self.cart:
            self.state.locked_shop_offers.pop(self.source_key(source), None)
        self.state.day_shop_sold = [self.source_key(source) for source in self.sold_sources]
        if self.detail_source in self.sold_sources:
            self.detail_sold = True
        self.cart.clear()
        self.status = f"Purchased {len(items)} item(s)"
        self.queue_item_reveals(mystery_items)

    def queue_item_reveals(self, items: list[Item]) -> None:
        self.reveal_queue.extend(items)
        if self.reveal_item is None:
            self.start_next_reveal()

    def start_next_reveal(self) -> None:
        self.reveal_elapsed = 0.0
        self.reveal_phase = "rip"
        self.tear_dragging = False
        self.tear_progress = 0.0
        self.reveal_equip_status = ""
        self.reveal_item = (
            self.reveal_queue.pop(0) if self.reveal_queue else None
        )

    def advance_reveal_phase(self) -> None:
        phases = ("rip", "open", "reveal", "slide", "full")
        if self.reveal_item is None:
            return
        index = phases.index(self.reveal_phase)
        if index == len(phases) - 1:
            self.start_next_reveal()
            if self.reveal_item is None and self.pending_night:
                self.transition_to_night()
            return
        self.reveal_phase = phases[index + 1]
        self.reveal_elapsed = 0.0
        self.tear_dragging = False

    def pack_rect(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, 360, 280)
        rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 55)
        return rect

    def tear_line_rect(self) -> pygame.Rect:
        pack = self.pack_rect()
        return pygame.Rect(pack.left + 32, pack.top + 44, pack.width - 64, 34)

    def reveal_equip_rect(self) -> pygame.Rect:
        rect = pygame.Rect(0, 0, 230, 56)
        rect.center = (800, 590)
        return rect

    def reveal_item_is_equipped(self) -> bool:
        item = self.reveal_item
        if item is None:
            return False
        if item.item_type == "gear":
            return any(equipped is item for equipped in self.state.equipped_gear.values())
        if item.item_type == "upgrade":
            return any(equipped is item for equipped in self.state.equipped_upgrades)
        if item.item_type == "blessing":
            return any(equipped is item for equipped in self.state.blessings)
        return False

    def equip_revealed_item(self) -> None:
        if self.reveal_item is None or self.reveal_item_is_equipped():
            return
        if self.state.auto_equip(self.reveal_item):
            self.reveal_equip_status = "Equipped"
        else:
            self.reveal_equip_status = "No compatible slot available"

    def draw_pack_triangles(
        self,
        pack: pygame.Rect,
        colors: list[tuple[int, int, int]],
    ) -> None:
        rays = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        origin = (pack.centerx, pack.top + 55)
        top_centers = (250, 380, 505, 640, 775, 900, 1030)
        for index, center_x in enumerate(top_centers):
            half_width = 70 if index % 2 else 95
            color = colors[index % len(colors)]
            pygame.draw.polygon(
                rays,
                (*color, 105),
                (
                    origin,
                    (center_x - half_width, 20 + (index % 3) * 18),
                    (center_x + half_width, 20 + (index % 3) * 18),
                ),
            )
        self.screen.blit(rays, (0, 0))

    def transition_to_night(self) -> None:
        self.pending_night = False
        self.state.begin_night()
        self.manager.change(self.next_scene)

    def begin_night(self) -> None:
        self.pending_night = True
        if self.cart:
            self.checkout()
        if self.reveal_item is None:
            self.transition_to_night()

    def close_inventory(self) -> None:
        self.set_subscene(None)

    def open_inventory(self) -> None:
        self.set_subscene(
            InventoryScene(
                self.manager,
                self.screen,
                self.state,
                self.close_inventory,
                self.refresh_tower,
                knowledge_access_mode="day",
            )
        )

    def refresh_tower(self) -> None:
        self.state.apply_tower_upgrades(self.tower)

    def open_knowledge(self) -> None:
        self.set_subscene(
            KnowledgeScene(
                self.manager,
                self.screen,
                self.state,
                self.close_inventory,
                access_mode="day",
            )
        )

    def resume_day(self) -> None:
        self.set_subscene(None)

    def restart(self) -> None:
        self.state.start_new_run(self.state.hero_id)
        self.manager.change("day")

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_i:
            self.open_inventory()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.set_subscene(
                PauseScene(self.manager, self.screen, self.resume_day, self.restart, self.state)
            )
            return

        if self.reveal_item is not None:
            if self.reveal_phase == "rip":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.tear_dragging = True
                    self.tear_start_pos.update(event.pos)
                    self.tear_progress = 0.0
                elif event.type == pygame.MOUSEMOTION and self.tear_dragging:
                    required_distance = self.pack_rect().width * 0.5
                    distance = self.tear_start_pos.distance_to(event.pos)
                    self.tear_progress = min(1.0, distance / required_distance)
                    if self.tear_progress >= 1.0:
                        self.advance_reveal_phase()
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.tear_dragging = False
                    self.tear_progress = 0.0
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if (
                    self.reveal_phase == "full"
                    and self.reveal_equip_rect().collidepoint(event.pos)
                ):
                    if not preferences.auto_equip_enabled:
                        self.equip_revealed_item()
                    return
                self.advance_reveal_phase()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.knowledge_rect.collidepoint(event.pos):
                audio.play_sound("menu_click")
                self.open_knowledge()
                return
            for source in self.option_rects:
                if self.lock_rect(source).collidepoint(event.pos):
                    audio.play_sound("menu_click")
                    self.toggle_lock(source)
                    return
            for index in range(len(self.cart)):
                if self.receipt_row_rect(index).collidepoint(event.pos):
                    audio.play_sound("menu_click")
                    source, item = self.cart.pop(index)
                    self.select_detail(
                        item,
                        source=source,
                        mystery=source[1] != "direct",
                    )
                    removed_name = (
                        self.mystery_label(source[0])
                        if source[1] == "mystery"
                        else item.name
                    )
                    self.status = f"Removed {removed_name}"
                    return
            if self.checkout_rect.collidepoint(event.pos):
                audio.play_sound("menu_click")
                self.checkout()
                return
            for source, rect in self.option_rects.items():
                if rect.collidepoint(event.pos):
                    audio.play_sound("menu_click")
                    _, offer_kind = source
                    if self.detail_source == source:
                        self.clear_detail()
                    else:
                        self.select_detail(
                            self.offer_for(source),
                            source=source,
                            mystery=offer_kind != "direct",
                            sold=source in self.sold_sources,
                        )
                    self.add_offer(source)
                    return

            self.clear_detail()

        self.skip_button.handle_event(event)

    def on_update(self, dt: float) -> None:
        if self.reveal_item is not None:
            if self.reveal_phase not in ("rip", "full"):
                self.reveal_elapsed += dt
                durations = {
                    "open": PACK_OPEN_DURATION,
                    "reveal": PACK_REVEAL_DURATION,
                    "slide": PACK_SLIDE_DURATION,
                }
                if self.reveal_elapsed >= durations[self.reveal_phase]:
                    self.advance_reveal_phase()
            return

        self.elapsed += dt
        self.state.day_elapsed = self.elapsed
        if not self.is_first_day and self.elapsed >= DAY_DURATION:
            self.begin_night()

    def capture_state(self) -> None:
        if self.state.day_active:
            self.state.day_elapsed = self.elapsed

    def draw_store(self, index: int, title: str, item_type: str) -> None:
        direct_rect = self.option_rects[(index, "direct")]
        card = pygame.Rect(
            direct_rect.left - 14,
            190,
            *DAY_CARD_SIZE,
        )
        pygame.draw.rect(self.screen, DAY_CARD_COLOR, card, border_radius=10)
        heading = self.store_font.render(title, True, MENU_TEXT_COLOR)
        self.screen.blit(heading, heading.get_rect(center=(card.centerx, 225)))

        for kind in ("direct", "mystery"):
            source = (index, kind)
            rect = self.option_rects[source]
            offer = self.offer_for(source)
            if source in self.sold_sources:
                self.draw_sold(rect)
            elif offer is None:
                self.draw_unavailable(rect)
            elif kind == "direct":
                offer.draw(self.screen, rect, self.item_font)
            else:
                collector = offer.price == 5
                color = (92, 67, 27) if collector else (65, 52, 75)
                pygame.draw.rect(self.screen, color, rect, border_radius=8)
                pygame.draw.rect(self.screen, (20, 20, 20), rect, width=2, border_radius=8)
                question = ui_font(54).render("?", True, MENU_TEXT_COLOR)
                self.screen.blit(
                    question,
                    question.get_rect(center=(rect.centerx, rect.centery - 12)),
                )
                label = "Collector" if collector else "Mystery"
                text = Item.fit_label(label, self.item_font, rect.width - 10)
                self.screen.blit(
                    text,
                    text.get_rect(midbottom=(rect.centerx, rect.bottom - 7)),
                )
            if source in self.cart_sources():
                pygame.draw.rect(
                    self.screen,
                    (255, 215, 60),
                    rect,
                    width=4,
                    border_radius=8,
                )
            if offer is None:
                continue
            price = self.item_font.render(
                f"{offer.price} Gold",
                True,
                MENU_TEXT_COLOR,
            )
            self.screen.blit(price, price.get_rect(center=(rect.centerx, rect.bottom + 18)))
            lock = self.lock_rect(source)
            locked = self.source_key(source) in self.state.locked_shop_offers
            lock_color = (220, 175, 55) if locked else (35, 35, 35)
            pygame.draw.rect(self.screen, lock_color, lock, border_radius=3)
            marker = self.small_lock_text("L" if locked else "")
            self.screen.blit(marker, marker.get_rect(center=lock.center))

    def small_lock_text(self, text: str) -> pygame.Surface:
        return self.item_font.render(text, True, (15, 15, 15))

    def draw_sold(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (45, 45, 45), rect, border_radius=8)
        sold = self.store_font.render("SOLD", True, (160, 160, 160))
        self.screen.blit(sold, sold.get_rect(center=rect.center))

    def draw_unavailable(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (45, 45, 45), rect, border_radius=8)
        label = self.item_font.render("No Offer", True, (160, 160, 160))
        self.screen.blit(label, label.get_rect(center=rect.center))

    def draw_receipt(self) -> None:
        pygame.draw.rect(
            self.screen,
            DAY_RECEIPT_COLOR,
            self.receipt_rect,
            border_radius=8,
        )
        pygame.draw.rect(
            self.screen,
            (35, 35, 35),
            self.receipt_rect,
            width=3,
            border_radius=8,
        )
        title = self.store_font.render("RECEIPT", True, DAY_RECEIPT_TEXT_COLOR)
        self.screen.blit(
            title,
            title.get_rect(midtop=(self.receipt_rect.centerx, self.receipt_rect.top + 8)),
        )

        for index, (source, item) in enumerate(self.cart):
            row = self.receipt_row_rect(index)
            is_mystery = source[1] == "mystery"
            row_color = (65, 52, 75) if is_mystery else item.color
            item_label = (
                self.mystery_label(source[0])
                if is_mystery
                else item.name
            )
            pygame.draw.rect(self.screen, row_color, row, border_radius=4)
            cost = self.receipt_font.render(
                f"{item.price} G",
                True,
                (255, 255, 255),
            )
            label = Item.fit_label(
                item_label,
                self.receipt_font,
                row.width - cost.get_width() - 28,
            )
            self.screen.blit(
                label,
                label.get_rect(midleft=(row.left + 9, row.centery)),
            )
            self.screen.blit(cost, cost.get_rect(midright=(row.right - 6, row.centery)))

        total = self.receipt_font.render(
            f"Total: {self.cart_total} Gold",
            True,
            DAY_RECEIPT_TEXT_COLOR,
        )
        self.screen.blit(
            total,
            total.get_rect(
                midleft=(self.receipt_rect.left + 14, self.checkout_rect.centery)
            ),
        )
        pygame.draw.rect(self.screen, (70, 105, 70), self.checkout_rect, border_radius=5)
        checkout = self.receipt_font.render("Checkout", True, (255, 255, 255))
        self.screen.blit(checkout, checkout.get_rect(center=self.checkout_rect.center))

    def draw_item_reveal(self) -> None:
        if self.reveal_item is None:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(ITEM_REVEAL_OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))

        pack = self.pack_rect()
        pack_color = (96, 64, 42) if self.reveal_item.price == 5 else (70, 49, 78)

        if self.reveal_phase in ("rip", "open", "reveal"):
            pygame.draw.rect(self.screen, pack_color, pack, border_radius=18)
            pygame.draw.rect(self.screen, (30, 24, 25), pack, width=4, border_radius=18)
            flap = pygame.Rect(pack.left + 12, pack.top + 12, pack.width - 24, 62)
            flap_color = tuple(max(0, channel - 18) for channel in pack_color)
            pygame.draw.rect(self.screen, flap_color, flap, border_radius=12)
            title = self.store_font.render("MYSTERY PACK", True, (235, 225, 210))
            self.screen.blit(title, title.get_rect(center=(pack.centerx, pack.centery + 34)))
            if self.reveal_phase != "rip":
                tear_y = pack.top + 60
                torn_edge = [(pack.left + 24, tear_y)]
                for index in range(9):
                    torn_edge.append(
                        (
                            pack.left + 24 + index * (pack.width - 48) // 8,
                            tear_y + (9 if index % 2 else -5),
                        )
                    )
                torn_edge.append((pack.right - 24, tear_y - 24))
                torn_edge.append((pack.left + 24, tear_y - 24))
                pygame.draw.polygon(self.screen, (18, 16, 20), torn_edge)

        if self.reveal_phase == "rip":
            line = self.tear_line_rect()
            segment_width = 18
            revealed_width = round(line.width * self.tear_progress)
            for x in range(line.left, line.right, segment_width * 2):
                pygame.draw.line(
                    self.screen,
                    (235, 225, 210),
                    (x, line.centery),
                    (min(x + segment_width, line.right), line.centery),
                    3,
                )
            if revealed_width > 0:
                pygame.draw.line(
                    self.screen,
                    (225, 75, 70),
                    (line.left, line.centery),
                    (line.left + revealed_width, line.centery),
                    4,
                )
            prompt = self.item_font.render(
                "Click anywhere and drag at least half the pack width",
                True,
                (245, 240, 225),
            )
            self.screen.blit(prompt, prompt.get_rect(center=(pack.centerx, pack.bottom + 30)))
            return

        target_center = pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 80)
        square = pygame.Rect(0, 0, ITEM_REVEAL_SQUARE_SIZE, ITEM_REVEAL_SQUARE_SIZE)

        if self.reveal_phase == "open":
            progress = min(1.0, self.reveal_elapsed / PACK_OPEN_DURATION)
            colors = [ITEM_RARITIES[name]["color"] for name in PACK_RARITY_ORDER]
            if progress >= 0.78:
                ray_colors = [self.reveal_item.color]
            else:
                start = int(self.reveal_elapsed * 7) % len(colors)
                ray_colors = colors[start:] + colors[:start]
            self.draw_pack_triangles(pack, ray_colors)
            if progress >= 0.55:
                extraction = (progress - 0.55) / 0.45
                eased = 1.0 - (1.0 - extraction) ** 3
                start = pygame.Vector2(pack.centerx, pack.top + 54)
                square.center = start.lerp(target_center, eased)
                self.reveal_item.draw(self.screen, square, self.item_font)
            hint = self.rate_font.render("Click to skip", True, (210, 210, 215))
            self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 35)))
            return

        if self.reveal_phase == "reveal":
            self.draw_pack_triangles(pack, [self.reveal_item.color])
            square.center = target_center
            self.reveal_item.draw(self.screen, square, self.item_font)
        else:
            progress = (
                min(1.0, self.reveal_elapsed / PACK_SLIDE_DURATION)
                if self.reveal_phase == "slide"
                else 1.0
            )
            eased = 1.0 - (1.0 - progress) ** 3
            square.center = target_center.lerp((300, SCREEN_HEIGHT / 2), eased)
            self.reveal_item.draw(self.screen, square, self.item_font)
            final_panel = pygame.Rect(505, 225, 600, 320)
            panel = final_panel.move(round((1.0 - eased) * (SCREEN_WIDTH - final_panel.left)), 0)
            self.detail_panel.draw(self.screen, panel, self.reveal_item)

        hint_text = "Click to continue" if self.reveal_phase == "full" else "Click to skip"
        hint = self.rate_font.render(hint_text, True, (210, 210, 215))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 35)))
        if self.reveal_phase == "full":
            equip_rect = self.reveal_equip_rect()
            equipped = preferences.auto_equip_enabled or self.reveal_item_is_equipped()
            pygame.draw.rect(
                self.screen,
                (55, 125, 75) if equipped else (45, 85, 145),
                equip_rect,
                border_radius=8,
            )
            pygame.draw.rect(
                self.screen,
                (235, 205, 90),
                equip_rect,
                width=2,
                border_radius=8,
            )
            equip_label = self.item_font.render(
                "Equipped" if equipped else "Equip?",
                True,
                (255, 255, 255),
            )
            self.screen.blit(equip_label, equip_label.get_rect(center=equip_rect.center))
            if self.reveal_equip_status:
                status = self.rate_font.render(
                    self.reveal_equip_status,
                    True,
                    (235, 205, 90),
                )
                self.screen.blit(
                    status,
                    status.get_rect(midtop=(equip_rect.centerx, equip_rect.bottom + 8)),
                )

    def draw_sold_detail(self, rect: pygame.Rect, item: Item) -> None:
        pygame.draw.rect(self.screen, (25, 28, 34), rect, border_radius=10)
        pygame.draw.rect(self.screen, (145, 155, 175), rect, width=2, border_radius=10)
        title = self.store_font.render(item.name, True, MENU_TEXT_COLOR)
        self.screen.blit(title, title.get_rect(midtop=(rect.centerx, rect.top + 18)))
        sold = self.title_font.render("SOLD", True, (135, 135, 140))
        sold = pygame.transform.rotate(sold, -12)
        self.screen.blit(sold, sold.get_rect(center=rect.center))

    def draw_hanging_sign(
        self,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        rope_top: int = 0,
    ) -> None:
        chain_color = (68, 61, 55)
        chain_spacing = min(115, rect.width // 3)
        for x in (rect.centerx - chain_spacing, rect.centerx + chain_spacing):
            for y in range(rope_top, rect.top + 6, 8):
                pygame.draw.circle(self.screen, chain_color, (x, y), 4, 2)
        pygame.draw.rect(self.screen, (91, 55, 30), rect, border_radius=5)
        inner = rect.inflate(-8, -8)
        pygame.draw.rect(self.screen, (143, 91, 48), inner, border_radius=4)
        pygame.draw.line(
            self.screen,
            (177, 119, 64),
            (inner.left + 8, inner.top + 8),
            (inner.right - 8, inner.top + 8),
            3,
        )
        label = font.render(text, True, (245, 231, 193))
        if label.get_width() > inner.width - 16:
            width = inner.width - 16
            height = max(1, round(label.get_height() * width / label.get_width()))
            label = pygame.transform.smoothscale(label, (width, height))
        self.screen.blit(label, label.get_rect(center=rect.center))

    def draw(self) -> None:
        draw_environment(self.screen, self.tower)
        title_sign = pygame.Rect(0, 8, 410, 66)
        title_sign.centerx = SCREEN_WIDTH // 2
        self.draw_hanging_sign(title_sign, "DAY MARKET", self.title_font)

        if self.is_first_day:
            timer_label = "Explore the market - start the night when ready"
        else:
            remaining = max(0, math.ceil(DAY_DURATION - self.elapsed))
            timer_label = f"Night in {remaining}s"
        timer_sign = pygame.Rect(0, 108, 600, 45)
        timer_sign.centerx = SCREEN_WIDTH // 2
        self.draw_hanging_sign(
            timer_sign,
            timer_label,
            self.item_font,
            rope_top=title_sign.bottom,
        )
        gold_sign = pygame.Rect(18, 8, 205, 58)
        self.draw_hanging_sign(
            gold_sign,
            f"Gold: {self.state.gold}",
            self.store_font,
        )

        pygame.draw.rect(self.screen, (25, 65, 135), self.knowledge_rect, border_radius=10)
        pygame.draw.rect(
            self.screen,
            (245, 245, 250),
            self.knowledge_rect,
            width=3,
            border_radius=10,
        )
        pygame.draw.line(
            self.screen,
            (245, 195, 70),
            (self.knowledge_rect.left + 8, self.knowledge_rect.bottom - 8),
            (self.knowledge_rect.right - 8, self.knowledge_rect.bottom - 8),
            3,
        )
        book_rect = pygame.Rect(
            self.knowledge_rect.left + 12,
            self.knowledge_rect.top + 8,
            52,
            52,
        )
        book_image = load_ui_image(KNOWLEDGE_BOOK_PATH, book_rect.size)
        if book_image is not None:
            self.screen.blit(book_image, book_rect)
        knowledge = self.store_font.render(
            str(self.state.hero_knowledge_points()),
            True,
            MENU_TEXT_COLOR,
        )
        self.screen.blit(
            knowledge,
            knowledge.get_rect(
                center=(self.knowledge_rect.left + 119, self.knowledge_rect.centery)
            ),
        )

        for index, (title, item_type) in enumerate(STORES):
            self.draw_store(index, title, item_type)

        status = self.item_font.render(self.status, True, MENU_TEXT_COLOR)
        self.screen.blit(status, (20, self.skip_button.rect.top - 28))
        self.draw_receipt()
        self.skip_button.display(self.screen)
        moon_center = (self.skip_button.rect.left + 38, self.skip_button.rect.centery)
        pygame.draw.circle(self.screen, (255, 224, 120), moon_center, 18)
        pygame.draw.circle(
            self.screen,
            (24, 35, 68),
            (moon_center[0] + 8, moon_center[1] - 5),
            16,
        )
        if self.detail_item is not None:
            detail_rect = pygame.Rect(300, 390, 535, 270)
            if self.detail_sold:
                self.draw_sold_detail(detail_rect, self.detail_item)
            else:
                rarity_rates = None
                if self.detail_mystery and self.detail_source is not None:
                    store_index = self.detail_source[0]
                    item_type = STORES[store_index][1]
                    rarity_rates = self.mystery_rates(
                        item_type,
                        self.detail_item.price == 5,
                    )
                self.detail_panel.draw(
                    self.screen,
                    detail_rect,
                    self.detail_item,
                    mystery=self.detail_mystery,
                    rarity_rates=rarity_rates,
                )
        self.draw_item_reveal()
