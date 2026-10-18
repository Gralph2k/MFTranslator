"""Внутреннее состояние персонажа: настроение и три шкалы."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCALES = ("trust", "openness", "energy")
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
        return cls(
            mood=str(data.get("mood", base.mood)),
            trust=_clamp(data.get("trust"), base.trust),
            openness=_clamp(data.get("openness"), base.openness),
            energy=_clamp(data.get("energy"), base.energy),
            notes=[str(n) for n in data.get("notes", []) if str(n).strip()][-MAX_NOTES:],
        )

    def apply(self, delta: dict[str, Any]) -> None:
        """Применяет изменение состояния от модели.

        Неизвестные ключи игнорируются: модель не должна ломать сессию опечаткой.
        Заметки только добавляются, чтобы персонаж не забывал, что уже было.
        """
        if not isinstance(delta, dict):
            return
        if isinstance(delta.get("mood"), str) and delta["mood"].strip():
            self.mood = delta["mood"].strip()
        for scale in SCALES:
            if scale in delta:
                setattr(self, scale, _clamp(delta[scale], getattr(self, scale)))
        new_notes = delta.get("notes")
        if isinstance(new_notes, list):
            for note in new_notes:
                text = str(note).strip()
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
