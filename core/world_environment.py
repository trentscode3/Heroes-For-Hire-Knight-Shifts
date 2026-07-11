from collections.abc import Iterable
from typing import TYPE_CHECKING

import pygame

from core.settings import (
    DAY_BG_COLOR,
    GRASS_BACKGROUND_PATH,
    INCOMING_NIGHT_SHADER_COLOR,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TREE_BORDER_PATH,
)
from sprites import Tower

if TYPE_CHECKING:
    from core.game_state import GameState


_background_image: pygame.Surface | None = None
_tree_border_image: pygame.Surface | None = None
_shader_cache: dict[tuple[tuple[int, int], int], pygame.Surface] = {}
_tinted_border_cache: dict[tuple[int, int, int], pygame.Surface] = {}


def load_environment_images() -> tuple[pygame.Surface | None, pygame.Surface | None]:
    global _background_image, _tree_border_image
    if _background_image is None:
        try:
            background = pygame.image.load(GRASS_BACKGROUND_PATH).convert_alpha()
            _background_image = pygame.transform.scale(
                background,
                (SCREEN_WIDTH, SCREEN_HEIGHT),
            )
        except (FileNotFoundError, pygame.error):
            pass
    if _tree_border_image is None:
        try:
            border = pygame.image.load(TREE_BORDER_PATH).convert_alpha()
            border = pygame.transform.scale(border, (SCREEN_WIDTH, SCREEN_HEIGHT))
            # Remove the near-white matte while preserving the anti-aliased trees.
            pygame.transform.threshold(
                border,
                border,
                (255, 255, 255, 255),
                (80, 80, 80, 0),
                (0, 0, 0, 0),
                1,
                None,
                True,
            )
            _tree_border_image = border
        except (FileNotFoundError, pygame.error):
            pass
    return _background_image, _tree_border_image


def create_tower(
    state: "GameState",
    center: tuple[float, float],
) -> Tower:
    tower = Tower(center)
    state.apply_tower_upgrades(tower)
    tower.health = max(0.0, min(tower.max_health, state.tower_health))
    tower.refresh_health_frame()
    tower.demotion_shake_timer = 0.0
    return tower


def apply_night_shader(surface: pygame.Surface, strength: float = 1.0) -> None:
    """Tint an already drawn environment without tinting its actors or UI."""
    strength = max(0.0, min(1.0, strength))
    if strength <= 0:
        return
    red, green, blue, alpha = INCOMING_NIGHT_SHADER_COLOR
    scaled_alpha = round(alpha * strength)
    key = (surface.get_size(), scaled_alpha)
    shader = _shader_cache.get(key)
    if shader is None:
        shader = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shader.fill((red, green, blue, scaled_alpha))
        _shader_cache[key] = shader
    surface.blit(shader, (0, 0))


def draw_environment(
    surface: pygame.Surface,
    tower: Tower,
    night_strength: float = 0.0,
    include_border: bool = True,
    background_sprites: pygame.sprite.AbstractGroup | None = None,
    draw_tower: bool = True,
) -> None:
    surface.fill(DAY_BG_COLOR)
    background, border = load_environment_images()
    if background is not None:
        surface.blit(background, (0, 0))
    if background_sprites is not None:
        background_sprites.draw(surface)
    if draw_tower:
        tower.display(surface)
    if include_border and border is not None:
        surface.blit(border, (0, 0))
    apply_night_shader(surface, night_strength)


def draw_tower_with_reveal(
    surface: pygame.Surface,
    tower: Tower,
    occluders: Iterable,
    layer: pygame.Surface,
    alpha_mask: pygame.Surface,
    night_strength: float = 1.0,
) -> None:
    """Draw the tower above actors with a soft local visibility window."""
    layer.fill((0, 0, 0, 0))
    alpha_mask.fill((255, 255, 255, 255))
    tower.display(layer)
    strength = max(0.0, min(1.0, night_strength))
    multiplier = tuple(
        round(255 + (channel - 255) * strength)
        for channel in (105, 111, 138)
    )
    layer.fill((*multiplier, 255), special_flags=pygame.BLEND_RGBA_MULT)
    radius = max(42, tower.rect.width // 2)
    for actor in occluders:
        if not tower.rect.inflate(12, 12).colliderect(actor.rect):
            continue
        center = actor.hitbox.center
        for step in range(8, 0, -1):
            progress = (8 - step) / 7
            alpha = round(255 + (72 - 255) * progress)
            pygame.draw.circle(
                alpha_mask,
                (255, 255, 255, alpha),
                center,
                max(1, round(radius * step / 8)),
            )
    layer.blit(alpha_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(layer, (0, 0))


def draw_environment_border(
    surface: pygame.Surface,
    night_strength: float = 0.0,
) -> None:
    """Draw the tree frame over world actors, with the matching night tint."""
    _, border = load_environment_images()
    if border is None:
        return
    strength = max(0.0, min(1.0, night_strength))
    if strength <= 0:
        surface.blit(border, (0, 0))
        return
    full_night_multiplier = (105, 111, 138)
    multiplier = tuple(
        round(255 + (channel - 255) * strength)
        for channel in full_night_multiplier
    )
    tinted = _tinted_border_cache.get(multiplier)
    if tinted is None:
        tinted = border.copy()
        tinted.fill((*multiplier, 255), special_flags=pygame.BLEND_RGBA_MULT)
        _tinted_border_cache[multiplier] = tinted
    surface.blit(tinted, (0, 0))
