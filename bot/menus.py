"""Клавиатуры меню: выбор сценария и что делать после разбора."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .scenario import available_scenarios, load_scenario


def scenario_titles() -> dict[str, str]:
    """id → название. Читается с диска один раз за процесс."""
    return {name: load_scenario(name).title for name in available_scenarios()}


def scenario_title(scenario_id: str) -> str:
    return scenario_titles().get(scenario_id, scenario_id)


def next_scenario_id(current: str) -> str:
    """Следующий по порядку; после последнего — снова первый."""
    ids = list(scenario_titles())
    if current not in ids:
        return ids[0]
    return ids[(ids.index(current) + 1) % len(ids)]


def scenarios_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"menu:start:{scenario_id}")]
        for scenario_id, title in scenario_titles().items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_finish_menu(current: str) -> InlineKeyboardMarkup:
    """После разбора: повторить, перейти к следующему или выбрать любой."""
    following = next_scenario_id(current)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Пройти заново", callback_data=f"menu:start:{current}"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Далее: {scenario_title(following)}",
                    callback_data=f"menu:start:{following}",
                )
            ],
            [InlineKeyboardButton(text="Выбрать сценарий", callback_data="menu:list")],
        ]
    )
