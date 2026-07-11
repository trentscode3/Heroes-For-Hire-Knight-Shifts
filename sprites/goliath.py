from core.settings import (
    GOLIATH_COLOR,
    GOLIATH_HEALTH,
    GOLIATH_PALETTE,
    GOLIATH_SIZE,
    GOLIATH_SPEED_MULTIPLIER,
    KNIGHT_CHARACTER_PATH,
    ORC_ATTACK_ANIMATION_TIME,
    ORC_ATTACK_SPEED,
    ORC_DAMAGE,
    ORC_XP_REWARD,
)
from .boss import Boss


class Goliath(Boss):
    """A two-times-scale Classic Knight boss."""

    SIZE = GOLIATH_SIZE
    TITLE = "Goliath"

    def __init__(self, start_pos: tuple[float, float], speed: float) -> None:
        super().__init__(
            start_pos=start_pos,
            size=GOLIATH_SIZE,
            color=GOLIATH_COLOR,
            speed=speed * GOLIATH_SPEED_MULTIPLIER,
            max_health=GOLIATH_HEALTH,
            damage=ORC_DAMAGE,
            attack_speed=ORC_ATTACK_SPEED,
            attack_animation_time=ORC_ATTACK_ANIMATION_TIME,
            xp_reward=ORC_XP_REWARD,
            character_path=KNIGHT_CHARACTER_PATH,
            palette=GOLIATH_PALETTE,
        )
