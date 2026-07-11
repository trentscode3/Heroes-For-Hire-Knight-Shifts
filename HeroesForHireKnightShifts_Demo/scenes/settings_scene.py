from collections.abc import Callable

import pygame

from core.ui_font import ui_font

from core.audio_manager import audio
from core.display_manager import display
from core.save_manager import save_manager
from core.user_preferences import preferences
from core.settings import (
    BUTTON_FONT_SIZE,
    BUTTON_SIZE,
    DISPLAY_MODES,
    DISPLAY_RESOLUTIONS,
    MENU_BG_COLOR,
    MENU_TEXT_COLOR,
    SCENE_TITLE_FONT_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from .button import Button
from .scene import Scene


class VolumeSlider:
    def __init__(
        self,
        label: str,
        center: tuple[int, int],
        value: float,
        on_change: Callable[[float], None],
    ) -> None:
        self.label = label
        self.track = pygame.Rect(0, 0, 460, 8)
        self.track.center = center
        self.value = value
        self.on_change = on_change
        self.dragging = False
        self.font = ui_font(30)

    def set_from_x(self, x: int) -> None:
        self.value = max(0.0, min(1.0, (x - self.track.left) / self.track.width))
        self.on_change(self.value)

    def handle_event(self, event: pygame.event.Event) -> None:
        hit_area = self.track.inflate(28, 34)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if hit_area.collidepoint(event.pos):
                audio.play_sound("menu_click")
                self.dragging = True
                self.set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

    def draw(self, surface: pygame.Surface) -> None:
        label = self.font.render(self.label, True, MENU_TEXT_COLOR)
        percent = self.font.render(f"{round(self.value * 100)}%", True, MENU_TEXT_COLOR)
        surface.blit(label, (self.track.left, self.track.top - 42))
        surface.blit(percent, percent.get_rect(right=self.track.right, top=self.track.top - 42))
        pygame.draw.rect(surface, (28, 28, 32), self.track, border_radius=4)
        filled = self.track.copy()
        filled.width = round(self.track.width * self.value)
        pygame.draw.rect(surface, (90, 155, 225), filled, border_radius=4)
        knob_x = round(self.track.left + self.track.width * self.value)
        pygame.draw.circle(surface, (235, 240, 250), (knob_x, self.track.centery), 12)
        pygame.draw.circle(surface, (55, 65, 80), (knob_x, self.track.centery), 12, 2)


class SettingsScene(Scene):
    music_track = "menu"

    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        back_action: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(manager, screen)
        self.back_action = back_action or (
            lambda: self.manager.change("main_menu")
        )
        self.active_tab = "general"
        self.pending_resolution = display.resolution
        self.pending_display_mode = display.mode
        self.graphics_status = ""
        self.title_font = ui_font(SCENE_TITLE_FONT_SIZE)
        self.body_font = ui_font(32)
        button_font = ui_font(BUTTON_FONT_SIZE)

        general_rect = pygame.Rect(0, 0, 180, 50)
        general_rect.center = (SCREEN_WIDTH / 2 - 195, 170)
        graphics_rect = general_rect.copy()
        graphics_rect.centerx = SCREEN_WIDTH / 2
        audio_rect = general_rect.copy()
        audio_rect.centerx = SCREEN_WIDTH / 2 + 195
        self.tab_buttons = (
            Button(general_rect, "General", button_font, lambda: self.set_tab("general")),
            Button(
                graphics_rect,
                "Graphics",
                button_font,
                lambda: self.set_tab("graphics"),
            ),
            Button(audio_rect, "Audio", button_font, lambda: self.set_tab("audio")),
        )

        auto_equip_rect = pygame.Rect(0, 0, 360, 64)
        auto_equip_rect.center = (SCREEN_WIDTH // 2, 300)
        self.auto_equip_button = Button(
            auto_equip_rect,
            "",
            button_font,
            self.toggle_auto_equip,
        )

        previous_resolution = pygame.Rect(0, 0, 64, 52)
        previous_resolution.center = (390, 315)
        next_resolution = previous_resolution.copy()
        next_resolution.centerx = 890
        previous_mode = previous_resolution.copy()
        previous_mode.centery = 430
        next_mode = next_resolution.copy()
        next_mode.centery = 430
        apply_rect = pygame.Rect(0, 0, *BUTTON_SIZE)
        apply_rect.center = (SCREEN_WIDTH / 2, 555)
        self.graphics_buttons = (
            Button(previous_resolution, "<", button_font, lambda: self.cycle_resolution(-1)),
            Button(next_resolution, ">", button_font, lambda: self.cycle_resolution(1)),
            Button(previous_mode, "<", button_font, lambda: self.cycle_display_mode(-1)),
            Button(next_mode, ">", button_font, lambda: self.cycle_display_mode(1)),
            Button(apply_rect, "Apply", button_font, self.apply_graphics),
        )

        self.sliders = (
            VolumeSlider(
                "Master Volume",
                (SCREEN_WIDTH // 2, 310),
                audio.master_volume,
                audio.set_master_volume,
            ),
            VolumeSlider(
                "Music Volume",
                (SCREEN_WIDTH // 2, 420),
                audio.music_volume,
                audio.set_music_volume,
            ),
            VolumeSlider(
                "Sound FX Volume",
                (SCREEN_WIDTH // 2, 530),
                audio.sound_volume,
                audio.set_sound_volume,
            ),
        )
        self.general_sliders = (
            VolumeSlider(
                "Screen Shake",
                (SCREEN_WIDTH // 2, 500),
                preferences.screen_shake_strength,
                self.set_screen_shake_strength,
            ),
        )

        back_rect = pygame.Rect(0, 0, *BUTTON_SIZE)
        back_rect.center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT - 90)
        self.back_button = Button(back_rect, "Back", button_font, self.back_action)

    def set_tab(self, tab: str) -> None:
        self.active_tab = tab

    def toggle_auto_equip(self) -> None:
        preferences.auto_equip_enabled = not preferences.auto_equip_enabled
        save_manager.save_preferences()

    @staticmethod
    def set_screen_shake_strength(value: float) -> None:
        preferences.screen_shake_strength = max(0.0, min(1.0, value))

    def cycle_resolution(self, direction: int) -> None:
        index = DISPLAY_RESOLUTIONS.index(self.pending_resolution)
        self.pending_resolution = DISPLAY_RESOLUTIONS[
            (index + direction) % len(DISPLAY_RESOLUTIONS)
        ]
        self.graphics_status = ""

    def cycle_display_mode(self, direction: int) -> None:
        index = DISPLAY_MODES.index(self.pending_display_mode)
        self.pending_display_mode = DISPLAY_MODES[
            (index + direction) % len(DISPLAY_MODES)
        ]
        self.graphics_status = ""

    def apply_graphics(self) -> None:
        requested_mode = self.pending_display_mode
        display.apply(self.pending_resolution, requested_mode)
        self.pending_display_mode = display.mode
        if display.mode == "Borderless":
            width, height = display.physical_size
            self.graphics_status = f"Applied borderless desktop: {width} x {height}"
        elif display.mode != requested_mode:
            self.graphics_status = "Display mode unsupported; using Windowed"
        else:
            self.graphics_status = "Graphics settings applied"
        save_manager.save_preferences()

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back_action()
            return
        for button in self.tab_buttons:
            button.handle_event(event)
        if self.active_tab == "audio":
            for slider in self.sliders:
                slider.handle_event(event)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                save_manager.save_preferences()
        elif self.active_tab == "graphics":
            for button in self.graphics_buttons:
                button.handle_event(event)
        elif self.active_tab == "general":
            self.auto_equip_button.handle_event(event)
            for slider in self.general_sliders:
                slider.handle_event(event)
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                save_manager.save_preferences()
        self.back_button.handle_event(event)

    def draw(self) -> None:
        self.screen.fill(MENU_BG_COLOR)
        title = self.title_font.render("WORKPLACE SETTINGS", True, MENU_TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH / 2, 80)))

        for button in self.tab_buttons:
            button.display(self.screen)
            if button.text.lower() == self.active_tab:
                pygame.draw.rect(
                    self.screen,
                    (90, 155, 225),
                    button.rect,
                    width=3,
                    border_radius=8,
                )

        if self.active_tab == "audio":
            for slider in self.sliders:
                slider.draw(self.screen)
        elif self.active_tab == "graphics":
            resolution_label = self.body_font.render(
                "Resolution", True, MENU_TEXT_COLOR
            )
            resolution = self.body_font.render(
                f"{self.pending_resolution[0]} x {self.pending_resolution[1]}",
                True,
                MENU_TEXT_COLOR,
            )
            mode_label = self.body_font.render(
                "Display Mode", True, MENU_TEXT_COLOR
            )
            mode = self.body_font.render(
                self.pending_display_mode, True, MENU_TEXT_COLOR
            )
            self.screen.blit(
                resolution_label,
                resolution_label.get_rect(center=(SCREEN_WIDTH / 2, 260)),
            )
            self.screen.blit(
                resolution,
                resolution.get_rect(center=(SCREEN_WIDTH / 2, 315)),
            )
            self.screen.blit(
                mode_label,
                mode_label.get_rect(center=(SCREEN_WIDTH / 2, 375)),
            )
            self.screen.blit(mode, mode.get_rect(center=(SCREEN_WIDTH / 2, 430)))
            for button in self.graphics_buttons:
                button.display(self.screen)
            if self.pending_display_mode == "Borderless":
                note = self.body_font.render(
                    "Borderless uses the monitor's desktop resolution.",
                    True,
                    (185, 190, 200),
                )
                self.screen.blit(note, note.get_rect(center=(SCREEN_WIDTH / 2, 495)))
            if self.graphics_status:
                status = self.body_font.render(
                    self.graphics_status, True, (125, 205, 140)
                )
                self.screen.blit(status, status.get_rect(center=(SCREEN_WIDTH / 2, 610)))
        else:
            self.auto_equip_button.text = (
                "Auto Equip: ON"
                if preferences.auto_equip_enabled
                else "Auto Equip: OFF"
            )
            self.auto_equip_button.color = (
                (55, 115, 70)
                if preferences.auto_equip_enabled
                else (75, 75, 82)
            )
            self.auto_equip_button.display(self.screen)
            explanation = self.body_font.render(
                "Automatically equip newly received items when possible.",
                True,
                (195, 200, 210),
            )
            self.screen.blit(
                explanation,
                explanation.get_rect(center=(SCREEN_WIDTH // 2, 370)),
            )
            for slider in self.general_sliders:
                slider.draw(self.screen)

        self.back_button.display(self.screen)
