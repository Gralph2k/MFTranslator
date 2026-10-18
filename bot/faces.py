"""Выбор иллюстрации по состоянию персонажа.

Картинки — данные: лежат в images/ с именами вроде anya_calm.jpg.
Если файла нет, бот просто не отправляет фото и работает дальше.
"""

from __future__ import annotations

from pathlib import Path

from .state import PersonaState

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FACES_DIR = ROOT / "images"

EMOTIONS: tuple[str, ...] = (
    "calm",
    "tired",
    "irritated",
    "hurt",
    "closed",
    "warming",
    "smiling",
    "tears",
)

LABELS: dict[str, str] = {
    "calm": "спокойно",
    "tired": "устала",
    "irritated": "раздражена",
    "hurt": "обижена",
    "closed": "закрылась",
    "warming": "теплеет",
    "smiling": "улыбается",
    "tears": "на глазах слёзы",
}

_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def _has(text: str, *markers: str) -> bool:
    return any(marker in text for marker in markers)


def emotion_for_state(state: PersonaState) -> str:
    """Правила простые и предсказуемые: сначала прямые слова, потом числа.

    Слова важнее шкал: модель пишет настроение текстом, и «обижена» надёжнее,
    чем доверие 0.38.
    """
    mood = state.mood.lower().replace("ё", "е")

    if _has(mood, "слез", "плач", "плак", "рыда", "ревет"):
        return "tears"
    if _has(mood, "улыб", "радост", "смех", "смеет", "весел"):
        return "smiling"
    if _has(mood, "обид", "обиж", "ранен", "задет", "унижен"):
        return "hurt"
    if _has(mood, "тепл"):
        return "warming"
    if _has(mood, "раздраж", "зл", "гнев", "бесит") or state.trust < 0.35:
        return "irritated"

    if state.energy < 0.22:
        return "tired"
    if state.openness < 0.3:
        return "calm"
    if state.openness < 0.45:
        return "closed"
    if state.openness >= 0.65:
        return "warming"
    return "calm"


def face_path(emotion: str, directory: Path | str = DEFAULT_FACES_DIR) -> Path | None:
    """Ищет файл эмоции. Имена — anya_<emotion>.jpg, имя персонажа не важно."""
    directory = Path(directory)
    if not directory.exists():
        return None

    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in _EXTENSIONS:
            continue
        if path.stem == emotion or path.stem.endswith(f"_{emotion}"):
            return path
    return None


def label(emotion: str) -> str:
    return LABELS.get(emotion, emotion)
