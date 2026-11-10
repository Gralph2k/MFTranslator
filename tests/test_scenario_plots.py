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


def test_first_message_is_about_the_app_chat_not_the_meeting():
    """Переписка до свидания: та же Вера, но ещё ни разу не виделись вживую."""
    scenario = load_scenario("first_message")
    text = _text(scenario)

    assert "приложени" in text
    assert "переписыва" in text or "матч" in text
    assert "сальса" in text or "анкет" in text
    assert "клава" not in text
    assert "одноклассниц" not in text
    # Это не свидание: в кафе они ещё не сидели.
    assert "кофейн" not in text


def test_first_call_is_about_the_phone_call_not_the_meeting():
    """Созвон после переписки: уже не переписка, но ещё не свидание."""
    scenario = load_scenario("first_call")
    text = _text(scenario)

    assert "созвон" in text or "телефон" in text
    assert "приложени" in text
    assert "клава" not in text
    assert "одноклассниц" not in text
    # Это не свидание: в кофейне они ещё не сидели вместе.
    assert "кофейне" not in text


def test_eva_message_is_about_her_life_not_vera():
    """Ева — отдельная героиня: фотографии, мотоцикл, поездки; без сюжета Веры."""
    scenario = load_scenario("eva_message")
    text = _text(scenario)

    assert "съёмк" in text or "фотограф" in text
    assert "мотоцикл" in text or "поездк" in text
    for vera_detail in ("сальса", "караоке", "издательств", "метро, книга", "редактор"):
        assert vera_detail not in text, f"в сценарий Евы протёк сюжет Веры: {vera_detail}"
    assert "клава" not in text
    assert "одноклассниц" not in text
    # Это переписка до встречи, а не свидание в кофейне.
    assert "кофейн" not in text or "кафе" in text

