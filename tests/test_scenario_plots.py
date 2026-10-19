"""Сюжеты сценариев не должны протекать друг в друга.

История: в «Пятничный вечер» однажды попал звонок Клавы из «Вечера встречи».
Пользователь видел в предыстории чужой сюжет, а персонаж — чужие секреты.
"""

from bot.scenario import load_scenario


def _text(scenario) -> str:
    return " ".join(
        [
            scenario.one_liner,
            scenario.backstory,
            scenario.situation,
            scenario.frame,
            *scenario.secrets,
        ]
    ).lower()


def test_friday_evening_is_about_work_not_reunion():
    scenario = load_scenario("friday_evening")
    text = _text(scenario)

    assert "клава" not in text
    assert "выпускник" not in text
    assert "одноклассниц" not in text
    assert "руководител" in text


def test_reunion_call_is_about_the_call_not_the_office():
    scenario = load_scenario("reunion_call")
    text = _text(scenario)

    assert "клава" in text
    assert "руководител" not in text
    assert "защит" not in text


def test_first_date_is_about_a_first_meeting_not_a_long_relationship():
    scenario = load_scenario("first_date")
    text = _text(scenario)

    assert "приложени" in text
    assert "караоке" in text
    assert "клава" not in text
    assert "одноклассниц" not in text
