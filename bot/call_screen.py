"""Экран исходящего звонка как в Android: фото сценария, интерфейс — кодом.

Буквы на сгенерированных картинках превращаются в кашу, поэтому лицо берётся
готовым, а «ВЫЗОВ», имя, тип звонка и красную трубку рисуем здесь — тем же
подходом, что и карточку анкеты в `profile_card.py`: шрифты с фолбэками,
кеш в `.tmp`, LANCZOS и плавное затемнение краёв.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .scenario import Scenario

ROOT = Path(__file__).resolve().parent.parent
CALL_DIR = ROOT / ".tmp" / "call_screens"

CALL_PHOTO = "call.jpg"
SIZE = 1024

# Затемнение сверху — под подпись звонка, снизу — под имя, статус и кнопку.
_TOP_SHADE = 280
_BOTTOM_SHADE = 560

_BUTTON_CENTER = (SIZE // 2, SIZE - 140)
_BUTTON_RADIUS = 64

# Блок имени ниже лица: на экране звонка текст не должен закрывать глаза и рот.
_NAME_Y = 596
_TYPE_Y = 660
_STATUS_Y = 720

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


def render_call_screen(scenario: Scenario) -> Path | None:
    """Собирает экран звонка из `images/call.jpg`. Нет фото — нет экрана."""
    source = scenario.faces_dir / CALL_PHOTO
    if not source.is_file():
        return None

    target = CALL_DIR / scenario.id / "call.jpg"
    # Перерисовываем, если фото, код экрана или данные сценария новее файла.
    code_stamp = Path(__file__).stat().st_mtime
    data_stamp = 0.0
    data_file = scenario.dir / "scenario.json"
    if data_file.is_file():
        data_stamp = data_file.stat().st_mtime
    if target.is_file() and target.stat().st_mtime >= max(
        source.stat().st_mtime, code_stamp, data_stamp
    ):
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    _render_screen(source, target, scenario)
    return target


def _render_screen(source: Path, target: Path, scenario: Scenario) -> None:
    with Image.open(source) as raw:
        photo = raw.convert("RGB")

    # Кроп по центру квадратом: фото должно закрыть весь кадр без полей.
    side = min(photo.size)
    left = (photo.width - side) // 2
    top = (photo.height - side) // 2
    photo = photo.crop((left, top, left + side, top + side))
    canvas = photo.resize((SIZE, SIZE), Image.LANCZOS)

    _darken_edges(canvas)

    # RGBA-режим у Draw включает альфа-смешивание на RGB-холсте:
    # так полупрозрачный текст ложится на фото, а не затирает его.
    draw = ImageDraw.Draw(canvas, "RGBA")

    label_font = _font(27, bold=True)
    name_font = _font(78, bold=True)
    type_font = _font(30)
    status_font = _font(34)

    # Шапка: мелкая разрядка по центру, как строка состояния звонка.
    _spaced_text(
        draw,
        center_x=SIZE // 2,
        top_y=66,
        text="ИСХОДЯЩИЙ ВЫЗОВ",
        font=label_font,
        fill=(255, 255, 255, 185),
        spacing=6,
    )

    # Тень у текста: фото бывает светлым, и без неё серый «мобильный» теряется.
    shadow = (10, 10, 14, 130)
    center_x = SIZE // 2
    draw.text(
        (center_x, _NAME_Y),
        scenario.persona.name,
        font=name_font,
        fill=(255, 255, 255),
        anchor="mm",
        stroke_width=3,
        stroke_fill=shadow,
    )
    draw.text(
        (center_x, _TYPE_Y),
        "мобильный",
        font=type_font,
        fill=(222, 222, 228),
        anchor="mm",
        stroke_width=2,
        stroke_fill=shadow,
    )
    draw.text(
        (center_x, _STATUS_Y),
        "Вызов…",
        font=status_font,
        fill=(245, 245, 248),
        anchor="mm",
        stroke_width=2,
        stroke_fill=shadow,
    )

    _hang_up_button(canvas)

    canvas.save(target, format="JPEG", quality=90, optimize=True)


def _darken_edges(canvas: Image.Image) -> None:
    """Плавный градиент сверху и снизу: текст и кнопка читаются на любом фото."""
    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shade = ImageDraw.Draw(overlay)

    # Лёгкая общая вуаль входит в альфу градиента: фото остаётся собой,
    # но белый текст не слепит на нём. Отдельным слоем её класть нельзя —
    # построчные прямоугольники затрут её и на границе появится шов.
    veil = 40

    for y in range(_TOP_SHADE):
        ratio = 1 - y / _TOP_SHADE
        alpha = min(255, veil + int(200 * (ratio ** 1.35)))
        shade.rectangle([0, y, SIZE, y + 1], fill=(8, 8, 12, alpha))

    bottom_top = SIZE - _BOTTOM_SHADE
    for y in range(bottom_top, SIZE):
        ratio = (y - bottom_top) / max(1, SIZE - bottom_top)
        alpha = min(255, veil + int(215 * (ratio ** 1.35)))
        shade.rectangle([0, y, SIZE, y + 1], fill=(8, 8, 12, alpha))

    # Середина — ровная вуаль, без градиента.
    shade.rectangle([0, _TOP_SHADE, SIZE, bottom_top], fill=(8, 8, 12, veil))

    canvas.paste(Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB"))


def _spaced_text(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    top_y: int,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    spacing: int,
) -> None:
    """Текст в разрядку: между буквами вставляем пробелы вручную."""
    widths = [draw.textlength(char, font=font) for char in text]
    total = sum(widths) + spacing * max(0, len(text) - 1)
    x = center_x - total / 2
    for char, width in zip(text, widths):
        draw.text((x, top_y), char, font=font, fill=fill)
        x += width + spacing


def _hang_up_button(canvas: Image.Image) -> None:
    """Красный круг с белой трубкой: единственная кнопка — сбросить звонок."""
    cx, cy = _BUTTON_CENTER
    radius = _BUTTON_RADIUS

    draw = ImageDraw.Draw(canvas, "RGBA")
    # Мягкая тень, чтобы круг не «прилипал» к фото.
    draw.ellipse(
        [cx - radius, cy - radius + 8, cx + radius, cy + radius + 12],
        fill=(0, 0, 0, 90),
    )
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=(220, 58, 52),
    )

    icon = _handset(int(radius * 1.2))
    canvas.paste(icon, (cx - icon.width // 2, cy - icon.height // 2), icon)


def _handset(size: int) -> Image.Image:
    """Трубка: дуга с утолщёнными концами, повёрнутая как на кнопке сброса.

    Рисуем с четырёхкратным запасом и уменьшаем LANCZOS — иначе диагональ
    получается рваной на маленькой иконке.
    """
    scale = 4
    side = size * scale
    layer = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    middle = side / 2
    radius = side * 0.31
    thickness = int(side * 0.17)
    box = [middle - radius, middle - radius, middle + radius, middle + radius]
    draw.arc(box, start=25, end=155, fill=(255, 255, 255, 255), width=thickness)

    # Утолщаем концы: у настоящей трубки на концах «чашки», а не срез дуги.
    end_radius = thickness * 0.62
    for angle in (25, 155):
        radians = math.radians(angle)
        end_x = middle + radius * math.cos(radians)
        end_y = middle + radius * math.sin(radians)
        draw.ellipse(
            [
                end_x - end_radius,
                end_y - end_radius,
                end_x + end_radius,
                end_y + end_radius,
            ],
            fill=(255, 255, 255, 255),
        )

    rotated = layer.rotate(-45, resample=Image.BICUBIC)
    return rotated.resize((size, size), Image.LANCZOS)
