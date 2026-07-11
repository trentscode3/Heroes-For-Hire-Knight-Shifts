import pygame

from core.ui_font import ui_font


WARRIOR_SKILLS = (
    ("conditioning", "Conditioning", "+25% movement and attack speed"),
    ("new_sword", "New Sword", "+25% damage and size"),
    ("slash_and_dash", "Slash and Dash", "Fast stopping dash slash"),
    ("whistle", "Whistle", "Direct focused reinforcements"),
    ("kinetic_conversion", "Kinetic Conversion", "Speed becomes damage"),
    ("sword_spin", "Sword Spin", "Full-circle attack"),
    ("well_equipped_soldiers", "Well Equipped Soldiers", "Reinforcement gear"),
    ("energy_core", "Energy Core", "+25% attack speed, +25% movement, enemy pull"),
    ("heavier_sword", "Heavier Sword", "An additional stronger spin"),
    ("elite_soldiers", "Elite Soldiers", "Slower elite spawns, much stronger soldiers"),
)
WARRIOR_CONNECTIONS = (
    ("conditioning", "new_sword"),
    ("new_sword", "slash_and_dash"),
    ("new_sword", "whistle"),
    ("slash_and_dash", "kinetic_conversion"),
    ("slash_and_dash", "sword_spin"),
    ("whistle", "kinetic_conversion"),
    ("whistle", "well_equipped_soldiers"),
    ("sword_spin", "heavier_sword"),
    ("kinetic_conversion", "energy_core"),
    ("well_equipped_soldiers", "elite_soldiers"),
)


def draw_skill_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    skill_id: str,
    color: tuple[int, int, int] = (225, 225, 230),
) -> None:
    """Draw a compact symbolic graphic for one Knowledge node."""
    center = pygame.Vector2(rect.center)
    if skill_id in ("new_sword", "heavier_sword"):
        pygame.draw.line(surface, color, center + (-10, 11), center + (10, -11), 5)
        pygame.draw.line(surface, (120, 75, 35), center + (-13, 14), center + (-6, 7), 5)
    elif skill_id == "conditioning":
        pygame.draw.line(surface, color, center + (-7, -11), center + (-11, 8), 5)
        pygame.draw.line(surface, color, center + (6, -8), center + (12, 8), 5)
        pygame.draw.line(surface, color, center + (-11, 8), center + (-21, 8), 5)
        pygame.draw.line(surface, color, center + (12, 8), center + (21, 8), 5)
    elif skill_id in ("slash_and_dash", "sword_spin"):
        pygame.draw.arc(surface, color, rect.inflate(-4, -4), 0.2, 2.8, 4)
        pygame.draw.polygon(
            surface,
            color,
            (rect.midleft, (rect.left + 9, rect.centery - 7), (rect.left + 11, rect.centery + 7)),
        )
    elif skill_id == "whistle":
        pygame.draw.circle(surface, color, rect.center, 9, 3)
        pygame.draw.line(surface, color, rect.center, rect.midright, 3)
    elif skill_id == "kinetic_conversion":
        points = (rect.midtop, rect.center, rect.midleft, rect.midbottom, rect.midright)
        pygame.draw.polygon(surface, color, points, 3)
    elif skill_id == "well_equipped_soldiers":
        pygame.draw.rect(surface, color, rect.inflate(-12, -7), width=3)
        pygame.draw.line(surface, color, rect.midtop, rect.midbottom, 3)
    elif skill_id == "energy_core":
        body = rect.inflate(-18, -14)
        pygame.draw.rect(surface, color, body, width=3, border_radius=3)
        pygame.draw.rect(surface, color, (body.right, body.centery - 5, 5, 10))
        bolt = (
            (body.centerx - 2, body.top + 5),
            (body.centerx - 8, body.centery + 1),
            (body.centerx + 1, body.centery + 1),
            (body.centerx - 4, body.bottom - 5),
            (body.centerx + 9, body.centery - 3),
            (body.centerx + 1, body.centery - 3),
        )
        pygame.draw.polygon(surface, color, bolt)
    elif skill_id == "elite_soldiers":
        for offset, accent in ((-9, color), (9, (230, 190, 70))):
            soldier = pygame.Rect(0, 0, 13, 24)
            soldier.center = (rect.centerx + offset, rect.centery + 2)
            pygame.draw.circle(surface, accent, (soldier.centerx, soldier.top), 5)
            pygame.draw.rect(surface, accent, soldier.inflate(-3, -7), width=3)


def draw_book_icon(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int] = (226, 205, 145),
    outline_color: tuple[int, int, int] = (105, 75, 45),
    accent_color: tuple[int, int, int] | None = None,
) -> None:
    left = pygame.Rect(rect.left, rect.top + 3, rect.width // 2, rect.height - 6)
    right = pygame.Rect(rect.centerx, rect.top + 3, rect.width - rect.width // 2, rect.height - 6)
    pygame.draw.polygon(
        surface,
        color,
        (left.topleft, left.topright, left.bottomright, left.bottomleft),
    )
    pygame.draw.polygon(
        surface,
        color,
        (right.topleft, right.topright, right.bottomright, right.bottomleft),
    )
    accent_color = accent_color or outline_color
    pygame.draw.line(surface, accent_color, rect.midtop, rect.midbottom, 2)
    pygame.draw.line(
        surface,
        accent_color,
        (left.left + 5, left.top + 8),
        (left.right - 4, left.top + 8),
        2,
    )
    pygame.draw.line(
        surface,
        accent_color,
        (right.left + 4, right.top + 8),
        (right.right - 5, right.top + 8),
        2,
    )
    pygame.draw.rect(surface, outline_color, rect, width=2, border_radius=3)


def draw_knowledge_tree(
    surface: pygame.Surface,
    rect: pygame.Rect,
    unlocked: set[str] | None = None,
    branch_unlocked: bool = False,
    compact: bool = False,
    show_title: bool = True,
) -> None:
    unlocked = unlocked or set()
    title_font = ui_font(24 if compact else 29)
    text_font = ui_font(19 if compact else 22)
    if show_title:
        title = title_font.render("THE KNOWLEDGE TREE", True, (235, 210, 120))
        surface.blit(title, (rect.left, rect.top))

    top = rect.top + (30 if show_title else 5)
    cx = rect.centerx
    positions = {
        "conditioning": (cx, top + 12),
        "new_sword": (cx, top + 62),
        "slash_and_dash": (cx - rect.width * 0.24, top + 116),
        "whistle": (cx + rect.width * 0.24, top + 116),
        "kinetic_conversion": (cx - rect.width * 0.34, top + 177),
        "sword_spin": (cx, top + 177),
        "well_equipped_soldiers": (cx + rect.width * 0.34, top + 177),
        "energy_core": (cx - rect.width * 0.34, top + 238),
        "heavier_sword": (cx, top + 238),
        "elite_soldiers": (cx + rect.width * 0.34, top + 238),
    }
    for start, end in WARRIOR_CONNECTIONS:
        pygame.draw.line(surface, (105, 130, 170), positions[start], positions[end], 3)
    labels = {skill_id: name for skill_id, name, _effect in WARRIOR_SKILLS}
    radius = 12 if compact else 15
    for skill_id, center in positions.items():
        learned = skill_id in unlocked
        available = skill_id not in ("slash_and_dash", "whistle") or branch_unlocked
        if learned:
            fill, outline = (55, 170, 85), (120, 230, 145)
        elif available:
            fill, outline = (45, 62, 92), (140, 160, 195)
        else:
            fill, outline = (50, 50, 55), (95, 95, 105)
        pygame.draw.circle(surface, fill, center, radius)
        pygame.draw.circle(surface, outline, center, radius, 3)
        label = text_font.render(labels[skill_id], True, outline)
        max_width = rect.width // 3
        if label.get_width() > max_width:
            height = max(
                1,
                round(label.get_height() * max_width / label.get_width()),
            )
            label = pygame.transform.smoothscale(label, (max_width, height))
        surface.blit(label, label.get_rect(midtop=(center[0], center[1] + radius + 2)))
