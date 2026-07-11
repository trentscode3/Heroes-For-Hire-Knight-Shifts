import pygame

from core.ui_font import ui_font

from items import Blessing, Gear, Item, TowerUpgrade
from core.settings import (
    ITEM_DETAIL_BORDER_COLOR,
    ITEM_DETAIL_GRAPHIC_SIZE,
    ITEM_DETAIL_PANEL_COLOR,
    ITEM_DETAIL_TEXT_SIZE,
    ITEM_DETAIL_TITLE_SIZE,
    ITEM_RARITIES,
    MENU_TEXT_COLOR,
)
from .detail_panel import draw_panel, wrap_text


class ItemDetailPanel:
    """Reusable non-modal description card for every item menu."""

    def __init__(self) -> None:
        self.title_font = ui_font(ITEM_DETAIL_TITLE_SIZE)
        self.text_font = ui_font(ITEM_DETAIL_TEXT_SIZE)

    def wrap_text(self, text: str, max_width: int) -> list[str]:
        return wrap_text(self.text_font, text, max_width)

    @staticmethod
    def item_kind(item: Item) -> str:
        if isinstance(item, Gear):
            return f"{item.gear_type.title()} gear"
        if isinstance(item, TowerUpgrade):
            return "Tower Upgrade"
        if isinstance(item, Blessing):
            return "Blessing"
        return item.item_type.title()

    @staticmethod
    def mechanics(item: Item) -> tuple[str, tuple[str, ...]] | None:
        if isinstance(item, Gear):
            return "Effects", item.effect_lines
        if isinstance(item, TowerUpgrade):
            return "Upgrade Stats", item.stat_lines
        if isinstance(item, Blessing):
            return "Effect", item.effect_lines
        return None

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        item: Item | None,
        mystery: bool = False,
        rarity_rates: dict[str, int] | None = None,
    ) -> None:
        draw_panel(
            surface,
            rect,
            ITEM_DETAIL_PANEL_COLOR,
            ITEM_DETAIL_BORDER_COLOR,
        )

        graphic = pygame.Rect(0, 0, ITEM_DETAIL_GRAPHIC_SIZE, ITEM_DETAIL_GRAPHIC_SIZE)
        graphic.midleft = (rect.left + 14, rect.centery)
        graphic.left = rect.left + 14
        color = (65, 52, 75) if mystery or item is None else item.color
        pygame.draw.rect(surface, color, graphic, border_radius=8)
        pygame.draw.rect(surface, (12, 12, 15), graphic, width=2, border_radius=8)

        if mystery:
            question = self.title_font.render("?", True, MENU_TEXT_COLOR)
            surface.blit(question, question.get_rect(center=graphic.center))

        if item is not None and not mystery:
            image = item.graphic
            if image is not None:
                scale = min(
                    (graphic.width - 12) / image.get_width(),
                    (graphic.height - 12) / image.get_height(),
                )
                size = (
                    max(1, round(image.get_width() * scale)),
                    max(1, round(image.get_height() * scale)),
                )
                enlarged = pygame.transform.smoothscale(image, size)
                surface.blit(enlarged, enlarged.get_rect(center=graphic.center))

        text_left = graphic.right + 16
        text_width = rect.right - text_left - 14
        if mystery or item is None:
            title_text = (
                "Collector Pack"
                if item is not None and item.price == 5
                else "Mystery Pack"
            )
        else:
            title_text = item.name
        title = self.title_font.render(title_text, True, MENU_TEXT_COLOR)
        if title.get_width() > text_width:
            title = pygame.transform.smoothscale(
                title,
                (text_width, max(1, round(title.get_height() * text_width / title.get_width()))),
            )
        surface.blit(title, (text_left, rect.top + 14))

        if mystery or item is None:
            collector = item is not None and item.price == 5
            kind = "Collector pack" if collector else "Mystery pack"
            description = "Contents are hidden until this item is purchased."
            price = f"Cost: {item.price if item is not None else 2} Gold"
        else:
            kind = self.item_kind(item)
            description = item.description or "No description yet."
            price = f"Cost: {item.price} Gold"

        y = rect.top + 48
        for text, color in ((kind, (185, 195, 215)), (price, (235, 205, 90))):
            label = self.text_font.render(text, True, color)
            surface.blit(label, (text_left, y))
            y += 23
        y += 5
        for line in self.wrap_text(description, text_width):
            label = self.text_font.render(line, True, MENU_TEXT_COLOR)
            surface.blit(label, (text_left, y))
            y += 21

        if mystery and rarity_rates is not None:
            y += 5
            heading_label = self.text_font.render(
                "Current Drop Rates",
                True,
                (235, 205, 90),
            )
            surface.blit(heading_label, (text_left, y))
            y += 22
            for rarity in ("common", "uncommon", "rare", "legendary"):
                rate = rarity_rates.get(rarity, 0)
                label = self.text_font.render(
                    f"{rarity.title()}: {rate}%",
                    True,
                    ITEM_RARITIES[rarity]["color"],
                )
                surface.blit(label, (text_left, y))
                y += 20

        if not mystery and item is not None:
            mechanics = self.mechanics(item)
            if mechanics is not None:
                heading, lines = mechanics
                y += 5
                heading_label = self.text_font.render(
                    heading,
                    True,
                    (235, 205, 90),
                )
                surface.blit(heading_label, (text_left, y))
                y += 22
                for mechanic in lines:
                    for line in self.wrap_text(mechanic, text_width):
                        label = self.text_font.render(
                            f"• {line}",
                            True,
                            (205, 215, 230),
                        )
                        surface.blit(label, (text_left, y))
                        y += 20
