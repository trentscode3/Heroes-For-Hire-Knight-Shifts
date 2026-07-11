import math

from core.settings import PIXELS_PER_METER


def pixels_to_meters(pixels: float) -> int:
    """Convert a positive logical-pixel distance to the nearest whole meter."""
    return math.floor(max(0.0, pixels) / PIXELS_PER_METER + 0.5)


def meters_label(pixels: float, suffix: str = "m") -> str:
    return f"{pixels_to_meters(pixels)} {suffix}"
