"""Меню героинь: две ступени, «Продолжить» и никаких выключенных сценариев."""

from bot.heroines import heroines
from bot.menus import (
    after_finish_menu,
    heroine_menu,
    heroines_menu,
    heroines_pick,
    scenario_title,
)


def _callbacks(markup) -> list[str]:
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def _texts(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def test_heroines_menu_lists_only_active_heroines():
    markup = heroines_menu()

    assert _callbacks(markup) == ["menu:heroine:vera", "menu:heroine:eva"]
    texts = _texts(markup)
    assert texts[0].startswith("Вера, 30")
    assert texts[1].startswith("Ева, 26")


def test_heroine_menu_lists_scenarios_in_story_order():
    markup = heroine_menu("vera")

    assert _callbacks(markup) == [
        "menu:start:first_message",
        "menu:start:first_call",
        "menu:start:first_date",
        "menu:list",
    ]


def test_eva_menu_lists_scenarios_in_story_order():
    assert _callbacks(heroine_menu("eva")) == [
        "menu:start:eva_message",
        "menu:start:eva_call",
        "menu:start:eva_date",
        "menu:list",
    ]


def test_disabled_scenarios_are_not_in_any_menu():
    callbacks = _callbacks(heroines_menu()) + _callbacks(heroine_menu("vera"))
    assert "menu:start:friday_evening" not in callbacks
    assert "menu:start:reunion_call" not in callbacks


def test_unknown_heroine_falls_back_to_the_list():
    assert _callbacks(heroine_menu("нет-такой")) == _callbacks(heroines_menu())


def test_after_finish_continues_vera_chain():
    markup = after_finish_menu("first_message")
    callbacks = _callbacks(markup)

    assert callbacks[0] == "menu:start:first_call"
    assert "menu:start:first_call" in callbacks
    assert "menu:list" in callbacks
    assert any("Продолжить: Вера" in text for text in _texts(markup))


def test_after_date_moves_to_the_next_heroine():
    markup = after_finish_menu("first_date")
    callbacks = _callbacks(markup)

    assert callbacks[0] == "menu:start:eva_message"
    assert any("Продолжить: Ева" in text for text in _texts(markup))


def test_after_eva_message_continues_eva_chain():
    markup = after_finish_menu("eva_message")
    callbacks = _callbacks(markup)

    assert callbacks[0] == "menu:start:eva_call"
    assert any("Продолжить: Ева" in text for text in _texts(markup))


def test_after_eva_date_returns_to_vera():
    assert _callbacks(after_finish_menu("eva_date"))[0] == "menu:start:first_message"


def test_pick_button_opens_the_heroine_list():
    markup = heroines_pick()

    assert _callbacks(markup) == ["menu:list"]
    assert _texts(markup) == ["Выбрать героиню"]


def test_scenario_title_is_readable():
    assert scenario_title("first_message") == "Первое сообщение"
    assert len(heroines()) == 2
