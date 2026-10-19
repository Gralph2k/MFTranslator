from bot.menus import (
    after_finish_menu,
    next_scenario_id,
    scenario_pick,
    scenario_title,
    scenario_titles,
    scenarios_menu,
)


def _callbacks(markup) -> list[str]:
    return [button.callback_data for row in markup.inline_keyboard for button in row]


def test_titles_cover_every_scenario():
    titles = scenario_titles()
    assert "friday_evening" in titles
    assert "reunion_call" in titles
    assert scenario_title("friday_evening") == "Пятничный вечер"


def test_next_scenario_wraps_around():
    ids = list(scenario_titles())
    assert next_scenario_id(ids[0]) == ids[1]
    assert next_scenario_id(ids[-1]) == ids[0]
    assert next_scenario_id("нет-такого") == ids[0]


def test_after_finish_offers_replay_and_next():
    callbacks = _callbacks(after_finish_menu("friday_evening"))

    assert "menu:start:friday_evening" in callbacks
    assert "menu:start:reunion_call" in callbacks
    assert "menu:list" in callbacks


def test_scenarios_menu_lists_all_scenarios():
    callbacks = _callbacks(scenarios_menu())
    assert len(callbacks) == len(scenario_titles())
    assert all(data.startswith("menu:start:") for data in callbacks)


def test_first_date_goes_first_in_the_menu():
    """`order` в сценарии задаёт место в списке: первое свидание — первым."""
    assert list(scenario_titles())[0] == "first_date"


def test_pick_button_opens_the_list():
    markup = scenario_pick()
    assert _callbacks(markup) == ["menu:list"]
    assert markup.inline_keyboard[0][0].text == "Выбор сценария"
