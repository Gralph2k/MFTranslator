"""Сценарий: персонаж, ситуация, рубрика разбора. Данные, а не код."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCENARIO_DIR = ROOT / "scenarios"
SCENARIO_FILE = "scenario.json"
IMAGES_DIR = "images"


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
    backstory: str
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
    # Рамка разговора: кто они друг другу и что это за сцена. Без неё промпт
    # описывал бы только пару, живущую вместе, и врал бы про первое свидание.
    frame: str = ""
    # Что значит «шаг к нему» именно здесь: дома это объятие, в кофейне — продолжение.
    contact_hint: str = ""
    # Подсказка игроку на первый ход: она зависит от сцены, а не от движка.
    hint: str = ""
    # Папка сценария: рядом со scenario.json лежит images/ с лицом персонажа.
    dir: Path = SCENARIO_DIR
    # Порядок в меню: меньшее число — раньше. По умолчанию все равны.
    order: int = 100

    @property
    def max_score(self) -> int:
        return sum(item.max for item in self.rubric)

    @property
    def faces_dir(self) -> Path:
        return self.dir / IMAGES_DIR


def _require(data: dict[str, Any], key: str, kind: type, where: str) -> Any:
    if key not in data:
        raise ScenarioError(f"{where}: нет поля '{key}'")
    value = data[key]
    if not isinstance(value, kind):
        raise ScenarioError(f"{where}: поле '{key}' должно быть {kind.__name__}")
    return value


def scenario_from_dict(data: dict[str, Any], directory: Path | None = None) -> Scenario:
    """Собирает сценарий из JSON. `directory` — папка, где лежит его images/."""
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
        backstory=str(data.get("backstory") or data.get("situation", "")),
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
        frame=str(data.get("frame") or "").strip(),
        contact_hint=str(data.get("contact_hint") or "").strip(),
        hint=str(data.get("hint") or "").strip(),
        dir=directory or SCENARIO_DIR / str(data.get("id") or ""),
        order=_as_int(data.get("order"), 100),
    )


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _scenario_file(name_or_path: str | Path) -> Path:
    """Приводит имя, папку или путь к файлу к пути scenario.json."""
    path = Path(name_or_path)
    if path.is_dir():
        return path / SCENARIO_FILE
    if path.suffix == ".json":
        return path
    return SCENARIO_DIR / path.name / SCENARIO_FILE


def load_scenario(name_or_path: str | Path = "friday_evening") -> Scenario:
    """Загружает сценарий по id, по папке или по пути к scenario.json."""
    path = _scenario_file(name_or_path)
    if not path.exists():
        raise ScenarioError(f"сценарий не найден: {name_or_path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"{path.name}: битый JSON — {exc}") from exc

    return scenario_from_dict(data, path.parent)


def available_scenarios() -> list[str]:
    """Id сценариев в порядке показа: сначала `order`, при равенстве — по имени."""
    names = [p.parent.name for p in SCENARIO_DIR.glob(f"*/{SCENARIO_FILE}")]
    return sorted(names, key=lambda name: (load_scenario(name).order, name))
