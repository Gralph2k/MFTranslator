"""Сценарий: персонаж, ситуация, рубрика разбора. Данные, а не код."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCENARIO_DIR = ROOT / "scenarios"


class ScenarioError(ValueError):
    """Сценарий не загрузился или в нём не хватает полей."""


@dataclass(frozen=True)
class Persona:
    name: str
    age: int
    job: str
    relation: str
    traits: list[str]
    speech: str


@dataclass(frozen=True)
class RubricItem:
    id: str
    label: str
    max: int
    what: str


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    language: str
    one_liner: str
    opening: str
    persona: Persona
    situation: str
    secrets: list[str]
    initial_state: dict[str, Any]
    turn_limit: int
    helps: list[str]
    hurts: list[str]
    rubric: list[RubricItem]
    debrief_tone: str

    @property
    def max_score(self) -> int:
        return sum(item.max for item in self.rubric)


def _require(data: dict[str, Any], key: str, kind: type, where: str) -> Any:
    if key not in data:
        raise ScenarioError(f"{where}: нет поля '{key}'")
    value = data[key]
    if not isinstance(value, kind):
        raise ScenarioError(f"{where}: поле '{key}' должно быть {kind.__name__}")
    return value


def scenario_from_dict(data: dict[str, Any]) -> Scenario:
    if not isinstance(data, dict):
        raise ScenarioError("сценарий должен быть объектом JSON")

    persona_raw = _require(data, "persona", dict, "сценарий")
    persona = Persona(
        name=_require(persona_raw, "name", str, "persona"),
        age=_require(persona_raw, "age", int, "persona"),
        job=_require(persona_raw, "job", str, "persona"),
        relation=_require(persona_raw, "relation", str, "persona"),
        traits=list(_require(persona_raw, "traits", list, "persona")),
        speech=_require(persona_raw, "speech", str, "persona"),
    )

    levers = _require(data, "levers", dict, "сценарий")
    rubric_raw = _require(data, "rubric", list, "сценарий")
    if not rubric_raw:
        raise ScenarioError("рубрика пустая: разбор будет бессмысленным")

    rubric = [
        RubricItem(
            id=_require(item, "id", str, "rubric[]"),
            label=_require(item, "label", str, "rubric[]"),
            max=_require(item, "max", int, "rubric[]"),
            what=_require(item, "what", str, "rubric[]"),
        )
        for item in rubric_raw
    ]

    return Scenario(
        id=_require(data, "id", str, "сценарий"),
        title=_require(data, "title", str, "сценарий"),
        language=data.get("language", "ru"),
        one_liner=_require(data, "one_liner", str, "сценарий"),
        opening=_require(data, "opening", str, "сценарий"),
        persona=persona,
        situation=_require(data, "situation", str, "сценарий"),
        secrets=list(_require(data, "secrets", list, "сценарий")),
        initial_state=_require(data, "initial_state", dict, "сценарий"),
        turn_limit=_require(data, "turn_limit", int, "сценарий"),
        helps=list(_require(levers, "helps", list, "levers")),
        hurts=list(_require(levers, "hurts", list, "levers")),
        rubric=rubric,
        debrief_tone=data.get("debrief_tone", "спокойно и по делу"),
    )


def load_scenario(name_or_path: str | Path = "friday_evening") -> Scenario:
    """Загружает сценарий по имени (без .json) или по пути к файлу."""
    path = Path(name_or_path)
    if not path.exists():
        path = SCENARIO_DIR / f"{path.name}.json"
    if not path.exists():
        raise ScenarioError(f"сценарий не найден: {name_or_path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"{path.name}: битый JSON — {exc}") from exc

    return scenario_from_dict(data)


def available_scenarios() -> list[str]:
    return sorted(p.stem for p in SCENARIO_DIR.glob("*.json"))
