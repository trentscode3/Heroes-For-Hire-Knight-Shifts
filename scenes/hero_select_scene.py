import pygame

from core.ui_font import ui_font
from core.units import meters_label

from core.audio_manager import audio
from core.display_manager import display
from core.game_state import GameState
from core.settings import (
    ARROW_SPEED,
    BUTTON_COLOR,
    BUTTON_FONT_SIZE,
    BUTTON_HOVER_COLOR,
    BUTTON_SIZE,
    BUTTON_SPACING,
    BUTTON_TEXT_COLOR,
    DEMO_BUILD,
    DEMO_PLAYABLE_HERO_IDS,
    HERO_SELECT_BUTTON_SHIFT,
    HERO_SELECT_CLOSE_DELAY,
    HERO_SELECT_DIM_ALPHA,
    HERO_SELECT_DIM_SCALE,
    HERO_SELECT_DRAWER_DURATION,
    HERO_SELECT_DRAWER_WIDTH,
    HERO_SELECT_HEADSHOT_SIZE,
    HERO_SELECT_HOVER_SCALE,
    MENU_BG_COLOR,
    MENU_TEXT_COLOR,
    NIMBUS_ATTACK_SPEED,
    NIMBUS_ATTACK_DAMAGE,
    NIMBUS_MAX_DAMAGE_MULTIPLIER,
    NIMBUS_MIN_DAMAGE_MULTIPLIER,
    NIMBUS_STRIKE_RADIUS,
    NIMBUS_MULTIPLIER_RING_RADIUS,
    PLAYER_ATTACK_DAMAGE,
    PLAYER_ATTACK_HALF_ANGLE,
    PLAYER_ATTACK_RADIUS,
    PLAYER_ATTACK_SPEED,
    PLAYER_CRIT_CHANCE,
    PLAYER_SPEED,
    SCENE_TITLE_FONT_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from sprites import HERO_CLASSES
from .button import Button
from .knowledge_scene import KnowledgeScene
from .scene import Scene


class HeroSelectScene(Scene):
    """Animated hero picker with a sliding character-information drawer."""

    music_track = "menu"

    def __init__(
        self,
        manager,
        screen: pygame.Surface,
        state: GameState,
        next_scene: str,
        debug_mode: bool = False,
    ) -> None:
        super().__init__(manager, screen)
        self.state = state
        self.next_scene = next_scene
        self.debug_mode = debug_mode
        self.title_font = ui_font(SCENE_TITLE_FONT_SIZE)
        self.button_font = ui_font(BUTTON_FONT_SIZE)
        self.name_font = ui_font(48)
        self.heading_font = ui_font(29)
        self.info_font = ui_font(23)
        self.mouse_pos = display.mouse_position()
        self.hovered_id: str | None = None
        self.displayed_hero_id: str | None = None
        self.drawer_progress = 0.0
        self.close_delay_remaining = 0.0
        self.headshots: dict[str, pygame.Surface | None] = {}

        hero_classes = tuple(
            hero_class
            for hero_class in HERO_CLASSES.values()
            if not DEMO_BUILD or hero_class.HERO_ID in DEMO_PLAYABLE_HERO_IDS
        )
        total_height = len(hero_classes) * BUTTON_SIZE[1] + (
            len(hero_classes) - 1
        ) * (BUTTON_SPACING + 28)
        first_y = (SCREEN_HEIGHT - total_height) / 2 + 55
        self.buttons: list[tuple[Button, type, pygame.Rect]] = []
        for index, hero_class in enumerate(hero_classes):
            base_rect = pygame.Rect(0, 0, *BUTTON_SIZE)
            base_rect.midtop = (
                SCREEN_WIDTH / 2,
                first_y + index * (BUTTON_SIZE[1] + BUTTON_SPACING + 28),
            )
            hero_id = hero_class.HERO_ID
            button = Button(
                base_rect.copy(),
                hero_class.HERO_NAME,
                self.button_font,
                lambda hero_id=hero_id: self.choose(hero_id),
            )
            self.buttons.append((button, hero_class, base_rect))
            self.headshots[hero_id] = self.load_headshot(hero_class)

    @staticmethod
    def smoothstep(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return value * value * (3 - 2 * value)

    @staticmethod
    def load_headshot(hero_class: type) -> pygame.Surface | None:
        try:
            sheet = pygame.image.load(
                hero_class.CHARACTER_PATH / "D_Idle.png"
            ).convert_alpha()
        except (FileNotFoundError, pygame.error):
            return None
        frame_width, frame_height = hero_class.ANIMATION_SOURCE_FRAME_SIZE
        frame = sheet.subsurface(
            pygame.Rect(0, 0, frame_width, frame_height)
        ).copy()
        bounds = frame.get_bounding_rect(min_alpha=1)
        if bounds.width <= 0 or bounds.height <= 0:
            return None
        bounds.inflate_ip(4, 4)
        bounds.clamp_ip(frame.get_rect())
        bounds.height = min(
            frame.get_height() - bounds.top,
            max(1, round(bounds.height * 0.65)),
        )
        portrait = frame.subsurface(bounds).copy()
        scale = min(
            HERO_SELECT_HEADSHOT_SIZE[0] / portrait.get_width(),
            HERO_SELECT_HEADSHOT_SIZE[1] / portrait.get_height(),
        )
        size = (
            max(1, round(portrait.get_width() * scale)),
            max(1, round(portrait.get_height() * scale)),
        )
        return pygame.transform.scale(portrait, size)

    def choose(self, hero_id: str) -> None:
        if not self.debug_mode and not self.state.hero_unlocked(hero_id):
            return
        if self.debug_mode:
            self.state.hero_id = hero_id
        else:
            self.state.start_new_run(hero_id)
        self.manager.change("hired" if self.next_scene == "day" else self.next_scene)

    def knowledge_button_rect(self) -> pygame.Rect | None:
        if self.displayed_hero_id is None:
            return None
        eased = self.smoothstep(self.drawer_progress)
        drawer_left = round(SCREEN_WIDTH - HERO_SELECT_DRAWER_WIDTH * eased)
        return pygame.Rect(
            drawer_left + 36,
            SCREEN_HEIGHT - 138,
            HERO_SELECT_DRAWER_WIDTH - 72,
            42,
        )

    def apply_button_rect(self) -> pygame.Rect | None:
        knowledge = self.knowledge_button_rect()
        if knowledge is None:
            return None
        return knowledge.move(0, 54)

    def drawer_rect(self) -> pygame.Rect | None:
        if self.displayed_hero_id is None or self.drawer_progress <= 0:
            return None
        eased = self.smoothstep(self.drawer_progress)
        left = round(SCREEN_WIDTH - HERO_SELECT_DRAWER_WIDTH * eased)
        return pygame.Rect(left, 0, SCREEN_WIDTH - left, SCREEN_HEIGHT)

    def close_knowledge(self) -> None:
        self.set_subscene(None)

    def open_knowledge(self) -> None:
        if self.displayed_hero_id is None:
            return
        self.set_subscene(
            KnowledgeScene(
                self.manager,
                self.screen,
                self.state,
                self.close_knowledge,
                access_mode="character_select",
                hero_id=self.displayed_hero_id,
            )
        )

    def hero_locked(self, hero_id: str) -> bool:
        return not self.debug_mode and not self.state.hero_unlocked(hero_id)

    def find_hovered_hero(self, position: tuple[int, int]) -> str | None:
        for button, hero_class, _ in self.buttons:
            if button.rect.collidepoint(position):
                return hero_class.HERO_ID
        return None

    def update_button_layout(self) -> None:
        eased = self.smoothstep(self.drawer_progress)
        active_id = self.hovered_id or self.displayed_hero_id
        for button, hero_class, base_rect in self.buttons:
            if active_id == hero_class.HERO_ID:
                scale = 1 + (HERO_SELECT_HOVER_SCALE - 1) * eased
            elif active_id is not None:
                scale = 1 + (HERO_SELECT_DIM_SCALE - 1) * eased
            else:
                scale = 1.0
            button.rect.size = (
                round(base_rect.width * scale),
                round(base_rect.height * scale),
            )
            button.rect.center = (
                round(base_rect.centerx - HERO_SELECT_BUTTON_SHIFT * eased),
                base_rect.centery,
            )

    def on_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.manager.change("main_menu")
            return
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.mouse_pos = event.pos
            knowledge_rect = self.knowledge_button_rect()
            if knowledge_rect is not None and knowledge_rect.collidepoint(event.pos):
                audio.play_sound("menu_click")
                self.open_knowledge()
                return
            apply_rect = self.apply_button_rect()
            if apply_rect is not None and apply_rect.collidepoint(event.pos):
                audio.play_sound("menu_click")
                if self.displayed_hero_id is not None:
                    self.choose(self.displayed_hero_id)
                return

    def on_update(self, dt: float) -> None:
        self.hovered_id = self.find_hovered_hero(self.mouse_pos)
        if self.hovered_id is not None:
            self.displayed_hero_id = self.hovered_id
            self.close_delay_remaining = HERO_SELECT_CLOSE_DELAY
        drawer = self.drawer_rect()
        pointer_in_drawer = drawer is not None and drawer.collidepoint(self.mouse_pos)
        if pointer_in_drawer:
            self.close_delay_remaining = HERO_SELECT_CLOSE_DELAY
        elif self.hovered_id is None:
            self.close_delay_remaining = max(0.0, self.close_delay_remaining - dt)
        keep_open = (
            self.hovered_id is not None
            or pointer_in_drawer
            or self.close_delay_remaining > 0
        )
        target = 1.0 if keep_open else 0.0
        step = dt / HERO_SELECT_DRAWER_DURATION
        if self.drawer_progress < target:
            self.drawer_progress = min(target, self.drawer_progress + step)
        else:
            self.drawer_progress = max(target, self.drawer_progress - step)
        if self.drawer_progress <= 0:
            self.displayed_hero_id = None
        self.update_button_layout()

    def draw_button(self, button: Button, hero_id: str) -> None:
        eased = self.smoothstep(self.drawer_progress)
        active_id = self.hovered_id or self.displayed_hero_id
        if active_id == hero_id:
            color = BUTTON_HOVER_COLOR
        elif active_id is not None:
            dim = 1 - (1 - HERO_SELECT_DIM_ALPHA) * eased
            color = tuple(round(channel * dim) for channel in BUTTON_COLOR)
        else:
            color = BUTTON_COLOR
        pygame.draw.rect(self.screen, color, button.rect, border_radius=8)
        if self.hero_locked(hero_id):
            shade = pygame.Surface(button.rect.size, pygame.SRCALPHA)
            shade.fill((0, 0, 0, 145))
            self.screen.blit(shade, button.rect)
        if self.state.hero_id == hero_id:
            pygame.draw.rect(
                self.screen,
                (255, 220, 80),
                button.rect,
                width=3,
                border_radius=8,
            )
        text_color = (
            tuple(round(channel * dim) for channel in BUTTON_TEXT_COLOR)
            if active_id is not None and active_id != hero_id
            else BUTTON_TEXT_COLOR
        )
        label = self.button_font.render(button.text, True, text_color)
        max_width = button.rect.width - 16
        if label.get_width() > max_width:
            label = pygame.transform.smoothscale(
                label,
                (
                    max_width,
                    max(1, round(label.get_height() * max_width / label.get_width())),
                ),
            )
        self.screen.blit(label, label.get_rect(center=button.rect.center))

    def wrap_text(self, text: str, width: int) -> list[str]:
        words = text.split()
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and self.info_font.size(candidate)[0] > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines

    @staticmethod
    def hero_stats(hero_id: str) -> tuple[str, ...]:
        base_damage = (
            NIMBUS_ATTACK_DAMAGE if hero_id == "nimbus" else PLAYER_ATTACK_DAMAGE
        )
        common = (
            f"Base damage: {base_damage:g}",
            f"Move speed: {meters_label(PLAYER_SPEED, 'm/s')}",
            (
                "Critical chance: 25%-100% by range"
                if hero_id == "robin_hood"
                else f"Critical chance: {PLAYER_CRIT_CHANCE:.0%}"
            ),
        )
        if hero_id == "warrior":
            specific = (
                f"Attack cooldown: {PLAYER_ATTACK_SPEED:g}s",
                f"Attack radius: {meters_label(PLAYER_ATTACK_RADIUS)}",
                "Sword swing area: "
                f"{round(PLAYER_ATTACK_HALF_ANGLE * 2 * 180 / 3.14159265)} degrees",
            )
        elif hero_id == "robin_hood":
            specific = (
                f"Attack cooldown: {PLAYER_ATTACK_SPEED:g}s",
                f"Arrow speed: {meters_label(ARROW_SPEED, 'm/s')}",
                "Range: Screen edge",
            )
        else:
            specific = (
                f"Attack cooldown: {NIMBUS_ATTACK_SPEED:g}s",
                f"Strike radius: {meters_label(NIMBUS_STRIKE_RADIUS)}",
                f"Maximum zone: {meters_label(NIMBUS_MULTIPLIER_RING_RADIUS)}",
                "Damage scaling: "
                f"x{NIMBUS_MIN_DAMAGE_MULTIPLIER:g}-"
                f"x{NIMBUS_MAX_DAMAGE_MULTIPLIER:g}",
            )
        return common + specific

    def draw_drawer(self) -> None:
        if self.displayed_hero_id is None:
            return
        eased = self.smoothstep(self.drawer_progress)
        drawer_left = round(SCREEN_WIDTH - HERO_SELECT_DRAWER_WIDTH * eased)
        drawer = pygame.Rect(
            drawer_left,
            0,
            HERO_SELECT_DRAWER_WIDTH,
            SCREEN_HEIGHT,
        )
        pygame.draw.rect(self.screen, (31, 35, 44), drawer)
        pygame.draw.line(
            self.screen,
            (130, 145, 170),
            (drawer.left, 0),
            (drawer.left, SCREEN_HEIGHT),
            3,
        )
        tab = pygame.Rect(drawer.left - 22, 92, 22, 120)
        pygame.draw.rect(self.screen, (65, 72, 88), tab, border_radius=5)

        hero_class = HERO_CLASSES[self.displayed_hero_id]
        content_left = drawer.left + 36
        headshot_rect = pygame.Rect(0, 0, *HERO_SELECT_HEADSHOT_SIZE)
        headshot_rect.midtop = (drawer.centerx, 42)
        pygame.draw.rect(self.screen, (18, 20, 26), headshot_rect, border_radius=12)
        headshot = self.headshots[self.displayed_hero_id]
        if headshot is not None:
            if self.hero_locked(self.displayed_hero_id):
                silhouette = headshot.copy()
                silhouette.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MIN)
                self.screen.blit(
                    silhouette,
                    silhouette.get_rect(center=headshot_rect.center),
                )
                question_font = ui_font(112)
                question = question_font.render("?", True, (240, 240, 240))
                self.screen.blit(question, question.get_rect(center=headshot_rect.center))
            else:
                self.screen.blit(headshot, headshot.get_rect(center=headshot_rect.center))

        name = self.name_font.render(hero_class.HERO_NAME, True, MENU_TEXT_COLOR)
        self.screen.blit(name, name.get_rect(midtop=(drawer.centerx, 248)))
        locked = self.hero_locked(self.displayed_hero_id)
        style_text = "LOCKED" if locked else hero_class.ATTACK_STYLE
        style = self.heading_font.render(style_text, True, (150, 185, 235))
        self.screen.blit(style, style.get_rect(midtop=(drawer.centerx, 294)))

        y = 336
        if locked:
            for line in self.wrap_text(
                self.state.quest_text(self.displayed_hero_id),
                drawer.width - 72,
            ):
                quest = self.info_font.render(line, True, (245, 215, 110))
                self.screen.blit(quest, (content_left, y))
                y += 25
        else:
            for line in self.wrap_text(
                hero_class.HERO_DESCRIPTION,
                drawer.width - 72,
            ):
                text = self.info_font.render(line, True, MENU_TEXT_COLOR)
                self.screen.blit(text, (content_left, y))
                y += 23
            y += 10
            heading = self.heading_font.render(
                "BASE STATS",
                True,
                (235, 210, 120),
            )
            self.screen.blit(heading, (content_left, y))
            y += 31
            for stat in self.hero_stats(self.displayed_hero_id):
                text = self.info_font.render(stat, True, MENU_TEXT_COLOR)
                self.screen.blit(text, (content_left, y))
                y += 23
        knowledge_rect = self.knowledge_button_rect()
        if knowledge_rect is not None:
            pygame.draw.rect(self.screen, (50, 82, 135), knowledge_rect, border_radius=7)
            pygame.draw.rect(
                self.screen,
                (135, 170, 225),
                knowledge_rect,
                width=2,
                border_radius=7,
            )
            knowledge_label = self.info_font.render(
                "View Knowledge Tree",
                True,
                MENU_TEXT_COLOR,
            )
            self.screen.blit(
                knowledge_label,
                knowledge_label.get_rect(center=knowledge_rect.center),
            )
        apply_rect = self.apply_button_rect()
        if apply_rect is not None:
            apply_color = (55, 155, 82) if not locked else (70, 70, 74)
            apply_border = (135, 235, 150) if not locked else (115, 115, 120)
            pygame.draw.rect(self.screen, apply_color, apply_rect, border_radius=7)
            pygame.draw.rect(
                self.screen,
                apply_border,
                apply_rect,
                width=2,
                border_radius=7,
            )
            apply_label = self.heading_font.render(
                "Apply" if not locked else "Position Locked",
                True,
                MENU_TEXT_COLOR,
            )
            self.screen.blit(
                apply_label,
                apply_label.get_rect(center=apply_rect.center),
            )

    def draw(self) -> None:
        self.screen.fill(MENU_BG_COLOR)
        title = self.title_font.render("SUBMIT APPLICATION", True, MENU_TEXT_COLOR)
        eased = self.smoothstep(self.drawer_progress)
        title_x = SCREEN_WIDTH / 2 + (
            (SCREEN_WIDTH - HERO_SELECT_DRAWER_WIDTH) / 2 - SCREEN_WIDTH / 2
        ) * eased
        self.screen.blit(title, title.get_rect(center=(title_x, 90)))
        for button, hero_class, _ in self.buttons:
            self.draw_button(button, hero_class.HERO_ID)
        self.draw_drawer()
