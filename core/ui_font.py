from functools import lru_cache

import pygame

from core.asset_paths import font_asset


DETERMINATION_FONT_PATH = font_asset("determination.ttf")
DETERMINATION_BASE_SIZE = 12


@lru_cache(maxsize=None)
def ui_font(size: int | float = DETERMINATION_BASE_SIZE) -> pygame.font.Font:
    """Create the shared Determination UI font at a logical pixel size."""
    logical_size = max(DETERMINATION_BASE_SIZE, round(size))
    return pygame.font.Font(str(DETERMINATION_FONT_PATH), logical_size)
