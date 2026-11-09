"""Карточка анкеты как в приложении знакомств: UI рисуем кодом поверх фото.

Текст и иконки нельзя просить у модели: на сгенерированных картинках буквы
превращаются в кашу. Поэтому фото берётся готовое, а интерфейс — подпись, счётчик,
точки и кнопки «пролистнуть» — рисуется здесь, читаемым шрифтом.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .scenario import Scenario

ROOT = Path(__file__).resolve().parent.parent
CARD_DIR = ROOT / ".tmp" / "profile_cards"

SIZE = 1024
MARGIN = 36
RADIUS = 44

_FONT_BOLD = Path("C:/Windows/Fonts/arialbd.ttf")
_FONT_REGULAR = Path("C:/Windows/Fonts/arial.ttf")
_FALLBACKS = (
    Path("C:/Windows/Fonts/segoeuib.ttf"),
    Path("C:/Windows/Fonts/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (_FONT_BOLD if bold else _FONT_REGULAR, *_FALLBACKS)
    for path in candidates:
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_profile_cards(scenario: Scenario) -> list[Path]:
    """Собирает карточки анкеты из фото сценария. Пусто — если фото нет."""
    profile = scenario.profile
    if profile is None:
        return []

    sources = [
        (scenario.faces_dir / name, name)
        for name in profile.photos
        if (scenario.faces_dir / name).is_file()
    ]
    if not sources:
        return []

    card_dir = CARD_DIR / scenario.id
    card_dir.mkdir(parents=True, exist_ok=True)

    cards: list[Path] = []
    total = len(sources)
    for index, (source, name) in enumerate(sources):
        target = card_dir / f"{Path(name).stem}.jpg"
        # Перерисовываем только если фото новее готовой карточки.
        if not target.is_file() or target.stat().st_mtime < source.stat().st_mtime:
            _render_card(source, target, index, total, scenario)
        cards.append(target)
    return cards


def _render_card(
    source: Path,
    target: Path,
    index: int,
    total: int,
    scenario: Scenario,
) -> None:
    base = Image.open(source).convert("RGB")
    side = min(base.size)
    left = (base.width - side) // 2
    top = (base.height - side) // 2
    base = base.crop((left, top, left + side, top + side))

    inner = SIZE - 2 * MARGIN
    photo = base.resize((inner, inner), Image.LANCZOS)

    canvas = Image.new("RGB", (SIZE, SIZE), (16, 16, 20))
    mask = Image.new("L", (inner, inner), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, inner - 1, inner - 1], radius=RADIUS, fill=255
    )
    canvas.paste(photo, (MARGIN, MARGIN), mask)

    # Затемнение снизу: на нём читаются имя, профессия и кнопки.
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shade = ImageDraw.Draw(overlay)
    shade_top = SIZE - 430
    for y in range(shade_top, SIZE):
        ratio = (y - shade_top) / max(1, SIZE - shade_top)
        alpha = int(215 * (ratio ** 1.35))
        shade.rectangle(
            [MARGIN, y, SIZE - MARGIN, y], fill=(8, 8, 12, alpha)
        )
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(canvas)
    label_font = _font(26, bold=True)
    counter_font = _font(28)
    name_font = _font(64, bold=True)
    job_font = _font(30)

    # Шапка карточки.
    draw.text((MARGIN + 30, MARGIN + 24), "АНКЕТА", font=label_font, fill=(245, 245, 250))
    counter = f"{index + 1}/{total}"
    counter_width = draw.textlength(counter, font=counter_font)
    draw.text(
        (SIZE - MARGIN - 30 - counter_width, MARGIN + 22),
        counter,
        font=counter_font,
        fill=(240, 240, 245),
    )

    # Подпись снизу.
    draw.text(
        (MARGIN + 40, SIZE - 256),
        f"{scenario.persona.name}, {scenario.persona.age}",
        font=name_font,
        fill=(255, 255, 255),
    )
    draw.text(
        (MARGIN + 42, SIZE - 170),
        scenario.persona.job,
        font=job_font,
        fill=(228, 228, 236),
    )

    # Точки-индикатор, как под карточкой в приложении.
    dot_y = SIZE - 96
    for dot in range(total):
        x = MARGIN + 46 + dot * 34
        if dot == index:
            draw.ellipse([x, dot_y - 8, x + 16, dot_y + 8], fill=(255, 255, 255))
        else:
            draw.ellipse(
                [x, dot_y - 8, x + 16, dot_y + 8],
                outline=(255, 255, 255),
                width=2,
            )

    # Кнопки «пролистнуть» и «нравится».
    _cross_button(draw, SIZE - MARGIN - 200, SIZE - 112, 40)
    _heart_button(draw, SIZE - MARGIN - 92, SIZE - 112, 40)

    canvas.save(target, format="JPEG", quality=90, optimize=True)


def _cross_button(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int) -> None:
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=(255, 255, 255),
        width=3,
    )
    arm = radius * 0.38
    draw.line([cx - arm, cy - arm, cx + arm, cy + arm], fill=(255, 255, 255), width=5)
    draw.line([cx - arm, cy + arm, cx + arm, cy - arm], fill=(255, 255, 255), width=5)


def _heart_button(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int) -> None:
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=(255, 255, 255),
        width=3,
    )
    size = radius * 0.62
    fill = (255, 255, 255)
    draw.ellipse(
        [cx - size, cy - size * 1.1, cx - size * 0.05, cy + size * 0.15], fill=fill
    )
    draw.ellipse(
        [cx + size * 0.05, cy - size * 1.1, cx + size, cy + size * 0.15], fill=fill
    )
    draw.polygon(
        [
            (cx - size, cy - size * 0.25),
            (cx + size, cy - size * 0.25),
            (cx, cy + size * 1.15),
        ],
        fill=fill,
    )
