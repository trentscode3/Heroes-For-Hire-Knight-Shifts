from dataclasses import dataclass


@dataclass
class UserPreferences:
    auto_equip_enabled: bool = False
    screen_shake_strength: float = 1.0


preferences = UserPreferences()
