from core.settings import (
    GOBLIN_ATTACK_SPEED,
    GOBLIN_CHARACTER_PATH,
    GOBLIN_DAMAGE,
    GOBLIN_HEALTH,
    GOBLIN_SOLDIER_ATTACK_SPEED,
    GOBLIN_SOLDIER_CHARACTER_PATH,
    GOBLIN_SOLDIER_DAMAGE,
    GOBLIN_SOLDIER_HEALTH,
    GOBLIN_SOLDIER_SPEED_MULTIPLIER,
    GOBLIN_SOLDIER_XP_REWARD,
    GOBLIN_SPEED_MULTIPLIER,
    GOBLIN_XP_REWARD,
)
from .knight import Knight


class Goblin(Knight):
    CHARACTER_PATH = GOBLIN_CHARACTER_PATH
    HEALTH = GOBLIN_HEALTH
    DAMAGE = GOBLIN_DAMAGE
    ATTACK_SPEED = GOBLIN_ATTACK_SPEED
    SPEED_MULTIPLIER = GOBLIN_SPEED_MULTIPLIER
    XP_REWARD = GOBLIN_XP_REWARD
    PALETTE = {}

    def __init__(self, start_pos: tuple[float, float], speed: float) -> None:
        super().__init__(start_pos, speed)
        self.speed = speed * self.SPEED_MULTIPLIER
        self.max_health = self.HEALTH
        self.health = self.max_health
        self.damage = self.DAMAGE
        self.attack_speed = self.ATTACK_SPEED
        self.xp_reward = self.XP_REWARD

class GoblinSoldier(Goblin):
    CHARACTER_PATH = GOBLIN_SOLDIER_CHARACTER_PATH
    HEALTH = GOBLIN_SOLDIER_HEALTH
    DAMAGE = GOBLIN_SOLDIER_DAMAGE
    ATTACK_SPEED = GOBLIN_SOLDIER_ATTACK_SPEED
    SPEED_MULTIPLIER = GOBLIN_SOLDIER_SPEED_MULTIPLIER
    XP_REWARD = GOBLIN_SOLDIER_XP_REWARD
