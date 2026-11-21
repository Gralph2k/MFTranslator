"""Клавиатуры меню: героини, их сценарии и что делать после разбора."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .heroines import heroine_for, heroines
from .scenario import ScenarioError, load_scenario


def scenario_title(scenario_id: str) -> str:
    try:
        return load_scenario(scenario_id).title
    except ScenarioError:
        return scenario_id


def heroines_menu() -> InlineKeyboardMarkup:
    """Главное меню: «Проверка анкеты» первой строкой, ниже - героини."""
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="Проверка анкеты", callback_data="profile:start")]
    ]
    rows.extend(
        [
            InlineKeyboardButton(
                text=heroine.menu_title, callback_data=f"menu:heroine:{heroine.id}"
            )
        ]
        for heroine in heroines()
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
    """После разбора: следующий сюжет той же героини или главное меню.

    «Знакомство» и «первый звонок» ведут к следующей сцене героини; её
    последняя сцена (например, «Первое свидание») замыкает историю - тогда
    показываем основное меню целиком: анкета плюс выбор героинь.
    """
    heroine = heroine_for(current)
    if heroine is not None and current in heroine.scenarios:
        index = heroine.scenarios.index(current)
        if index + 1 < len(heroine.scenarios):
            following = heroine.scenarios[index + 1]
            return InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=f"Продолжить: {scenario_title(following)}",
                            callback_data=f"menu:start:{following}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="В основное меню", callback_data="menu:main"
                        )
                    ],
                ]
            )
    return heroines_menu()
