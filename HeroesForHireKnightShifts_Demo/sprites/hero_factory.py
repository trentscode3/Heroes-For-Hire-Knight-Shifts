from .nimbus import Nimbus
from .player import Player
from .robin_hood import RobinHood


HERO_CLASSES = {
    Player.HERO_ID: Player,
    RobinHood.HERO_ID: RobinHood,
    Nimbus.HERO_ID: Nimbus,
}


def create_player(
    hero_id: str,
    start_pos: tuple[float, float] | None = None,
) -> Player:
    try:
        hero_class = HERO_CLASSES[hero_id]
    except KeyError as error:
        raise ValueError(f"Unknown hero: {hero_id}") from error
    return hero_class() if start_pos is None else hero_class(start_pos)
