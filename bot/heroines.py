"""Героини: одна личность на все сценарии.

Героиня — это и есть человек: имя, возраст, профессия, характер, голос и анкета.
Она живёт один раз в `heroines/<slug>/heroine.json`, а сценарии ссылаются на неё
полем `heroine`. Так Вера в переписке, на созвоне и на свидании остаётся одной и
той же, а не тремя похожими женщинами.

Модуль же отвечает за каталог: порядок героинь в меню, порядок сцен внутри
героини, случайный выбор на старте и «продолжить» после разбора.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .scenario import (
    ROOT,
    Profile,
    ScenarioError,
    available_scenarios,
    load_scenario,
    profile_from_dict,
)

HEROINES_DIR = ROOT / "heroines"
HEROINE_FILE = "heroine.json"


@dataclass(frozen=True)
class HeroineData:
    """Содержимое `heroine.json`: личность без привязки к сцене."""

    id: str
    name: str
    age: int
    job: str
    traits: list[str]
    speech: str
    order: int = 100
    profile: Profile | None = None


@dataclass(frozen=True)
class Heroine:
    """Героиня в каталоге: личность плюс её сценарии по порядку."""

    id: str
    name: str
    age: int
    job: str
    order: int
    scenarios: tuple[str, ...]

    @property
    def first_scenario(self) -> str:
        return self.scenarios[0]

    @property
    def menu_title(self) -> str:
        """Подпись кнопки: «Вера, 30 — редактор в небольшом издательстве»."""
        return f"{self.name}, {self.age} — {self.job}"


def load_heroine(slug: str) -> HeroineData:
    """Читает и проверяет `heroines/<slug>/heroine.json`."""
    slug = str(slug or "").strip()
    if not slug:
        raise ScenarioError("героиня: пустой id")
    path = HEROINES_DIR / slug / HEROINE_FILE
    if not path.is_file():
        raise ScenarioError(f"героиня не найдена: {slug} ({path})")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioError(f"{path}: битый JSON — {exc}") from exc
    if not isinstance(data, dict):
        raise ScenarioError(f"{path}: ожидался объект JSON")

    for field in ("id", "name", "job", "speech"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ScenarioError(f"{path}: поле '{field}' должно быть непустой строкой")
    if data["id"].strip() != slug:
        raise ScenarioError(f"{path}: id '{data['id']}' не совпадает с папкой '{slug}'")
    if not isinstance(data.get("age"), int):
        raise ScenarioError(f"{path}: поле 'age' должно быть числом")
    if not isinstance(data.get("traits"), list) or not data["traits"]:
        raise ScenarioError(f"{path}: поле 'traits' должно быть непустым списком")

    profile = None
    if data.get("profile") is not None:
        profile = profile_from_dict(data["profile"])

    return HeroineData(
        id=slug,
        name=data["name"].strip(),
        age=int(data["age"]),
        job=data["job"].strip(),
        traits=[str(item).strip() for item in data["traits"] if str(item).strip()],
        speech=data["speech"].strip(),
        order=_as_int(data.get("order"), 100),
        profile=profile,
    )


def heroines() -> list[Heroine]:
    """Героини, у которых есть хотя бы один включённый сценарий.

    Порядок — по `order` из `heroine.json`, сцены внутри — по `order` сценария.
    """
    by_slug: dict[str, list[Any]] = {}
    for scenario_id in available_scenarios():
        scenario = load_scenario(scenario_id)
        if not scenario.heroine:
            raise ScenarioError(
                f"сценарий '{scenario.id}' включён, но не ссылается на героиню"
            )
        by_slug.setdefault(scenario.heroine, []).append(scenario)

    catalog: list[Heroine] = []
    for slug, scenarios in by_slug.items():
        data = load_heroine(slug)
        ordered = sorted(scenarios, key=lambda item: (item.order, item.id))
        catalog.append(
            Heroine(
                id=slug,
                name=data.name,
                age=data.age,
                job=data.job,
                order=data.order,
                scenarios=tuple(item.id for item in ordered),
            )
        )
    return sorted(catalog, key=lambda heroine: (heroine.order, heroine.id))


def heroine_for(scenario_id: str) -> Heroine | None:
    """Героиня, которой принадлежит сценарий; None — если такого нет."""
    for heroine in heroines():
        if scenario_id in heroine.scenarios:
            return heroine
    return None


def story_scenarios() -> list[str]:
    """Все включённые сценарии в порядке истории: героиня за героиней."""
    return [scenario for heroine in heroines() for scenario in heroine.scenarios]


def next_scenario_id(current: str) -> str:
    """Следующий сценарий истории; после последнего — снова первый.

    Внутри героини идём по порядку сцен, после её последней — к следующей
    героине. Неизвестный id трактуется как «начнём сначала».
    """
    ids = story_scenarios()
    if not ids:
        return ""
    if current not in ids:
        return ids[0]
    return ids[(ids.index(current) + 1) % len(ids)]


def random_heroine(
    last: str | None = None,
    rng: random.Random | None = None,
) -> Heroine:
    """Случайная героиня для `/start`, по возможности не та же, что в прошлый раз."""
    catalog = heroines()
    if not catalog:
        raise ScenarioError("нет ни одной включённой героини")
    candidates = [heroine for heroine in catalog if heroine.id != last] or catalog
    picker = rng or random
    return picker.choice(candidates)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
