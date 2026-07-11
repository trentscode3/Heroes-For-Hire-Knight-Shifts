import json
import os
from pathlib import Path

from core.audio_manager import audio
from core.display_manager import display
from core.game_state import GameState
from core.settings import (
    DEFAULT_DISPLAY_MODE,
    DEFAULT_DISPLAY_RESOLUTION,
    DEMO_BUILD,
    DISPLAY_MODES,
    DISPLAY_RESOLUTIONS,
)
from core.user_preferences import preferences


SAVE_VERSION = 11
PREFERENCES_VERSION = 4
SAVE_SLOT_COUNT = 4


class SaveManager:
    """Versioned, atomic persistence for profile data and user preferences."""

    def __init__(self) -> None:
        override = os.environ.get("KNIGHT_SHIFTS_SAVE_DIR")
        if override:
            root = Path(override)
        elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
            root = Path(os.environ["LOCALAPPDATA"])
        elif os.environ.get("XDG_DATA_HOME"):
            root = Path(os.environ["XDG_DATA_HOME"])
        else:
            root = Path.home() / ".local" / "share"
        save_folder = "Knight Shifts Demo" if DEMO_BUILD else "Knight Shifts"
        self.directory = root / save_folder
        self.active_slot = 1
        self.legacy_profile_path = self.directory / "profile.json"
        self.preferences_path = self.directory / "preferences.json"

    def slot_path(self, slot: int) -> Path:
        self.validate_slot(slot)
        return self.directory / f"profile_{slot}.json"

    @staticmethod
    def validate_slot(slot: int) -> None:
        if not 1 <= slot <= SAVE_SLOT_COUNT:
            raise ValueError(f"Save slot must be between 1 and {SAVE_SLOT_COUNT}")

    def _profile_data(self, slot: int) -> dict | None:
        data = self._read(self.slot_path(slot))
        if data is None and slot == 1:
            data = self._read(self.legacy_profile_path)
        return data

    @staticmethod
    def _read(path: Path) -> dict | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _write_atomic(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(data, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temporary.replace(path)

    def load_profile(self, slot: int | None = None) -> tuple[GameState, bool]:
        slot = self.active_slot if slot is None else slot
        self.validate_slot(slot)
        data = self._profile_data(slot)
        if data is None:
            return GameState(), True
        payload = data.get("state", {})
        if not isinstance(payload, dict):
            return GameState(), True
        return GameState.from_save_data(payload), False

    def save_profile(self, state: GameState, slot: int | None = None) -> None:
        slot = self.active_slot if slot is None else slot
        self._write_atomic(
            self.slot_path(slot),
            {"version": SAVE_VERSION, "state": state.to_save_data()},
        )

    def select_slot(self, slot: int) -> None:
        self.validate_slot(slot)
        self.active_slot = slot
        self.save_preferences()

    def delete_slot(self, slot: int) -> None:
        self.validate_slot(slot)
        paths = [self.slot_path(slot)]
        if slot == 1:
            paths.append(self.legacy_profile_path)
        for path in paths:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def slot_summary(self, slot: int) -> dict | None:
        data = self._profile_data(slot)
        if data is None or not isinstance(data.get("state"), dict):
            return None
        state = data["state"]
        stats = state.get("lifetime_stats", {})
        return {
            "hero_id": state.get("hero_id", "warrior"),
            "night_count": max(0, int(state.get("night_count", 0))),
            "games_played": max(0, int(stats.get("games_played", 0))),
            "longest_employment": max(
                0,
                int(stats.get("longest_employment", 0)),
            ),
            "run_active": bool(state.get("run_active", False)),
            "resume_scene": state.get("resume_scene", "day"),
        }

    def load_preferences(self) -> None:
        data = self._read(self.preferences_path) or {}
        active_slot = data.get("active_slot", 1)
        resolution = tuple(data.get("resolution", DEFAULT_DISPLAY_RESOLUTION))
        mode = data.get("display_mode", DEFAULT_DISPLAY_MODE)
        if resolution in DISPLAY_RESOLUTIONS:
            display.resolution = resolution
        if mode in DISPLAY_MODES:
            display.mode = mode
        if isinstance(active_slot, int) and 1 <= active_slot <= SAVE_SLOT_COUNT:
            self.active_slot = active_slot
        audio.master_volume = audio._clamp(data.get("master_volume", audio.master_volume))
        audio.music_volume = audio._clamp(data.get("music_volume", audio.music_volume))
        audio.sound_volume = audio._clamp(data.get("sound_volume", audio.sound_volume))
        preferences.auto_equip_enabled = bool(data.get("auto_equip_enabled", False))
        try:
            screen_shake_strength = float(data.get("screen_shake_strength", 1.0))
        except (TypeError, ValueError):
            screen_shake_strength = 1.0
        preferences.screen_shake_strength = max(
            0.0,
            min(1.0, screen_shake_strength),
        )

    def save_preferences(self) -> None:
        self._write_atomic(
            self.preferences_path,
            {
                "version": PREFERENCES_VERSION,
                "active_slot": self.active_slot,
                "resolution": list(display.resolution),
                "display_mode": display.mode,
                "master_volume": audio.master_volume,
                "music_volume": audio.music_volume,
                "sound_volume": audio.sound_volume,
                "auto_equip_enabled": preferences.auto_equip_enabled,
                "screen_shake_strength": preferences.screen_shake_strength,
            },
        )

    def save_all(self, state: GameState) -> None:
        self.save_profile(state)
        self.save_preferences()


save_manager = SaveManager()
