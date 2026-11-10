"""Клавиатуры меню: героини, их сценарии и что делать после разбора."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .heroines import heroine_for, heroines, next_scenario_id
from .scenario import ScenarioError, load_scenario


def scenario_title(scenario_id: str) -> str:
    try:
        return load_scenario(scenario_id).title
    except ScenarioError:
        return scenario_id


def heroines_menu() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=heroine.menu_title, callback_data=f"menu:heroine:{heroine.id}"
            )
        ]
        for heroine in heroines()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def heroines_pick() -> InlineKeyboardMarkup:
    """Одна кнопка «Выбрать героиню»: после разбора и после случайного старта."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Выбрать героиню", callback_data="menu:list")]
        ]
    )


def heroine_menu(heroine_id: str) -> InlineKeyboardMarkup:
    """Сценарии выбранной героини по порядку истории."""
    heroine = next((item for item in heroines() if item.id == heroine_id), None)
    if heroine is None:
        return heroines_menu()

    rows = [
        [
            InlineKeyboardButton(
                text=scenario_title(scenario_id),
                callback_data=f"menu:start:{scenario_id}",
            )
        ]
        for scenario_id in heroine.scenarios
    ]
    rows.append(
        [InlineKeyboardButton(text="Назад к героиням", callback_data="menu:list")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_finish_menu(current: str) -> InlineKeyboardMarkup:
    """После разбора: продолжить историю или выбрать другую героиню."""
    following = next_scenario_id(current)
    rows: list[list[InlineKeyboardButton]] = []
    if following:
        next_heroine = heroine_for(following)
        title = scenario_title(following)
        label = (
            f"Продолжить: {next_heroine.name} — {title}"
            if next_heroine is not None
            else f"Продолжить: {title}"
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=label, callback_data=f"menu:start:{following}"
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="Выбрать героиню", callback_data="menu:list")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
