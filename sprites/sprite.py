from pathlib import Path

import pygame

from core.settings import (
    CHARACTER_SHADOW_COLOR,
    SPRITE_HITBOX_HEIGHT_RATIO,
    SPRITE_HITBOX_WIDTH_RATIO,
)


class Sprite(pygame.sprite.Sprite):
    """Base class for visible game objects with a position and image."""

    def __init__(
        self,
        start_pos: tuple[float, float],
        size: tuple[int, int],
        color: pygame.Color | tuple[int, int, int],
        sprite_path: str | Path | None = None,
    ) -> None:
        super().__init__()
        self.collision_group = pygame.sprite.GroupSingle(self)
        self.pos = pygame.Vector2(start_pos)
        self.shadow_image: pygame.Surface | None = None
        self.shadow_rect: pygame.Rect | None = None
        self.shadow_anchor_y_ratio = 1.0

        self.image = pygame.Surface(size, pygame.SRCALPHA)
        self.image.fill(color)

        if sprite_path:
            try:
                loaded_image = pygame.image.load(sprite_path).convert_alpha()
                self.image = pygame.transform.smoothscale(loaded_image, size)
            except (FileNotFoundError, pygame.error):
                # Keep the colored fallback surface when an asset cannot be loaded.
                pass

        self.rect = self.image.get_rect(topleft=(round(self.pos.x), round(self.pos.y)))
        self.hitbox = pygame.Rect(
            0,
            0,
            max(1, round(self.rect.width * SPRITE_HITBOX_WIDTH_RATIO)),
            max(1, round(self.rect.height * SPRITE_HITBOX_HEIGHT_RATIO)),
        )
        self.sync_hitbox()
        self.refresh_collision_mask()

    def sync_hitbox(self) -> None:
        """Center the hitbox on the bottom half of the image."""
        if self.shadow_rect is not None:
            self.shadow_rect.center = (
                self.rect.centerx,
                self.rect.top
                + round(self.rect.height * self.shadow_anchor_y_ratio),
            )
            self.hitbox = self.shadow_rect.copy()
        else:
            self.hitbox.midbottom = self.rect.midbottom

    def refresh_collision_mask(self) -> None:
        """Build a rect-aligned mask from the active collision boundary."""
        self.mask = pygame.Mask(self.rect.size)
        local_hitbox = self.hitbox.move(-self.rect.left, -self.rect.top)
        hitbox_mask = pygame.Mask(local_hitbox.size, fill=True)
        self.mask.draw(hitbox_mask, local_hitbox.topleft)

    def set_collision_shadow(
        self,
        shadow_path: str | Path,
        reference_size: int,
        anchor_y_ratio: float = 1.0,
    ) -> None:
        """Use a scaled shadow image as this sprite's collision boundary."""
        try:
            source_shadow = pygame.image.load(shadow_path).convert_alpha()
        except (FileNotFoundError, pygame.error):
            return

        scale = self.rect.width / reference_size
        tinted_shadow = pygame.Surface(source_shadow.get_size(), pygame.SRCALPHA)
        tinted_shadow.fill((*CHARACTER_SHADOW_COLOR, 255))
        tinted_shadow.blit(
            source_shadow,
            (0, 0),
            special_flags=pygame.BLEND_RGBA_MIN,
        )
        shadow_size = (
            max(1, round(source_shadow.get_width() * scale)),
            max(1, round(source_shadow.get_height() * scale)),
        )
        self.shadow_image = pygame.transform.scale(tinted_shadow, shadow_size)
        self.shadow_anchor_y_ratio = max(0.0, min(1.0, anchor_y_ratio))
        shadow_center = (
            self.rect.centerx,
            self.rect.top + round(self.rect.height * self.shadow_anchor_y_ratio),
        )
        self.shadow_rect = self.shadow_image.get_rect(center=shadow_center)
        self.hitbox = self.shadow_rect.copy()

        local_offset = (
            self.shadow_rect.left - self.rect.left,
            self.shadow_rect.top - self.rect.top,
        )
        mask_size = (
            max(self.rect.width, local_offset[0] + self.shadow_rect.width),
            max(self.rect.height, local_offset[1] + self.shadow_rect.height),
        )
        self.mask = pygame.Mask(mask_size)
        shadow_mask = pygame.mask.from_surface(self.shadow_image)
        self.mask.draw(shadow_mask, local_offset)

    def sync_rect(self) -> None:
        """Keep pygame's integer rectangle aligned with the precise position."""
        self.rect.topleft = (round(self.pos.x), round(self.pos.y))
        self.sync_hitbox()

    def clamp_to(self, bounds: pygame.Rect) -> None:
        """Keep the entire sprite inside the supplied bounds."""
        self.pos.x = max(bounds.left, min(self.pos.x, bounds.right - self.rect.width))
        self.pos.y = max(bounds.top, min(self.pos.y, bounds.bottom - self.rect.height))
        self.sync_rect()

    def update(self, dt: float) -> None:
        """Update the sprite. Subclasses can override this behavior."""
        self.sync_rect()

    def display(self, surface: pygame.Surface) -> None:
        self.display_shadow(surface)
        surface.blit(self.image, self.rect)

    def display_shadow(self, surface: pygame.Surface) -> None:
        if self.shadow_image is not None and self.shadow_rect is not None:
            surface.blit(self.shadow_image, self.shadow_rect)

    @staticmethod
    def animation_frame(elapsed: float, duration: float, frame_count: int) -> int:
        """Return a stable zero-based frame for a timed animation."""
        if duration <= 0 or frame_count <= 1:
            return 0
        progress = max(0.0, min(1.0, elapsed / duration))
        return min(frame_count - 1, int(progress * frame_count))


def collide_hitboxes(left: Sprite, right: Sprite) -> bool:
    """Pygame collision callback using each sprite's collision mask."""
    return pygame.sprite.collide_mask(left, right) is not None


def collide_rect_hitbox(left: Sprite, right: Sprite) -> bool:
    """Pygame collision callback using left's rect and right's hitbox."""
    return left.rect.colliderect(right.hitbox)


def sprites_collide(
    left: Sprite,
    right: Sprite,
    collided=collide_hitboxes,
) -> bool:
    """Check two sprites through Pygame's sprite collision system."""
    return (
        pygame.sprite.spritecollideany(
            left,
            right.collision_group,
            collided,
        )
        is not None
    )
