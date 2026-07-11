import os

os.environ.setdefault("KNIGHT_SHIFTS_DEMO", "1")

from core.app import Game


if __name__ == "__main__":
    Game().run()
