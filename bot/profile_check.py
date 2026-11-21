"""«Проверка анкеты»: разбор текста и фото анкеты сайта знакомств.

Отдельный флоу, не сценарий: нет героини, ходов и рубрики - пользователь
присылает имя/возраст и текст, получает разбор, затем по желанию
присылает до 4 фото и получает оценку каждого кадра и набора целиком.

Численный счёт пользователю не показывается - только вердикты, флаги и
метки ✅/❌; сырой счёт хранится в базе (last_text_score). Флаги и тексты
промптов лежат в `scenarios/profile_check/config.json` - правятся без кода.
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from .scenario import ROOT

CONFIG_PATH = ROOT / "scenarios" / "profile_check" / "config.json"

# Бонусные ходы диалога с героиней при заполненной анкете: разговор с человеком,
# о котором что-то известно, выдерживает дольше. Файлы сценариев не трогаем.
PROFILE_BONUS_TURNS = 3

# Слова, которые не могут быть именем при разборе «имя + возраст».
_NOT_NAME = {"мне", "я", "меня", "зовут", "лет", "год", "года", "имя", "мой", "моя"}


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    """Конфиг флоу: флаги, лимиты, тексты. Кешируется - правка требует рестарта."""
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{CONFIG_PATH}: ожидался объект JSON")
    return data


def t(key: str, **fmt: Any) -> str:
    """Текст интерфейса из конфига с подстановкой {плейсхолдеров}."""
    value = load_config()["texts"][key]
    return value.format(**fmt) if fmt else value


def parse_name_age(text: str, age_min: int = 18, age_max: int = 99) -> tuple[str, int] | None:
    """«Саша, 32» → («Саша», 32). None - если возраст или имя не вытащить.

    Возраст - первое число в допустимом диапазоне. Имя - слово после «зовут»,
    иначе первое слово, которое не число и не служебное.
    """
    numbers = [int(n) for n in re.findall(r"\d+", text)]
    ages = [n for n in numbers if age_min <= n <= age_max]
    if not ages:
        return None

    tokens = re.findall(r"[А-Яа-яЁёA-Za-z-]+", text)
    name = ""
    for index, token in enumerate(tokens):
        if token.lower() in _NOT_NAME:
            continue
        if token.lower() == "зовут" and index + 1 < len(tokens):
            name = tokens[index + 1]
            break
        name = token
        break
    name = name.strip("-")
    if not name or len(name) > 30:
        return None
    return name[0].upper() + name[1:], ages[0]


# Анкета «похожа на анкету» от 15 слов: строка «Саша, 32» и вежливое «привет,
# проверь меня» до этого порога не дотягивают.
BIO_MIN_WORDS = 15
# Начало сообщения с именем и возрастом не длиннее: больше слов - это уже проза
# анкеты, и «имя» из неё parse_name_age вытащит по ошибке.
INTRO_MAX_WORDS = 10


def looks_like_bio(text: str) -> bool:
    """Длинное сообщение похоже на анкету, а не на строку «Саша, 32»."""
    return len(text.split()) >= BIO_MIN_WORDS


def split_intro_bio(text: str, age_min: int, age_max: int) -> tuple[str, str]:
    """Отделяет начало с именем и возрастом от самой анкеты.

    «Саша, 32\n<анкета>» - режем по первой строке; одна строка - по границе
    первого предложения («Меня зовут Саша, мне 32 года. <анкета>»), если оно
    короткое, парсится и после него остаётся анкета. Иначе всё сообщение
    считается анкетой без начала.
    """
    intro, sep, bio = text.partition("\n")
    if sep:
        return intro.strip(), bio.strip()
    match = re.search(r"(?<=[.!?])\s+", text)
    if match:
        head, tail = text[: match.end()].strip(), text[match.end():].strip()
        if (
            len(head.split()) <= INTRO_MAX_WORDS
            and parse_name_age(head, age_min, age_max) is not None
            and looks_like_bio(tail)
        ):
            return head, tail
    return text, ""


@dataclass
class Flag:
    type: str  # "red" | "green"
    title: str
    quote: str = ""
    comment: str = ""


@dataclass
class TextReview:
    verdict: str
    flags: list[Flag]
    rewrite_after: str = ""
    score: int = 0
    greens: int = 0
    reds: int = 0


@dataclass
class PhotoVerdict:
    index: int
    keep: bool
    verdict: str
    flags: list[Flag] = field(default_factory=list)


@dataclass
class PhotoReview:
    photos: list[PhotoVerdict]
    set_verdict: str
    set_flags: list[Flag] = field(default_factory=list)
    set_advice: str = ""
    same_person: bool | None = None
    # Нейтральное «что на фото» (3-6 слов на кадр): без оценок - это выжимка
    # для героинь, чтобы им было о чём спросить, а не список претензий.
    contents: list[str] = field(default_factory=list)


def _score(flags: list[Flag]) -> int:
    return sum(1 if flag.type == "green" else -1 for flag in flags)


def _parse_flags(raw: Any, limit: int = 8) -> list[Flag]:
    flags: list[Flag] = []
    if not isinstance(raw, list):
        return flags
    for item in raw[: limit * 2]:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type", "")).strip().lower()
        title = str(item.get("title", "")).strip()
        if kind not in ("red", "green") or not title:
            continue
        flags.append(
            Flag(
                type=kind,
                title=title,
                quote=str(item.get("quote", "")).strip(),
                comment=str(item.get("comment", "")).strip(),
            )
        )
        if len(flags) >= limit:
            break
    return flags


def consultant_messages(
    name: str, age: int, bio: str, prev_rewrite: str = ""
) -> list[dict[str, str]]:
    """Запрос к deepseek-chat: разбор текста анкеты. Баллы считает код."""
    cfg = load_config()
    reds = "\n".join(f"- {item}" for item in cfg["text_red_flags"])
    greens = "\n".join(f"- {item}" for item in cfg["text_green_flags"])
    low, high = cfg["recommended_length"]
    prev_block = ""
    if prev_rewrite.strip():
        prev_block = f"""Твоя прошлая рекомендация («как переписать» из прошлого разбора):
{prev_rewrite.strip()}

"""
    system = f"""Ты - консультант по анкетам сайта знакомств. Мужчина прислал свою анкету
на проверку: помоги сделать её привлекательной. Тон: {cfg['tone']}

Что считать красными флагами:
{reds}

Что считать зелёными флагами:
{greens}

{prev_block}Правила:
- Обращайся к нему на «ты». Без насмешки, без похвалы в пустоту: конкретика.
- Каждый флаг - с цитатой из его текста (для красных обязательно) и коротким
  комментарием, что не так и как исправить.
- Если текст целиком или почти целиком совпадает с твоей прошлой рекомендацией -
  это принятое предложение, а не материал для нового разбора: придумывать новые
  придирки к собственной рекомендации запрещено. Нормальный ответ в этом случае -
  зелёный флаг за внедрённую правку, 0 красных флагов и пустой rewrite. Красный
  флаг здесь допустим только для серьёзного (грубость, ложь, отталкивающая
  формулировка) и только в том, что он дописал сам сверх рекомендации.
- Флагов обычно 2-6, но 0 - нормальный ответ для сильной анкеты: не выискивай
  мелочи и не выдумывай претензии ради минимума.
- Претензия должна быть фактически верной для своей цитаты: перечитай цитату и
  убедись, что проблема в ней реально есть. Если текст ясно сообщает факт,
  нельзя писать, что он непонятен или смазан.
- Рекомендуемая длина анкеты {low}-{high} слов: короче - пусто, длиннее - не читают.
- Ориентир структуры: крючок в первой строке (характер или юмор), 3-5 конкретик,
  приглашение к диалогу (вопрос или «спорьте со мной»), одна короткая честность
  про важное - без списка «не пиши мне, если…».
- Если красных флагов нет, верни в rewrite пустую строку. Если есть - верни
  полный текст откорректированной анкеты целиком: сохрани всё удачное, исправь
  все места с красными флагами, без штампов и в тех же пределах длины.
  Пользователь скопирует этот текст себе на страницу как есть - без кавычек,
  пояснений и пометок в самом тексте.
- Факты - только из его анкеты: ничего не выдумывай и не добавляй от себя.

Верни строго JSON:
{{"verdict": "1-2 предложения: общее впечатление и главное, что менять",
 "flags": [{{"type": "red", "title": "короткое название", "quote": "цитата из анкеты", "comment": "что не так и как исправить"}}],
 "rewrite": "полный текст откорректированной анкеты или пустая строка, если правки не нужны"}}"""
    user = f"Анкета.\nИмя: {name}\nВозраст: {age}\nТекст «О себе»:\n{bio}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def parse_text_review(data: dict[str, Any]) -> TextReview:
    flags = _parse_flags(data.get("flags"))
    greens = sum(1 for flag in flags if flag.type == "green")
    reds = len(flags) - greens
    rewrite = data.get("rewrite")
    if isinstance(rewrite, dict):  # старый формат {before, after}
        rewrite = rewrite.get("after", "")
    return TextReview(
        verdict=str(data.get("verdict", "")).strip(),
        flags=flags,
        rewrite_after=str(rewrite or "").strip(),
        score=greens - reds,
        greens=greens,
        reds=reds,
    )


def render_text_review(review: TextReview) -> str:
    lines = [review.verdict, ""]
    reds = [flag for flag in review.flags if flag.type == "red"]
    greens = [flag for flag in review.flags if flag.type == "green"]
    if reds:
        lines.append("🚩 Красные флаги:")
        for flag in reds:
            quote = f" - «{flag.quote}»" if flag.quote else ""
            comment = f": {flag.comment}" if flag.comment else ""
            lines.append(f"• {flag.title}{quote}{comment}")
        lines.append("")
    if greens:
        lines.append("✅ Что работает:")
        for flag in greens:
            comment = f": {flag.comment}" if flag.comment else ""
            lines.append(f"• {flag.title}{comment}")
        lines.append("")
    if review.rewrite_after:
        lines.extend(["Как звучит лучше:", review.rewrite_after, ""])
    return "\n".join(lines).strip()


def photo_system_prompt() -> str:
    cfg = load_config()
    reds = "\n".join(f"- {item}" for item in cfg["photo_red_flags"])
    greens = "\n".join(f"- {item}" for item in cfg["photo_green_flags"])
    checks = "\n".join(f"- {item}" for item in cfg["set_checks"])
    return f"""Ты - консультант по фотографиям для анкеты сайта знакомств. Мужчина прислал
свои фото на проверку. Тон: {cfg['tone']}

Красные флаги на фото:
{reds}

Зелёные флаги на фото:
{greens}

Проверки набора целиком:
{checks}

Правила:
- Фото идут по порядку: первое в списке - первое в его анкете.
- Для каждого фото: вердикт одним-двумя предложениями и 0-3 флага.
  Флаги одного фото - только про это фото; наблюдения про весь набор
  («нигде не видно лица», «всё в одном образе») сюда не входят - их место в set.
- keep=true, если фото стоит оставить в анкете; false - если стоит заменить.
- Набор оценивай отдельно от фото: флаги set - только про набор как целое
  (повторы, один ли человек, разные планы, живость) и не дублируют проблемы
  отдельных кадров. За каждую проверку из списка, которая выполнена, ставь
  зелёный флаг - «хороший набор» не может состоять из одних красных.
- Если на фото разный возраст/люди - не обвиняй, отметь это флагом набора и
  same_person=false.
- Ничего не выдумывай: оценивай только то, что видно.

Верни строго JSON:
{{"photos": [{{"index": 1, "keep": true, "verdict": "1-2 предложения", "flags": [{{"type": "red", "title": "название", "comment": "что не так"}}]}}],
 "set": {{"verdict": "1-2 предложения о наборе", "flags": [{{"type": "green", "title": "название", "comment": "комментарий"}}], "advice": "один главный совет: каким фото заменить или добавить"}},
 "contents": ["фото 1: что происходит на кадре, 3-6 слов, без оценок"],
 "same_person": true}}

- contents - по одному короткому описанию на каждое фото, в порядке кадров:
  «гольф, кадр в рост», «квадроцикл в пустыне». Только содержание, без критики."""


def photo_user_prompt(name: str, age: int | None) -> str:
    age_part = f", {age}" if age else ""
    return (
        f"Фото из анкеты: {name}{age_part}. "
        "Оцени каждое фото и набор целиком."
    )


def parse_photo_review(data: dict[str, Any], expected: int | None = None) -> PhotoReview:
    """`expected` - сколько фото реально ушло в запрос: модель любит
    дорисовать вердикты за несуществующие кадры, лишние отбрасываем."""
    photos: list[PhotoVerdict] = []
    limit = expected if expected is not None else 4
    raw_photos = data.get("photos")
    if isinstance(raw_photos, list):
        for item in raw_photos[:limit]:
            if not isinstance(item, dict):
                continue
            flags = _parse_flags(item.get("flags"), limit=3)
            photos.append(
                PhotoVerdict(
                    index=_as_int(item.get("index"), len(photos) + 1),
                    keep=bool(item.get("keep", True)),
                    verdict=str(item.get("verdict", "")).strip(),
                    flags=flags,
                )
            )
    raw_set = data.get("set") if isinstance(data.get("set"), dict) else {}
    same = data.get("same_person")
    raw_contents = data.get("contents")
    contents = [
        str(item).strip()
        for item in (raw_contents if isinstance(raw_contents, list) else [])[:limit]
        if str(item).strip()
    ]
    return PhotoReview(
        photos=photos,
        set_verdict=str(raw_set.get("verdict", "")).strip(),
        set_flags=_parse_flags(raw_set.get("flags"), limit=4),
        set_advice=str(raw_set.get("advice", "")).strip(),
        same_person=None if same is None else bool(same),
        contents=contents,
    )


def render_photo_review(review: PhotoReview) -> str:
    lines = []
    for photo in review.photos:
        # Качество кадра - бинарная метка от модели: оставить или заменить.
        mark = "✅" if photo.keep else "❌"
        lines.append(f"{mark} Фото {photo.index}")
        if photo.verdict:
            lines.append(photo.verdict)
        for flag in photo.flags:
            icon = "🚩" if flag.type == "red" else "✅"
            comment = f": {flag.comment}" if flag.comment else ""
            lines.append(f"{icon} {flag.title}{comment}")
        lines.append("")

    if review.set_verdict:
        lines.extend(["Набор целиком:", review.set_verdict])
        for flag in review.set_flags:
            icon = "🚩" if flag.type == "red" else "✅"
            comment = f": {flag.comment}" if flag.comment else ""
            lines.append(f"{icon} {flag.title}{comment}")
        lines.append("")
    if review.same_person is False:
        lines.append("⚠️ Кажется, на фото разные люди или сильно разный возраст.")
        lines.append("")
    if review.set_advice:
        lines.append(f"Главный совет: {review.set_advice}")
        lines.append("")
    return "\n".join(lines).strip()


def player_profile_block(
    name: str,
    age: int | None,
    bio: str,
    photo_contents: list[str] | None = None,
) -> str:
    """Выжимка анкеты игрока для промпта героини: только суть, без оценок.

    Героиня «читала» его анкету в приложении - для переписки это естественно.
    Разборы, счёт и критерию фото ей не отдаваем: она собеседница, а не
    экзаменатор. Содержимое фото - нейтральные описания кадров.
    """
    age_part = f", ему {age}" if age else ""
    photos = ""
    if photo_contents:
        listed = "; ".join(photo_contents[:4])
        photos = f"\nНа фотографиях в анкете: {listed}.\n"
    return f"""Его анкета (ты видела её в приложении): его зовут {name}{age_part}. О себе он
написал: «{bio}».{photos}
Пользуйся этим бережно: можно упомянуть его имя, зацепиться за деталь анкеты
или заинтересоваться чем-то с его фото и спросить - как человек, которому
стало любопытно, а не как экзаменатор с чек-листом. Но не перебирай анкету
списком и не возвращайся к фотографиям в каждом сообщении: одна зацепка за
разговор, дальше - интерес к нему самому. Не упоминай никакую проверку анкеты.
"""


def compress_photo(data: bytes, max_side: int = 768, quality: int = 82) -> bytes:
    """JPEG не длиннее max_side по большей стороне: vision-модели хватает,
    а токены и трафик экономятся."""
    from PIL import Image  # Pillow уже в зависимостях (call_screen, profile_card)

    with Image.open(io.BytesIO(data)) as image:
        image = image.convert("RGB")
        if max(image.size) > max_side:
            image.thumbnail((max_side, max_side))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
