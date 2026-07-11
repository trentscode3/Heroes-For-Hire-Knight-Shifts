from functools import lru_cache
from pathlib import Path

import pygame


@lru_cache(maxsize=None)
def load_ui_image(
    path: str | Path,
    size: tuple[int, int],
) -> pygame.Surface | None:
    """Load and scale an interface image once, with a safe missing-asset fallback."""
    try:
        image = pygame.image.load(path).convert_alpha()
    except (FileNotFoundError, pygame.error):
        return None
    return pygame.transform.smoothscale(image, size)
