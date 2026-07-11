import pygame

from core.settings import (
    DEFAULT_DISPLAY_MODE,
    DEFAULT_DISPLAY_RESOLUTION,
    DISPLAY_MODES,
    DISPLAY_RESOLUTIONS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)


class DisplayManager:
    """Renders a fixed logical canvas into a scalable physical display."""

    def __init__(self) -> None:
        self.logical_size = (SCREEN_WIDTH, SCREEN_HEIGHT)
        self.surface = pygame.Surface(self.logical_size)
        self.window: pygame.Surface | None = None
        self.mode = DEFAULT_DISPLAY_MODE
        self.resolution = DEFAULT_DISPLAY_RESOLUTION
        self.physical_size = DEFAULT_DISPLAY_RESOLUTION
        self.viewport = pygame.Rect((0, 0), self.logical_size)
        self.scale = 1.0

    def initialize(self) -> pygame.Surface:
        self.apply(self.resolution, self.mode)
        return self.surface

    @staticmethod
    def desktop_resolution() -> tuple[int, int]:
        try:
            sizes = pygame.display.get_desktop_sizes()
        except pygame.error:
            sizes = []
        return tuple(sizes[0]) if sizes else DEFAULT_DISPLAY_RESOLUTION

    def apply(self, resolution: tuple[int, int], mode: str) -> None:
        if resolution not in DISPLAY_RESOLUTIONS:
            raise ValueError(f"Unsupported display resolution: {resolution}")
        if mode not in DISPLAY_MODES:
            raise ValueError(f"Unsupported display mode: {mode}")

        self.resolution = resolution
        self.mode = mode
        flags = 0
        target_size = resolution
        if mode == "Borderless":
            flags = pygame.NOFRAME
            target_size = self.desktop_resolution()
        elif mode == "Fullscreen":
            flags = pygame.FULLSCREEN

        try:
            self.window = pygame.display.set_mode(target_size, flags)
        except pygame.error:
            # A requested exclusive resolution may not be supported by the
            # current monitor. Fall back safely while retaining the selection.
            self.mode = "Windowed"
            self.window = pygame.display.set_mode(resolution)

        self.physical_size = self.window.get_size()
        self._calculate_viewport()

    def _calculate_viewport(self) -> None:
        physical_width, physical_height = self.physical_size
        logical_width, logical_height = self.logical_size
        self.scale = min(
            physical_width / logical_width,
            physical_height / logical_height,
        )
        scaled_size = (
            max(1, round(logical_width * self.scale)),
            max(1, round(logical_height * self.scale)),
        )
        self.viewport = pygame.Rect((0, 0), scaled_size)
        self.viewport.center = (physical_width // 2, physical_height // 2)

    def logical_position(
        self,
        physical_position: tuple[int, int],
        clamp: bool = False,
    ) -> tuple[int, int]:
        if not self.viewport.collidepoint(physical_position):
            if not clamp:
                return (-1, -1)
            physical_position = (
                max(self.viewport.left, min(physical_position[0], self.viewport.right - 1)),
                max(self.viewport.top, min(physical_position[1], self.viewport.bottom - 1)),
            )
        return (
            round((physical_position[0] - self.viewport.left) / self.scale),
            round((physical_position[1] - self.viewport.top) / self.scale),
        )

    def mouse_position(self, clamp: bool = False) -> tuple[int, int]:
        return self.logical_position(pygame.mouse.get_pos(), clamp)

    def logical_event(self, event: pygame.event.Event) -> pygame.event.Event:
        if event.type not in (
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
        ):
            return event
        values = event.dict.copy()
        if "pos" in values:
            values["pos"] = self.logical_position(values["pos"])
        if "rel" in values:
            values["rel"] = (
                round(values["rel"][0] / self.scale),
                round(values["rel"][1] / self.scale),
            )
        return pygame.event.Event(event.type, values)

    def present(self) -> None:
        if self.window is None:
            return
        self.window.fill((0, 0, 0))
        if self.viewport.size == self.logical_size:
            scaled = self.surface
        else:
            # Linear filtering keeps antialiased fonts legible at fractional
            # scales (for example 1600x900 and 1920x1080). At exact native
            # size no filtering is applied, preserving original pixel detail.
            scaled = pygame.transform.smoothscale(
                self.surface,
                self.viewport.size,
            )
        self.window.blit(scaled, self.viewport)
        pygame.display.flip()


display = DisplayManager()
