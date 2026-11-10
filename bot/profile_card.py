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

# Вёрстка меняется кодом, а кеш — по исходным фото. Без этого штампа новая
# вёрстка не доехала бы до уже отрисованных карточек.
CODE_STAMP = Path(__file__).stat().st_mtime

# Подпись не должна залезать под кнопки: ширина карточки минус поля.
TEXT_WIDTH = SIZE - 2 * (MARGIN + 40)

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


def card_caption(scenario: Scenario, photo_name: str) -> str:
    """Текст на карточке: подпись конкретного фото, иначе — профессия.

    Раньше на всех карточках стояла только профессия. Теперь подпись своя у
    каждого кадра: работа и «о себе», хобби и интересы, чего она ищет, — и на
    скриншоте анкеты видна вся её жизнь, а не только место работы.
    """
    profile = scenario.profile
    if profile is not None:
        caption = profile.captions.get(photo_name, "").strip()
        if caption:
            return caption
    return scenario.persona.job


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

    # Имя и подписи живут в scenario.json: их правка тоже должна сбрасывать кеш.
    data_stamp = 0.0
    data_file = scenario.dir / "scenario.json"
    if data_file.is_file():
        data_stamp = data_file.stat().st_mtime

    cards: list[Path] = []
    total = len(sources)
    for index, (source, name) in enumerate(sources):
        target = card_dir / f"{Path(name).stem}.jpg"
        # Перерисовываем, если фото, код карточки или данные сценария новее файла.
        if not target.is_file() or target.stat().st_mtime < max(
            source.stat().st_mtime, CODE_STAMP, data_stamp
        ):
            _render_card(
                source,
                target,
                index,
                total,
                scenario,
                card_caption(scenario, name),
            )
        cards.append(target)
    return cards


def _render_card(
    source: Path,
    target: Path,
    index: int,
    total: int,
    scenario: Scenario,
    caption: str,
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

    # Затемнение снизу: на нём читаются имя, подпись и кнопки.
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shade = ImageDraw.Draw(overlay)
    shade_top = SIZE - 520
    for y in range(shade_top, SIZE):
        ratio = (y - shade_top) / max(1, SIZE - shade_top)
        alpha = int(215 * (ratio ** 1.35))
        shade.rectangle(
            [MARGIN, y, SIZE - MARGIN, y], fill=(8, 8, 12, alpha)
        )
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(canvas)
    label_font = _font(30, bold=True)
    counter_font = _font(32)
    name_font = _font(68, bold=True)
    caption_font = _font(36)

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

    # Имя и подпись к этому кадру — у самого нижнего края, над кнопками.
    # Позиция считается от низа: подпись прижимается, имя встаёт над ней, поэтому
    # даже длинная подпись не заезжает на кнопки приложения.
    caption_lines = _wrap_lines(draw, caption, caption_font)
    caption_step = _line_height(caption_font) + 8
    caption_top = (
        SIZE - 176 - caption_step * (len(caption_lines) - 1) - _line_height(caption_font)
    )
    name_top = caption_top - 14 - _line_height(name_font)
    draw.text(
        (MARGIN + 40, name_top),
        f"{scenario.persona.name}, {scenario.persona.age}",
        font=name_font,
        fill=(255, 255, 255),
    )
    for line_index, text_line in enumerate(caption_lines):
        draw.text(
            (MARGIN + 42, caption_top + line_index * caption_step),
            text_line,
            font=caption_font,
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


def _wrap_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    width: int = TEXT_WIDTH,
) -> list[str]:
    """Разбивает подпись по словам: в кадр влезает одна–три строки."""
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and draw.textlength(candidate, font=font) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines or [""]


def _line_height(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
    return int(getattr(font, "size", 24))


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
