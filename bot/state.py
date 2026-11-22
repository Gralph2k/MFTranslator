"""Внутреннее состояние персонажа: настроение и три шкалы."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .guards import MAX_MOOD_LEN, clamp_text, sanitize_note

SCALES = ("trust", "openness", "energy")
# Доверие и открытость растут медленно: один тёплый ход не переписывает историю.
# Числа совпадают с правилами в промпте наблюдателя, но здесь они ещё и зажаты.
MAX_GROWTH = {"trust": 0.1, "openness": 0.15, "energy": 0.05}
MAX_NOTES = 8


def _clamp(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(1.0, number))


@dataclass
class PersonaState:
    """То, что персонаж чувствует прямо сейчас.

    Шкалы держим в 0..1: так модель не улетает в «обожаю» после одной фразы,
    а код может проверить границы.
    """

    mood: str = "спокойно"
    trust: float = 0.5
    openness: float = 0.5
    energy: float = 0.5
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "PersonaState":
        base = cls()
        # Восстановление из базы - тоже точка входа данных в промпты: mood и
        # заметки чистим так же, как при живом ходе (строки, записанные до
        # появления чистки, не должны попадать в промпты как есть).
        raw_notes = data.get("notes", [])
        notes: list[str] = []
        if isinstance(raw_notes, list):
            for note in raw_notes:
                text = sanitize_note(note)
                if text and text not in notes:
                    notes.append(text)
        return cls(
            mood=clamp_text(str(data.get("mood", base.mood)), MAX_MOOD_LEN),
            trust=_clamp(data.get("trust"), base.trust),
            openness=_clamp(data.get("openness"), base.openness),
            energy=_clamp(data.get("energy"), base.energy),
            notes=notes[-MAX_NOTES:],
        )

    def apply(self, delta: dict[str, Any]) -> None:
        """Применяет изменение состояния от модели.

        Неизвестные ключи игнорируются: модель не должна ломать сессию опечаткой.
        Заметки только добавляются, чтобы персонаж не забывал, что уже было.
        """
        if not isinstance(delta, dict):
            return
        if isinstance(delta.get("mood"), str) and delta["mood"].strip():
            # Лимит длины: mood живёт в каждом промпте, а инъекция не должна
            # расширять его в абзац команд.
            self.mood = clamp_text(delta["mood"], MAX_MOOD_LEN)
        for scale in SCALES:
            if scale in delta:
                current = getattr(self, scale)
                value = _clamp(delta[scale], current)
                if value > current:
                    value = min(value, current + MAX_GROWTH[scale])
                setattr(self, scale, value)
        new_notes = delta.get("notes")
        if isinstance(new_notes, list):
            for note in new_notes:
                # Чистка от тегов и маркера конца: заметка уходит в промпты
                # следующих ходов и не должна разносить инъекцию дальше.
                text = sanitize_note(note)
                if text and text not in self.notes:
                    self.notes.append(text)
            self.notes = self.notes[-MAX_NOTES:]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "mood": self.mood,
            "trust": round(self.trust, 3),
            "openness": round(self.openness, 3),
            "energy": round(self.energy, 3),
            "notes": list(self.notes),
        }

    def describe(self) -> str:
        """Текст для промпта: без чисел там, где они только мешают."""
        parts = [
            f"настроение: {self.mood}",
            f"доверие к нему: {_word(self.trust)}",
            f"готовность говорить: {_word(self.openness)}",
            f"силы: {_word(self.energy)}",
        ]
        if self.notes:
            parts.append("что уже было в разговоре: " + "; ".join(self.notes))
        return ". ".join(parts)


def _word(value: float) -> str:
    if value < 0.2:
        return "почти нет"
    if value < 0.4:
        return "низкое"
    if value < 0.6:
        return "среднее"
    if value < 0.8:
        return "высокое"
    return "очень высокое"
