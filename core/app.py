import pygame

from core.audio_manager import audio
from core.display_manager import display
from core.game_state import GameState
from scenes import (
    DayScene,
    DebugGame,
    GameScene,
    HeroSelectScene,
    HiredScene,
    IncomingNightScene,
    MainMenuScene,
    ReturnToDayScene,
    SaveSlotsScene,
    SettingsScene,
    TitleScene,
    PromotionsScene,
    WaveSelectScene,
)
from scenes.game_scene import WAVES
from scenes.scene import SceneManager
from core.save_manager import save_manager
from core.settings import GAME_TITLE


class Game:
    """Application loop and top-level scene owner."""

    def __init__(self) -> None:
        pygame.init()
        save_manager.load_preferences()
        audio.initialize()
        self.screen = display.initialize()
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state, first_launch = save_manager.load_profile()
        if first_launch:
            self.state.start_new_run("warrior")
        self.debug_state = GameState()
        self.autosave_elapsed = 0.0

        self.scenes = SceneManager(self.quit, self.on_scene_change)
        self.scenes.register(
            "title", lambda: TitleScene(self.scenes, self.screen)
        )
        self.scenes.register(
            "main_menu",
            lambda: MainMenuScene(self.scenes, self.screen, self.state),
        )
        self.scenes.register(
            "settings", lambda: SettingsScene(self.scenes, self.screen)
        )
        self.scenes.register(
            "save_slots",
            lambda: SaveSlotsScene(
                self.scenes,
                self.screen,
                self.select_save_slot,
                self.delete_save_slot,
            ),
        )
        self.scenes.register(
            "promotions",
            lambda: PromotionsScene(self.scenes, self.screen, self.state),
        )
        self.scenes.register(
            "game", lambda: GameScene(self.scenes, self.screen, self.state)
        )
        self.scenes.register(
            "incoming",
            lambda: IncomingNightScene(
                self.scenes, self.screen, self.state, "game"
            ),
        )
        self.scenes.register(
            "outgoing",
            lambda: ReturnToDayScene(
                self.scenes, self.screen, self.state, "day"
            ),
        )
        self.scenes.register(
            "hero_select",
            lambda: HeroSelectScene(
                self.scenes, self.screen, self.state, "day"
            ),
        )
        self.scenes.register(
            "hired",
            lambda: HiredScene(self.scenes, self.screen, "day"),
        )
        self.scenes.register(
            "hero_select_debug",
            lambda: HeroSelectScene(
                self.scenes,
                self.screen,
                self.debug_state,
                "wave_select",
                debug_mode=True,
            ),
        )
        self.scenes.register(
            "wave_select", lambda: WaveSelectScene(self.scenes, self.screen)
        )
        for wave_index in range(len(WAVES)):
            self.scenes.register(
                f"debug_game_{wave_index}",
                lambda wave_index=wave_index: DebugGame(
                    self.scenes,
                    self.screen,
                    wave_index,
                    self.debug_state,
                ),
            )
            self.scenes.register(
                f"debug_incoming_{wave_index}",
                lambda wave_index=wave_index: IncomingNightScene(
                    self.scenes,
                    self.screen,
                    self.debug_state,
                    f"debug_game_{wave_index}",
                ),
            )
            self.scenes.register(
                f"debug_day_{wave_index}",
                lambda wave_index=wave_index: DayScene(
                    self.scenes,
                    self.screen,
                    self.debug_state,
                    next_scene=f"debug_incoming_{wave_index}",
                    debug_mode=True,
                ),
            )
            self.scenes.register(
                f"debug_outgoing_{wave_index}",
                lambda wave_index=wave_index: ReturnToDayScene(
                    self.scenes,
                    self.screen,
                    self.debug_state,
                    f"debug_day_{wave_index}",
                ),
            )
        self.scenes.register(
            "day",
            lambda: DayScene(
                self.scenes, self.screen, self.state, next_scene="incoming"
            ),
        )
        self.scenes.change("title")

    def select_save_slot(self, slot: int) -> None:
        save_manager.save_profile(self.state)
        save_manager.select_slot(slot)
        state, is_new = save_manager.load_profile()
        if is_new:
            state.start_new_run("warrior")
            save_manager.save_profile(state)
        self.state = state
        self.scenes.change("day" if is_new else "main_menu")

    @staticmethod
    def delete_save_slot(slot: int) -> bool:
        if slot == save_manager.active_slot:
            return False
        save_manager.delete_slot(slot)
        return True

    def on_scene_change(self, name: str) -> None:
        if self.state.run_active and name in ("day", "incoming", "game", "outgoing"):
            self.state.resume_scene = name
        save_manager.save_profile(self.state)

    def quit(self) -> None:
        self.scenes.capture_state()
        save_manager.save_all(self.state)
        self.running = False

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.autosave_elapsed += dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                else:
                    self.scenes.handle_event(display.logical_event(event))

            self.scenes.update(dt)
            self.scenes.display()
            display.present()
            if self.autosave_elapsed >= 2.0:
                self.scenes.capture_state()
                save_manager.save_all(self.state)
                self.autosave_elapsed = 0.0

        pygame.quit()

