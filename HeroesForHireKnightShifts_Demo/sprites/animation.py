from functools import lru_cache
from pathlib import Path

import pygame

from .palette import ColorKey, replace_palette


DIRECTION_PREFIXES = (("down", "D"), ("side", "S"), ("up", "U"))
ANIMATION_STATES = (
    ("idle", "Idle"),
    ("walk", "Walk"),
    ("attack", "Attack"),
    ("death", "Death"),
)


@lru_cache(maxsize=None)
def load_directional_animations(
    character_path: str,
    source_size: tuple[int, int],
    display_size: tuple[int, int],
    palette_items: tuple[tuple[ColorKey, ColorKey], ...] = (),
) -> dict[tuple[str, str], tuple[pygame.Surface, ...]]:
    """Load, recolor, and scale one directional animation set once."""
    root = Path(character_path)
    palette = dict(palette_items)
    animations = {}
    for direction, prefix in DIRECTION_PREFIXES:
        for state, filename_state in ANIMATION_STATES:
            try:
                sheet = pygame.image.load(
                    root / f"{prefix}_{filename_state}.png"
                ).convert_alpha()
            except (FileNotFoundError, pygame.error):
                animations[(direction, state)] = (
                    pygame.Surface(display_size, pygame.SRCALPHA),
                )
                continue

            frame_width, frame_height = source_size
            frames = []
            for index in range(sheet.get_width() // frame_width):
                frame = sheet.subsurface(
                    index * frame_width,
                    0,
                    frame_width,
                    frame_height,
                ).copy()
                if palette:
                    frame = replace_palette(frame, palette)
                frames.append(pygame.transform.scale(frame, display_size))
            animations[(direction, state)] = tuple(frames) or (
                pygame.Surface(display_size, pygame.SRCALPHA),
            )
    return animations
