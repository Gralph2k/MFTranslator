"""Меню героинь: две ступени, «Продолжить» и никаких выключенных сценариев."""

from bot.heroines import heroines
from bot.menus import (
    after_finish_menu,
    heroine_menu,
    heroines_menu,
    scenario_title,
)


def _callbacks(markup) -> list[str]:
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def _texts(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def test_heroines_menu_lists_only_active_heroines():
    markup = heroines_menu()

    # «Проверка анкеты» - первая кнопка главного меню, ниже - героини.
    assert _callbacks(markup) == [
        "profile:start",
        "menu:heroine:vera",
        "menu:heroine:eva",
    ]
    texts = _texts(markup)
    assert texts[0] == "Проверка анкеты"
    assert texts[1].startswith("Вера, 30")
    assert texts[2].startswith("Ева, 26")


def test_heroines_menu_without_check_for_bridge():
    """Мостик после проверки анкеты - то же главное меню: анкета плюс героини."""
    assert _callbacks(heroines_menu()) == [
        "profile:start",
        "menu:heroine:vera",
        "menu:heroine:eva",
    ]


def test_heroine_menu_lists_scenarios_in_story_order():
    markup = heroine_menu("vera")

    assert _callbacks(markup) == [
        "menu:start:first_message/vera",
        "menu:start:first_call/vera",
        "menu:start:first_date/vera",
        "menu:list",
    ]


def test_eva_menu_lists_scenarios_in_story_order():
    assert _callbacks(heroine_menu("eva")) == [
        "menu:start:first_message/eva",
        "menu:start:first_call/eva",
        "menu:start:first_date/eva",
        "menu:list",
    ]


def test_disabled_scenarios_are_not_in_any_menu():
    callbacks = _callbacks(heroines_menu()) + _callbacks(heroine_menu("vera"))
    assert "menu:start:friday_evening/anya" not in callbacks
    assert "menu:start:reunion_call/ira" not in callbacks


def test_unknown_heroine_falls_back_to_the_list():
    assert _callbacks(heroine_menu("нет-такой")) == _callbacks(heroines_menu())


def test_after_finish_continues_vera_chain():
    markup = after_finish_menu("first_message/vera")
    callbacks = _callbacks(markup)

    assert callbacks == ["menu:start:first_call/vera", "menu:main"]
    assert _texts(markup) == [
        f"Продолжить: {scenario_title('first_call/vera')}",
        "В основное меню",
    ]


def test_after_vera_call_leads_to_date():
    assert _callbacks(after_finish_menu("first_call/vera")) == [
        "menu:start:first_date/vera",
        "menu:main",
    ]


def test_after_date_shows_main_menu():
    """«Первое свидание» - последняя сцена героини: дальше основное меню."""
    main_menu = _callbacks(heroines_menu())
    assert _callbacks(after_finish_menu("first_date/vera")) == main_menu
    assert _callbacks(after_finish_menu("first_date/eva")) == main_menu


def test_after_eva_chat_continues_eva_chain():
    markup = after_finish_menu("first_message/eva")
    callbacks = _callbacks(markup)

    assert callbacks[0] == "menu:start:first_call/eva"
    assert _texts(markup)[0] == "Продолжить: Первый созвон"


def test_scenario_title_is_readable():
    assert scenario_title("first_message/vera") == "Первое сообщение"
    assert len(heroines()) == 2
