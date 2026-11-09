"""Экран исходящего звонка: рендер, кеш и отсутствие фото."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from PIL import Image

from bot.call_screen import CALL_PHOTO, render_call_screen
from bot.scenario import Scenario, scenario_from_dict

# %TEMP% в этой среде закрыт песочницей, поэтому tmp_path не используем.
ROOT = Path(__file__).resolve().parent.parent
TMP_ROOT = ROOT / ".tmp"
CALL_CACHE = TMP_ROOT / "call_screens"


def _scenario_data(scenario_id: str) -> dict[str, Any]:
    """Минимальный словарь, который loader принимает без opening/frame/contact_hint."""
    return {
        "id": scenario_id,
        "title": "Тестовый звонок",
        "one_liner": "Проверка экрана исходящего звонка",
        "persona": {
            "name": "Вера",
            "age": 34,
            "job": "врач",
            "relation": "жена",
            "traits": ["устала", "прямая"],
            "speech": "короткими фразами",
        },
        "situation": "Вечер, Вера звонит после смены.",
        "secrets": ["Секрет 1", "Секрет 2", "Секрет 3"],
        "initial_state": {"openness": 0.2, "trust": 0.2, "energy": 0.4},
        "turn_limit": 10,
        "levers": {"helps": ["внимание"], "hurts": ["советы"]},
        "rubric": [
            {"id": "empathy", "label": "Эмпатия", "max": 2, "what": "Слышит чувства."},
            {"id": "questions", "label": "Вопросы", "max": 2, "what": "Уточняет."},
            {"id": "support", "label": "Опора", "max": 2, "what": "Не спасает."},
        ],
    }


def _make_scenario(with_photo: bool = True) -> Scenario:
    """Временная папка-сценарий с настоящим маленьким JPEG в images/."""
    folder = TMP_ROOT / f"call-screen-{uuid.uuid4().hex[:8]}"
    images = folder / "images"
    images.mkdir(parents=True)
    if with_photo:
        Image.new("RGB", (160, 120), (72, 96, 128)).save(
            images / CALL_PHOTO, format="JPEG"
        )
    data = _scenario_data(f"call-test-{uuid.uuid4().hex[:8]}")
    return scenario_from_dict(data, directory=folder)


def test_render_returns_jpeg_1024() -> None:
    scenario = _make_scenario()

    path = render_call_screen(scenario)

    assert path is not None
    assert path.is_file()
    with Image.open(path) as image:
        assert image.format == "JPEG"
        assert image.size == (1024, 1024)


def test_second_call_returns_same_path() -> None:
    scenario = _make_scenario()
    first = render_call_screen(scenario)
    assert first is not None
    rendered_at = first.stat().st_mtime_ns

    second = render_call_screen(scenario)

    assert second == first
    assert second is not None and second.is_file()
    # Кеш: готовый экран не перерисовывался.
    assert second.stat().st_mtime_ns == rendered_at


def test_without_photo_returns_none() -> None:
    scenario = _make_scenario(with_photo=False)

    assert render_call_screen(scenario) is None


def test_cache_lives_in_tmp_call_screens() -> None:
    scenario = _make_scenario()

    path = render_call_screen(scenario)

    assert path is not None
    assert CALL_CACHE in path.parents
    assert path.parent == CALL_CACHE / scenario.id
