from collections.abc import Callable

import pygame

from core.audio_manager import audio


class Scene:
    """Base scene with optional nested subscene support."""

    music_track: str | None = None
    changes_music_as_subscene = False

    def __init__(self, manager: "SceneManager", screen: pygame.Surface) -> None:
        self.manager = manager
        self.screen = screen
        self.subscene: Scene | None = None

    def set_subscene(self, scene: "Scene | None") -> None:
        previous = self.subscene
        self.subscene = scene
        if scene is not None and scene.changes_music_as_subscene:
            if scene.music_track is not None:
                audio.play_music(scene.music_track)
        elif (
            scene is None
            and previous is not None
            and previous.changes_music_as_subscene
            and self.music_track is not None
        ):
            audio.play_music(self.music_track)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.subscene is not None:
            self.subscene.handle_event(event)
        else:
            self.on_event(event)

    def update(self, dt: float) -> None:
        if self.subscene is not None:
            self.subscene.update(dt)
        else:
            self.on_update(dt)

    def display(self) -> None:
        self.draw()
        if self.subscene is not None:
            self.subscene.display()

    def on_event(self, event: pygame.event.Event) -> None:
        pass

    def on_update(self, dt: float) -> None:
        pass

    def capture_state(self) -> None:
        """Copy transient scene state into the persistent game state when needed."""
        pass

    def draw(self) -> None:
        raise NotImplementedError


SceneFactory = Callable[[], Scene]


class SceneManager:
    def __init__(
        self,
        quit_callback: Callable[[], None],
        change_callback: Callable[[str], None] | None = None,
    ) -> None:
        self.quit_callback = quit_callback
        self.change_callback = change_callback
        self.factories: dict[str, SceneFactory] = {}
        self.current: Scene | None = None

    def register(self, name: str, factory: SceneFactory) -> None:
        self.factories[name] = factory

    def change(self, name: str) -> None:
        if name not in self.factories:
            raise KeyError(f"Unknown scene: {name}")
        if self.current is not None:
            self.current.capture_state()
        self.current = self.factories[name]()
        if self.current.music_track is not None:
            audio.play_music(self.current.music_track)
        if self.change_callback is not None:
            self.change_callback(name)

    def quit(self) -> None:
        self.quit_callback()

    def capture_state(self) -> None:
        if self.current is not None:
            self.current.capture_state()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.current is not None:
            self.current.handle_event(event)

    def update(self, dt: float) -> None:
        if self.current is not None:
            self.current.update(dt)

    def display(self) -> None:
        if self.current is not None:
            self.current.display()
