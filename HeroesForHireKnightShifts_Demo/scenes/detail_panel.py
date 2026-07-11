import pygame


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """Wrap text to a pixel width while preserving explicit line breaks."""
    lines: list[str] = []
    for paragraph in text.splitlines() or ("",):
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if current and font.size(candidate)[0] > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return lines


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill: tuple[int, int, int],
    border: tuple[int, int, int],
) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=10)
    pygame.draw.rect(surface, border, rect, width=2, border_radius=10)


def draw_action_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    font: pygame.font.Font,
    enabled: bool,
) -> None:
    fill = (60, 132, 78) if enabled else (72, 72, 76)
    border = (145, 225, 160) if enabled else (120, 120, 125)
    pygame.draw.rect(surface, fill, rect, border_radius=7)
    pygame.draw.rect(surface, border, rect, width=2, border_radius=7)
    text = font.render(label, True, (245, 245, 245))
    if text.get_width() > rect.width - 16:
        width = rect.width - 16
        height = max(1, round(text.get_height() * width / text.get_width()))
        text = pygame.transform.smoothscale(text, (width, height))
    surface.blit(text, text.get_rect(center=rect.center))
