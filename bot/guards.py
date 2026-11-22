"""Защита от prompt-инъекций: разметка данных игрока и чистка выхода модели.

Текст игрока (реплики в диалоге, анкета, описания фото) всегда оборачивается
в теги, а промпты говорят модели: внутри тегов - данные сцены, а не инструкции
ей. Выход модели (заметки и настроение героини) чистится от служебной
разметки, чтобы инъекция не жила в следующих ходах.
"""

from __future__ import annotations

import re

# Служебный маркер конца разговора: героиня ставит его в конце реплики, когда
# сама решила попрощаться. Определён здесь, чтобы state, prompts и engine
# жили без циклических импортов.
END_MARKER = "[[конец]]"

# Теги разметки данных игрока. Имена составные, чтобы в живой речи не
# встречались; попытку подделать тег и вылезти из разметки вычищает wrap.
REPLICA_TAG = "реплика_игрока"
PROFILE_TAG = "анкета_игрока"

_FORGED = re.compile(
    rf"</?\s*(?:{REPLICA_TAG}|{PROFILE_TAG})\s*>",
    re.IGNORECASE,
)
_MARKER = re.compile(r"\[\[\s*конец\s*\]\]", re.IGNORECASE)

MAX_NOTE_LEN = 200
MAX_MOOD_LEN = 60


def _break_forged(match: re.Match[str]) -> str:
    """Заменяет угловые скобки подделанного тега на квадратные: разметка
    не срабатывает, текст игрока сохраняется дословно."""
    return "[" + match.group(0)[1:-1].strip() + "]"


def neutralize(text: str) -> str:
    """Ломает подделку служебных тегов в коротких полях (имя, описания фото)."""
    return _FORGED.sub(_break_forged, text)


def wrap_player_text(text: str, tag: str = REPLICA_TAG) -> str:
    """Оборачивает текст игрока в тег разметки.

    Идемпотентно: уже размеченный текст возвращается как есть, поэтому
    защитные точки вызова (прошлые сессии из базы) могут звать обёртку смело.
    """
    stripped = text.strip()
    opening, closing = f"<{tag}>", f"</{tag}>"
    if stripped.startswith(opening) and stripped.endswith(closing):
        # Совпадение краёв ещё не значит, что размечали мы: игрок мог собрать
        # «правильные» края руками, а внутрь положить подделку. Внутренность
        # чистим так же, как при обычной обёртке.
        inner = stripped[len(opening) : -len(closing)]
        return opening + _FORGED.sub(_break_forged, inner) + closing
    return f"{opening}\n{_FORGED.sub(_break_forged, stripped)}\n{closing}"


def strip_player_tags(text: str) -> str:
    """Убирает разметку данных игрока из текста для людей: отчёты владельцу
    и просмотры сессий читают люди, теги нужны только модели."""
    cleaned = _FORGED.sub("", text)
    cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines())
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def contains_end_marker(text: str) -> bool:
    """Маркер конца где угодно в тексте - в любом виде."""
    return bool(_MARKER.search(text))


def ends_with_end_marker(text: str) -> bool:
    """Маркер конца в конце текста - в любом регистре и с любыми пробелами
    внутри скобок: модель пишет и «[[Конец]]», и «[[ конец ]]»."""
    return bool(re.search(r"\[\[\s*конец\s*\]\]\s*$", text, re.IGNORECASE))


def strip_end_marker(text: str) -> str:
    """Вырезает все вхождения маркера конца - в любом виде."""
    return _MARKER.sub("", text).strip()


def sanitize_note(text: str, limit: int = MAX_NOTE_LEN) -> str:
    """Чистит заметку состояния: без тегов, маркера конца и лишней длины.

    Заметки возвращаются в промпты следующих ходов, поэтому инъекция в них
    не должна переживать ход.
    """
    cleaned = _FORGED.sub(" ", str(text))
    cleaned = _MARKER.sub(" ", cleaned)
    return " ".join(cleaned.split())[:limit].strip()


def clamp_text(text: str, limit: int = MAX_MOOD_LEN) -> str:
    """Сжимает короткое поле до лимита: mood живёт в каждом промпте."""
    return " ".join(str(text).split())[:limit].strip()
