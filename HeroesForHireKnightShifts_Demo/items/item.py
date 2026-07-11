from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re

import pygame

from core.settings import ITEM_PRICES_BY_RARITY, ITEM_RARITIES, ITEM_TEXT_COLOR


@lru_cache(maxsize=None)
def load_item_image(
    path: str,
    crop: tuple[int, int, int, int] | None = None,
) -> pygame.Surface | None:
    try:
        image = pygame.image.load(path)
        image = image.convert_alpha() if pygame.display.get_surface() else image
        if crop is not None:
            image = image.subsurface(pygame.Rect(crop)).copy()
        return image
    except (FileNotFoundError, pygame.error):
        return None


@dataclass(frozen=True, kw_only=True)
class Item:
    """Base model shared by gear, tower upgrades, and blessings."""

    item_type: str
    rarity: str
    name: str
    item_id: str = ""
    description: str = ""
    image_path: Path | None = None
    image_crop: tuple[int, int, int, int] | None = None
    price: int | None = None

    def __post_init__(self) -> None:
        item_id = self.item_id or re.sub(r"[^a-z0-9]+", "_", self.name.casefold()).strip("_")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", item_id):
            raise ValueError(f"Invalid item_id: {item_id!r}")
        object.__setattr__(self, "item_id", item_id)
        if self.price is None:
            object.__setattr__(self, "price", ITEM_PRICES_BY_RARITY[self.rarity])

    @classmethod
    def random(
        cls,
        item_type: str,
        price: int | None = None,
        excluded_names: set[str] | None = None,
    ) -> "Item | None":
        from .factory import random_item

        return random_item(item_type, price, excluded_names)

    @property
    def color(self) -> tuple[int, int, int]:
        return ITEM_RARITIES[self.rarity]["color"]

    @property
    def graphic(self) -> pygame.Surface | None:
        if self.image_path is None:
            return None
        return load_item_image(str(self.image_path), self.image_crop)

    @staticmethod
    def fit_label(
        text: str,
        font: pygame.font.Font,
        max_width: int,
    ) -> pygame.Surface:
        label = font.render(text, True, ITEM_TEXT_COLOR)
        if label.get_width() <= max_width:
            return label
        scale = max_width / label.get_width()
        return pygame.transform.smoothscale(
            label,
            (max_width, max(1, round(label.get_height() * scale))),
        )

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        font: pygame.font.Font,
    ) -> None:
        pygame.draw.rect(surface, self.color, rect, border_radius=8)
        pygame.draw.rect(surface, (20, 20, 20), rect, width=2, border_radius=8)
        label = self.fit_label(self.name, font, rect.width - 10)
        image = self.graphic
        if image is None:
            surface.blit(label, label.get_rect(center=rect.center))
            return

        label_height = min(label.get_height(), max(10, rect.height // 3))
        available_size = (
            max(1, rect.width - 12),
            max(1, rect.height - label_height - 13),
        )
        scale = min(
            available_size[0] / image.get_width(),
            available_size[1] / image.get_height(),
        )
        image_size = (
            max(1, round(image.get_width() * scale)),
            max(1, round(image.get_height() * scale)),
        )
        displayed_image = pygame.transform.scale(image, image_size)
        image_rect = displayed_image.get_rect(
            center=(rect.centerx, rect.top + 6 + available_size[1] // 2)
        )
        surface.blit(displayed_image, image_rect)

        label_back = pygame.Rect(
            rect.left + 3,
            rect.bottom - label_height - 5,
            rect.width - 6,
            label_height + 3,
        )
        pygame.draw.rect(surface, (15, 15, 18, 175), label_back, border_radius=4)
        surface.blit(
            label,
            label.get_rect(center=(rect.centerx, label_back.centery)),
        )
