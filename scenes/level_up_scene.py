import random
from collections.abc import Callable

import pygame

from core.ui_font import ui_font

from core.game_state import GameState
from core.settings import (
    BUTTON_FONT_SIZE,
    LEVEL_UP_BUTTON_SIZE,
    LEVEL_UP_BUTTON_SPACING,
    LEVEL_UP_OPTIONS_DURATION,
    LEVEL_UP_OVERLAY_COLOR,
    LEVEL_UP_TITLE_COLOR,
    LEVEL_UP_TITLE_DURATION,
    LEVEL_UP_TITLE_END_SIZE,
    LEVEL_UP_TITLE_START_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from sprites import Player
from .button import Button
from .scene import Scene
from .pause_scene import PauseScene


class LevelUpScene(Scene):
    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        player: Player,
        on_complete: Callable[[], None],
        state: GameState | None = None,
    ) -> None:
        super().__init__(manager, screen)
        self.player = player
        self.state = state
        self.on_complete = on_complete
        self.elapsed = 0.0
        self.option_progress = 0.0
        self.button_font = ui_font(BUTTON_FONT_SIZE)
        self.skill_button_font = ui_font(29)

        if self.player.HERO_ID == "warrior":
            weighted_options = [
                (30, (None, "+25% damage", self.player.upgrade_damage)),
                (30, (None, "+25% attack speed", self.player.upgrade_attack_speed)),
                (30, (None, "+25% sword swing size", self.player.upgrade_attack_size)),
                (
                    5,
                    (
                        None,
                        "-20% reinforcement spawn time",
                        self.player.upgrade_reinforcement_spawn,
                    ),
                ),
                (
                    5,
                    (
                        None,
                        "+50% reinforcement damage and health",
                        self.player.upgrade_reinforcement_power,
                    ),
                ),
            ]
            selected_options = []
            pool = weighted_options.copy()
            if (
                self.state is not None
                and "whistle" in self.state.hero_knowledge_skills("warrior")
            ):
                pool = [(1, option) for _weight, option in pool]
            while len(selected_options) < 3:
                weights = [weight for weight, _option in pool]
                choice = random.choices(pool, weights=weights, k=1)[0]
                selected_options.append(choice[1])
                pool.remove(choice)
        else:
            range_label = (
                "+25% minimum damage"
                if self.player.HERO_ID == "nimbus"
                else "+25% attack range"
            )
            arc_label = "+25% attack area"
            all_options = (
                (None, "+50% damage", self.player.upgrade_damage),
                (None, "+25% attack speed", self.player.upgrade_attack_speed),
                (None, range_label, self.player.upgrade_attack_radius),
                (None, arc_label, self.player.upgrade_sword_arc),
            )
            selected_options = random.sample(all_options, 3)
        self.buttons = []
        self.option_skill_ids = []
        for skill_id, label, upgrade in selected_options:
            rect = pygame.Rect(0, 0, *LEVEL_UP_BUTTON_SIZE)
            self.option_skill_ids.append(skill_id)
            button = Button(
                rect,
                label,
                self.skill_button_font if skill_id is not None else self.button_font,
                lambda upgrade=upgrade: self.choose(upgrade),
            )
            self.buttons.append(button)

    def choose(self, upgrade: Callable[[], None]) -> None:
        upgrade()
        self.on_complete()

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.state is not None:
            self.set_subscene(
                PauseScene(
                    self.manager,
                    self.screen,
                    lambda: self.set_subscene(None),
                    self.restart,
                    self.state,
                )
            )
            return
        if self.option_progress >= 1.0:
            for button in self.buttons:
                button.handle_event(event)

    def restart(self) -> None:
        if self.state is not None:
            self.state.start_new_run(self.state.hero_id)
        self.manager.change("day")

    def on_update(self, dt: float) -> None:
        self.elapsed += dt
        self.option_progress = max(
            0.0,
            min(
                1.0,
                (self.elapsed - LEVEL_UP_TITLE_DURATION)
                / LEVEL_UP_OPTIONS_DURATION,
            ),
        )

    def draw(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(LEVEL_UP_OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))

        title_progress = min(1.0, self.elapsed / LEVEL_UP_TITLE_DURATION)
        eased_title = 1 - (1 - title_progress) ** 3
        title_size = round(
            LEVEL_UP_TITLE_START_SIZE
            + (LEVEL_UP_TITLE_END_SIZE - LEVEL_UP_TITLE_START_SIZE)
            * eased_title
        )
        title_y = SCREEN_HEIGHT / 2 + (-150) * eased_title
        title_font = ui_font(title_size)
        title = title_font.render(
            f"LEVEL {self.player.level}", True, LEVEL_UP_TITLE_COLOR
        )
        self.screen.blit(
            title, title.get_rect(center=(SCREEN_WIDTH / 2, title_y))
        )

        if self.option_progress <= 0:
            return

        option_count = len(self.buttons)
        for index, button in enumerate(self.buttons):
            staggered = max(
                0.0, min(1.0, self.option_progress * 1.4 - index * 0.2)
            )
            eased = 1 - (1 - staggered) ** 3
            target_x = SCREEN_WIDTH / 2
            start_x = SCREEN_WIDTH + LEVEL_UP_BUTTON_SIZE[0] / 2
            button.rect.center = (
                start_x + (target_x - start_x) * eased,
                SCREEN_HEIGHT / 2
                + 30
                + (index - (option_count - 1) / 2)
                * (LEVEL_UP_BUTTON_SIZE[1] + LEVEL_UP_BUTTON_SPACING),
            )
            button.display(self.screen)
