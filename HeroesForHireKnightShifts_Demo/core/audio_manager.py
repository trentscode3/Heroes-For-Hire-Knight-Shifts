from pathlib import Path

import pygame

from core.asset_paths import PROJECT_ROOT
from core.settings import (
    DEFAULT_MASTER_VOLUME,
    DEFAULT_MUSIC_VOLUME,
    DEFAULT_SOUND_VOLUME,
    MUSIC_PATHS,
    SOUND_PATHS,
)


class AudioManager:
    """Loads configured audio lazily and applies independent volume groups."""

    def __init__(self) -> None:
        self.master_volume = DEFAULT_MASTER_VOLUME
        self.music_volume = DEFAULT_MUSIC_VOLUME
        self.sound_volume = DEFAULT_SOUND_VOLUME
        self.current_music_key: str | None = None
        self._music_loaded = False
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self.available = False

    def initialize(self) -> None:
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            self.available = True
            self._apply_music_volume()
        except pygame.error:
            self.available = False

    @staticmethod
    def _path(configured_path) -> Path | None:
        if not configured_path:
            return None
        path = Path(configured_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path if path.is_file() else None

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _apply_music_volume(self) -> None:
        if self.available:
            pygame.mixer.music.set_volume(self.master_volume * self.music_volume)

    def _apply_sound_volumes(self) -> None:
        volume = self.master_volume * self.sound_volume
        for sound in self._sounds.values():
            sound.set_volume(volume)

    def set_master_volume(self, value: float) -> None:
        self.master_volume = self._clamp(value)
        self._apply_music_volume()
        self._apply_sound_volumes()

    def set_music_volume(self, value: float) -> None:
        self.music_volume = self._clamp(value)
        self._apply_music_volume()

    def set_sound_volume(self, value: float) -> None:
        self.sound_volume = self._clamp(value)
        self._apply_sound_volumes()

    def play_music(self, key: str, loops: int = -1) -> None:
        if not self.available:
            return
        path = self._path(MUSIC_PATHS.get(key))
        if self.current_music_key == key and self._music_loaded:
            return
        self.current_music_key = key
        self._music_loaded = False
        if path is None:
            pygame.mixer.music.stop()
            return
        try:
            pygame.mixer.music.load(str(path))
            self._apply_music_volume()
            pygame.mixer.music.play(loops)
            self._music_loaded = True
        except pygame.error:
            pygame.mixer.music.stop()

    def play_sound(self, key: str) -> None:
        if not self.available:
            return
        sound = self._sounds.get(key)
        if sound is None:
            path = self._path(SOUND_PATHS.get(key))
            if path is None:
                return
            try:
                sound = pygame.mixer.Sound(str(path))
            except pygame.error:
                return
            self._sounds[key] = sound
            sound.set_volume(self.master_volume * self.sound_volume)
        sound.play()

    def stop(self) -> None:
        if self.available:
            pygame.mixer.stop()
            pygame.mixer.music.stop()


audio = AudioManager()
