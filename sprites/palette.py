import pygame


ColorKey = tuple[int, int, int]


def replace_palette(
    surface: pygame.Surface,
    palette: dict[ColorKey, ColorKey],
) -> pygame.Surface:
    """Replace exact RGB keys while preserving every unlisted pixel."""
    recolored = surface.copy()
    for y in range(recolored.get_height()):
        for x in range(recolored.get_width()):
            color = recolored.get_at((x, y))
            replacement = palette.get(tuple(color[:3]))
            if replacement is not None:
                recolored.set_at((x, y), (*replacement, color.a))
    return recolored
