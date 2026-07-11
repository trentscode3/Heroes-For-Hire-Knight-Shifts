import sys
from pathlib import Path


def _project_root() -> Path:
    """Return the source root or PyInstaller extraction root when frozen."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _project_root()
ASSET_ROOT = PROJECT_ROOT / "assets"
IMAGE_ASSET_ROOT = ASSET_ROOT / "images"
SPRITE_ASSET_ROOT = IMAGE_ASSET_ROOT / "sprites"
CHARACTER_ASSET_ROOT = SPRITE_ASSET_ROOT / "characters"
DUNGEON_ENEMY_ASSET_ROOT = SPRITE_ASSET_ROOT / "dungeon_enemies"
ITEM_ASSET_ROOT = IMAGE_ASSET_ROOT / "items"
UI_ASSET_ROOT = IMAGE_ASSET_ROOT / "UI"
FONT_ASSET_ROOT = ASSET_ROOT / "fonts"
MUSIC_ASSET_ROOT = ASSET_ROOT / "music"
SOUND_ASSET_ROOT = ASSET_ROOT / "sounds"


def sprite_asset(filename: str) -> Path:
    return SPRITE_ASSET_ROOT / filename


def character_asset(character: str, filename: str | None = None) -> Path:
    character_root = CHARACTER_ASSET_ROOT / character
    return character_root / filename if filename else character_root


def enemy_character_asset(character: str, filename: str | None = None) -> Path:
    character_root = DUNGEON_ENEMY_ASSET_ROOT / character
    return character_root / filename if filename else character_root


def image_asset(*parts: str) -> Path:
    return IMAGE_ASSET_ROOT.joinpath(*parts)


def item_asset(filename: str) -> Path:
    return ITEM_ASSET_ROOT / filename


def ui_asset(filename: str) -> Path:
    return UI_ASSET_ROOT / filename


def font_asset(filename: str) -> Path:
    return FONT_ASSET_ROOT / filename


def music_asset(filename: str) -> Path:
    return MUSIC_ASSET_ROOT / filename


def sound_asset(filename: str) -> Path:
    return SOUND_ASSET_ROOT / filename
