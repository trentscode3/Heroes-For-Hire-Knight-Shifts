from core.settings import (
    SHAMAN_ATTACK_SPEED,
    SHAMAN_ATTACK_TIME,
    SHAMAN_CHARACTER_PATH,
    SHAMAN_DAMAGE,
    SHAMAN_HEALTH,
    SHAMAN_RANGE,
    SHAMAN_XP_REWARD,
)
from .archer import Archer


class Shaman(Archer):
    CHARACTER_PATH = SHAMAN_CHARACTER_PATH
    PALETTE = {}

    def __init__(self, start_pos: tuple[float, float], speed: float) -> None:
        super().__init__(start_pos, speed)
        self.max_health = SHAMAN_HEALTH
        self.health = self.max_health
        self.damage = SHAMAN_DAMAGE
        self.attack_range = SHAMAN_RANGE
        self.attack_speed = SHAMAN_ATTACK_SPEED
        self.attack_time = SHAMAN_ATTACK_TIME
        self.xp_reward = SHAMAN_XP_REWARD

    def ranged_attack(self, dt: float) -> None:
        if not self.is_attacking:
            self.attack_cooldown -= dt
            if self.attack_cooldown <= 0:
                self.is_attacking = True
                self.attack_windup = max(0.0, -self.attack_cooldown)
                self.attack_cooldown = 0.0
        else:
            self.attack_windup += dt
        if self.is_attacking and self.attack_windup >= self.attack_time:
            self.is_attacking = False
            self.attack_windup = 0.0
            self.attack_cooldown = self.attack_speed
            self.pending_shots.append((self.damage, False))
