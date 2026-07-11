from functools import lru_cache

import pygame

from core.settings import (
    ARCHER_ANIMATION_SOURCE_FRAME_SIZE,
    CLASSIC_ARCHER_PALETTE,
    CLASSIC_KNIGHT_PALETTE,
    GOBLIN_CHARACTER_PATH,
    KNIGHT_ANIMATION_SOURCE_FRAME_SIZE,
    KNIGHT_CHARACTER_PATH,
    NIMBUS_CHARACTER_PATH,
    PLAYER_ANIMATION_SOURCE_FRAME_SIZE,
    PLAYER_CHARACTER_PATH,
    ROBIN_HOOD_CHARACTER_PATH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SHAMAN_CHARACTER_PATH,
)
from sprites.animation import load_directional_animations


@lru_cache(maxsize=None)
def character_frame(
    character_path: str,
    source_size: tuple[int, int],
    display_size: tuple[int, int],
    direction: str = "down",
    state: str = "idle",
    palette_items: tuple = (),
) -> pygame.Surface:
    animations = load_directional_animations(
        character_path,
        source_size,
        display_size,
        palette_items,
    )
    return animations[(direction, state)][0]


def vertical_gradient(
    surface: pygame.Surface,
    top_color: tuple[int, int, int],
    bottom_color: tuple[int, int, int],
) -> None:
    height = max(1, surface.get_height() - 1)
    for y in range(surface.get_height()):
        amount = y / height
        color = tuple(
            round(top_color[channel] * (1 - amount) + bottom_color[channel] * amount)
            for channel in range(3)
        )
        pygame.draw.line(surface, color, (0, y), (surface.get_width(), y))


def draw_soft_ellipse(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    alpha: int,
) -> None:
    ellipse = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.ellipse(ellipse, (*color, alpha), ellipse.get_rect())
    surface.blit(ellipse, rect)


def draw_shadow(
    surface: pygame.Surface,
    center: tuple[float, float],
    size: tuple[int, int],
    alpha: int = 95,
) -> None:
    rect = pygame.Rect(0, 0, *size)
    rect.center = center
    draw_soft_ellipse(surface, rect, (0, 0, 0), alpha)


def blit_center(
    surface: pygame.Surface,
    image: pygame.Surface,
    center: tuple[float, float],
    flip_x: bool = False,
    size: tuple[int, int] | None = None,
) -> None:
    if flip_x:
        image = pygame.transform.flip(image, True, False)
    if size is not None:
        visible_bounds = image.get_bounding_rect(1)
        if visible_bounds.width > 0 and visible_bounds.height > 0:
            image = image.subsurface(visible_bounds).copy()
        image = pygame.transform.smoothscale(image, size)
    surface.blit(image, image.get_rect(center=center))


def parallax(
    mouse_position: tuple[int, int] | None,
    strength: float,
) -> pygame.Vector2:
    if mouse_position is None:
        return pygame.Vector2()
    mouse = pygame.Vector2(mouse_position)
    normalized = pygame.Vector2(
        (mouse.x - SCREEN_WIDTH / 2) / (SCREEN_WIDTH / 2),
        (mouse.y - SCREEN_HEIGHT / 2) / (SCREEN_HEIGHT / 2),
    )
    return normalized * strength


def draw_clouds(surface: pygame.Surface) -> None:
    clouds = (
        (110, 82, 255, 52),
        (570, 66, 342, 58),
        (790, 154, 250, 42),
        (1010, 214, 220, 36),
    )
    for x, y, width, height in clouds:
        draw_soft_ellipse(
            surface,
            pygame.Rect(x, y, width, height),
            (226, 234, 240),
            156,
        )


def draw_title_landscape(surface: pygame.Surface) -> None:
    vertical_gradient(surface, (92, 139, 184), (30, 73, 83))
    sun = pygame.Surface((270, 270), pygame.SRCALPHA)
    for radius, alpha in ((132, 28), (92, 44), (58, 225)):
        pygame.draw.circle(sun, (246, 211, 120, alpha), (135, 135), radius)
    surface.blit(sun, (900, -22))
    draw_clouds(surface)

    mountains = (
        ((0, 466), (178, 275), (372, 466), (29, 60, 78)),
        ((835, 464), (1090, 246), (1280, 464), (31, 68, 78)),
        ((0, 500), (355, 326), (680, 500), (44, 86, 78)),
        ((635, 500), (965, 330), (1280, 500), (40, 83, 71)),
    )
    for left, peak, right, color in mountains:
        pygame.draw.polygon(surface, color, (left, peak, right))

    ground = pygame.Rect(0, round(SCREEN_HEIGHT * 0.56), SCREEN_WIDTH, 360)
    ground_fill = pygame.Surface(ground.size)
    vertical_gradient(ground_fill, (47, 110, 53), (24, 66, 34))
    surface.blit(ground_fill, ground)

    for x in range(-18, SCREEN_WIDTH + 60, 76):
        trunk = pygame.Rect(x + 22, ground.top - 18, 14, 72)
        pygame.draw.rect(surface, (58, 41, 28), trunk)
        pygame.draw.polygon(
            surface,
            (28, 78, 42),
            ((x, ground.top + 5), (x + 30, ground.top - 86), (x + 62, ground.top + 5)),
        )
        pygame.draw.polygon(
            surface,
            (36, 94, 48),
            (
                (x + 8, ground.top - 24),
                (x + 31, ground.top - 118),
                (x + 55, ground.top - 24),
            ),
        )

    pygame.draw.line(surface, (30, 68, 38), (110, 645), (310, 606), 5)
    pygame.draw.line(surface, (30, 68, 38), (990, 638), (760, 595), 5)


def draw_title_battle_background(surface: pygame.Surface) -> None:
    draw_title_landscape(surface)

    hero_size = (128, 128)
    nimbus_size = (128, 128)
    enemy_size = (112, 112)
    warrior = character_frame(
        str(PLAYER_CHARACTER_PATH),
        PLAYER_ANIMATION_SOURCE_FRAME_SIZE,
        hero_size,
        "side",
        "attack",
    )
    robin = character_frame(
        str(ROBIN_HOOD_CHARACTER_PATH),
        ARCHER_ANIMATION_SOURCE_FRAME_SIZE,
        hero_size,
        "side",
        "attack",
    )
    nimbus = character_frame(
        str(NIMBUS_CHARACTER_PATH),
        PLAYER_ANIMATION_SOURCE_FRAME_SIZE,
        nimbus_size,
        "down",
        "attack",
    )
    knight = character_frame(
        str(KNIGHT_CHARACTER_PATH),
        KNIGHT_ANIMATION_SOURCE_FRAME_SIZE,
        enemy_size,
        "side",
        "attack",
        tuple(sorted(CLASSIC_KNIGHT_PALETTE.items())),
    )
    goblin = character_frame(
        str(GOBLIN_CHARACTER_PATH),
        KNIGHT_ANIMATION_SOURCE_FRAME_SIZE,
        enemy_size,
        "side",
        "walk",
    )
    shaman = character_frame(
        str(SHAMAN_CHARACTER_PATH),
        KNIGHT_ANIMATION_SOURCE_FRAME_SIZE,
        enemy_size,
        "down",
        "attack",
    )

    draw_soft_ellipse(surface, pygame.Rect(178, 475, 260, 100), (212, 190, 116), 42)
    draw_soft_ellipse(surface, pygame.Rect(800, 495, 270, 98), (212, 190, 116), 34)
    draw_soft_ellipse(surface, pygame.Rect(510, 470, 280, 150), (120, 180, 232), 36)

    draw_shadow(surface, (305, 590), (58, 16))
    draw_shadow(surface, (482, 590), (50, 14))
    blit_center(surface, warrior, (305, 548), size=(59, 59))
    blit_center(surface, knight, (482, 552), True, size=(52, 52))
    pygame.draw.arc(surface, (245, 247, 250), (300, 438, 214, 152), -0.55, 0.75, 8)
    pygame.draw.arc(surface, (126, 168, 225), (294, 432, 226, 164), -0.55, 0.75, 3)

    draw_shadow(surface, (820, 608), (58, 16))
    draw_shadow(surface, (1018, 602), (50, 14))
    blit_center(surface, robin, (820, 568), True, size=(58, 58))
    blit_center(surface, goblin, (1018, 570), size=(50, 50))
    pygame.draw.line(surface, (236, 220, 150), (820, 512), (975, 520), 5)
    pygame.draw.polygon(surface, (236, 220, 150), ((978, 520), (958, 508), (958, 532)))

    draw_shadow(surface, (640, 502), (60, 16), 70)
    draw_shadow(surface, (690, 646), (50, 14))
    blit_center(surface, nimbus, (640, 458), size=(60, 60))
    blit_center(surface, shaman, (690, 612), size=(52, 52))
    for radius, alpha in ((46, 80), (72, 50), (102, 28)):
        aura = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(aura, (125, 185, 255, alpha), (radius, radius), radius, 4)
        surface.blit(aura, aura.get_rect(center=(655, 565)))
    pygame.draw.line(surface, (225, 240, 255), (665, 350), (640, 505), 6)
    pygame.draw.line(surface, (160, 205, 255), (640, 505), (690, 565), 5)

    vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for inset, alpha in ((0, 92), (35, 62), (80, 28)):
        rect = pygame.Rect(inset, inset, SCREEN_WIDTH - inset * 2, SCREEN_HEIGHT - inset * 2)
        pygame.draw.rect(vignette, (5, 10, 18, alpha), rect, width=34)
    surface.blit(vignette, (0, 0))


def draw_wall_panels(surface: pygame.Surface) -> None:
    pygame.draw.rect(surface, (100, 92, 78), (0, 0, SCREEN_WIDTH, 386))
    for x in range(0, SCREEN_WIDTH, 96):
        panel = pygame.Rect(x, 0, 92, 386)
        pygame.draw.rect(surface, (93, 85, 73), panel)
        pygame.draw.rect(surface, (68, 62, 54), panel, width=2)


def draw_office_window(surface: pygame.Surface) -> None:
    window = pygame.Rect(426, 84, 428, 188)
    pygame.draw.rect(surface, (42, 62, 82), window, border_radius=8)
    pygame.draw.rect(surface, (180, 145, 82), window, width=5, border_radius=8)
    pygame.draw.line(surface, (180, 145, 82), window.midtop, window.midbottom, 4)
    pygame.draw.line(
        surface,
        (180, 145, 82),
        window.midleft,
        window.midright,
        4,
    )
    pygame.draw.circle(surface, (234, 198, 103), (window.right - 72, window.top + 46), 27)
    pygame.draw.polygon(
        surface,
        (24, 55, 67),
        (
            (window.left + 15, window.bottom - 5),
            (window.left + 105, window.top + 62),
            (window.left + 205, window.bottom - 5),
        ),
    )
    pygame.draw.polygon(
        surface,
        (27, 65, 62),
        (
            (window.left + 170, window.bottom - 5),
            (window.left + 290, window.top + 50),
            (window.right - 15, window.bottom - 5),
        ),
    )


def draw_office_floor(surface: pygame.Surface) -> None:
    pygame.draw.rect(surface, (57, 45, 37), (0, 386, SCREEN_WIDTH, SCREEN_HEIGHT - 386))
    for x in range(-80, SCREEN_WIDTH, 120):
        pygame.draw.line(surface, (83, 65, 51), (x, 386), (x + 230, SCREEN_HEIGHT), 3)
    for y in range(424, SCREEN_HEIGHT, 66):
        pygame.draw.line(surface, (75, 58, 47), (0, y), (SCREEN_WIDTH, y), 2)


def draw_office_sign(surface: pygame.Surface) -> None:
    sign = pygame.Rect(330, 24, 620, 82)
    for x in (sign.left + 86, sign.right - 86):
        pygame.draw.line(surface, (60, 49, 38), (x, 0), (x, sign.top + 6), 5)
    pygame.draw.rect(surface, (92, 58, 31), sign, border_radius=8)
    pygame.draw.rect(surface, (218, 168, 82), sign, 5, border_radius=8)
    pygame.draw.rect(surface, (120, 76, 39), sign.inflate(-18, -18), width=2)
    font = pygame.font.Font(None, 50)
    text = font.render("HERO EMPLOYMENT CENTER", True, (255, 236, 178))
    surface.blit(text, text.get_rect(center=sign.center))


def draw_office_props(surface: pygame.Surface) -> None:
    board = pygame.Rect(54, 150, 270, 242)
    pygame.draw.rect(surface, (58, 38, 24), board.move(0, 8), border_radius=8)
    pygame.draw.rect(surface, (100, 64, 35), board, border_radius=8)
    pygame.draw.rect(surface, (200, 151, 78), board, 4, border_radius=8)
    for index, label in enumerate(("WANTED", "NIGHT SHIFT", "BOSS HAZARD")):
        paper = pygame.Rect(board.left + 28, board.top + 28 + index * 64, 214, 46)
        pygame.draw.rect(surface, (238, 223, 178), paper)
        pygame.draw.rect(surface, (116, 82, 48), paper, width=2)
        line = pygame.font.Font(None, 28).render(label, True, (62, 43, 30))
        surface.blit(line, line.get_rect(center=paper.center))

    desk = pygame.Rect(964, 174, 232, 178)
    pygame.draw.rect(surface, (49, 32, 22), desk.move(0, 8), border_radius=8)
    pygame.draw.rect(surface, (82, 51, 30), desk, border_radius=8)
    pygame.draw.rect(surface, (150, 96, 47), desk, 4, border_radius=8)
    pygame.draw.rect(surface, (238, 228, 190), (1004, 206, 96, 42))
    pygame.draw.rect(surface, (238, 228, 190), (1082, 266, 82, 38))
    pygame.draw.rect(surface, (40, 42, 45), (1012, 318, 140, 14), border_radius=4)


def draw_rooftop(surface: pygame.Surface, rect: pygame.Rect) -> None:
    pygame.draw.polygon(
        surface,
        (72, 36, 28),
        (
            (rect.left - 55, rect.top + 72),
            (rect.centerx, rect.top - 42),
            (rect.right + 55, rect.top + 72),
        ),
    )
    pygame.draw.polygon(
        surface,
        (120, 60, 42),
        (
            (rect.left - 26, rect.top + 70),
            (rect.centerx, rect.top - 24),
            (rect.right + 26, rect.top + 70),
        ),
    )
    pygame.draw.line(
        surface,
        (224, 172, 84),
        (rect.left - 36, rect.top + 72),
        (rect.right + 36, rect.top + 72),
        6,
    )


def draw_storefront_windows(surface: pygame.Surface, building: pygame.Rect) -> None:
    for x in (building.left + 62, building.right - 220):
        window = pygame.Rect(x, building.top + 130, 158, 128)
        pygame.draw.rect(surface, (42, 64, 83), window, border_radius=8)
        pygame.draw.rect(surface, (220, 174, 88), window, width=4, border_radius=8)
        pygame.draw.line(surface, (220, 174, 88), window.midtop, window.midbottom, 3)
        pygame.draw.line(surface, (220, 174, 88), window.midleft, window.midright, 3)
        shine = pygame.Surface(window.size, pygame.SRCALPHA)
        pygame.draw.polygon(
            shine,
            (255, 255, 255, 38),
            ((20, 0), (65, 0), (18, window.height), (0, window.height)),
        )
        surface.blit(shine, window)


def draw_exterior_sign(surface: pygame.Surface, building: pygame.Rect) -> None:
    sign = pygame.Rect(0, 0, 560, 82)
    sign.center = (building.centerx, building.top + 76)
    for x in (sign.left + 72, sign.right - 72):
        pygame.draw.line(surface, (50, 38, 30), (x, sign.top - 28), (x, sign.top), 5)
    pygame.draw.rect(surface, (76, 48, 28), sign.move(0, 6), border_radius=10)
    pygame.draw.rect(surface, (104, 64, 34), sign, border_radius=10)
    pygame.draw.rect(surface, (226, 174, 82), sign, width=5, border_radius=10)
    pygame.draw.rect(surface, (135, 86, 42), sign.inflate(-18, -18), width=2)
    font = pygame.font.Font(None, 50)
    label = font.render("HEROES FOR HIRE", True, (255, 236, 180))
    surface.blit(label, label.get_rect(center=sign.center))


def draw_exterior_props(surface: pygame.Surface, building: pygame.Rect) -> None:
    board = pygame.Rect(building.left + 48, building.bottom - 180, 174, 126)
    pygame.draw.rect(surface, (56, 36, 24), board.move(0, 6), border_radius=8)
    pygame.draw.rect(surface, (98, 64, 36), board, border_radius=8)
    pygame.draw.rect(surface, (206, 154, 76), board, width=3, border_radius=8)
    for index, label in enumerate(("NOW HIRING", "NIGHT PAY")):
        paper = pygame.Rect(board.left + 18, board.top + 20 + index * 48, 138, 34)
        pygame.draw.rect(surface, (238, 224, 178), paper)
        text = pygame.font.Font(None, 22).render(label, True, (62, 43, 30))
        surface.blit(text, text.get_rect(center=paper.center))

    barrel = pygame.Rect(building.right - 136, building.bottom - 80, 48, 58)
    pygame.draw.ellipse(surface, (115, 73, 38), (barrel.left, barrel.top - 8, 48, 16))
    pygame.draw.rect(surface, (98, 58, 32), barrel, border_radius=8)
    pygame.draw.ellipse(surface, (63, 40, 26), (barrel.left, barrel.bottom - 9, 48, 18))
    pygame.draw.line(surface, (194, 143, 76), barrel.midleft, barrel.midright, 3)


def draw_employment_center_background(
    surface: pygame.Surface,
    mouse_position: tuple[int, int] | None = None,
) -> None:
    offset = parallax(mouse_position, 10)
    vertical_gradient(surface, (64, 47, 34), (34, 25, 20))

    wall_shift = offset * 0.18
    for x in range(-80, SCREEN_WIDTH + 120, 112):
        plank = pygame.Rect(round(x + wall_shift.x), 0, 106, SCREEN_HEIGHT)
        pygame.draw.rect(surface, (73, 50, 32), plank)
        pygame.draw.rect(surface, (45, 31, 22), plank, width=2)
        pygame.draw.line(
            surface,
            (95, 66, 41),
            (plank.left + 18, 0),
            (plank.left + 42, SCREEN_HEIGHT),
            2,
        )

    board = pygame.Rect(86, 68, SCREEN_WIDTH - 172, SCREEN_HEIGHT - 118)
    board.move_ip(round(offset.x * 0.25), round(offset.y * 0.25))
    pygame.draw.rect(surface, (32, 22, 16), board.move(0, 14), border_radius=20)
    pygame.draw.rect(surface, (103, 65, 35), board.inflate(34, 34), border_radius=22)
    pygame.draw.rect(surface, (184, 132, 70), board.inflate(34, 34), width=8, border_radius=22)
    pygame.draw.rect(surface, (151, 92, 45), board, border_radius=18)

    for y in range(board.top + 22, board.bottom, 34):
        pygame.draw.line(surface, (132, 78, 38), (board.left + 18, y), (board.right - 18, y), 1)
    for x in range(board.left + 28, board.right, 42):
        pygame.draw.line(
            surface,
            (166, 103, 52),
            (x, board.top + 12),
            (x - 28, board.bottom - 12),
            1,
        )

    header = pygame.Rect(0, 0, 640, 82)
    header.center = (SCREEN_WIDTH // 2, board.top + 58)
    pygame.draw.rect(surface, (52, 34, 23), header.move(0, 6), border_radius=10)
    pygame.draw.rect(surface, (247, 226, 174), header, border_radius=10)
    pygame.draw.rect(surface, (82, 52, 30), header, width=4, border_radius=10)
    font = pygame.font.Font(None, 58)
    title = font.render("HEROES FOR HIRE", True, (71, 43, 25))
    surface.blit(title, title.get_rect(center=header.center))

    for point in (
        board.topleft,
        board.topright,
        board.bottomleft,
        board.bottomright,
        header.topleft,
        header.topright,
    ):
        pygame.draw.circle(surface, (137, 24, 20), point, 10)
        pygame.draw.circle(surface, (232, 92, 64), (point[0] - 3, point[1] - 3), 4)


def draw_squiggly_lines(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (96, 74, 52),
) -> None:
    for row in range(4):
        y = rect.top + 64 + row * 23
        points = []
        for step in range(10):
            x = rect.left + 28 + step * ((rect.width - 56) / 9)
            wave = 3 if step % 2 == 0 else -3
            points.append((round(x), y + wave))
        pygame.draw.lines(surface, color, False, points, 2)
