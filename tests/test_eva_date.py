"""Сценарий «Первое свидание» Евы: вживую, винный бар с живой музыкой.

Свидание Евы — не копия свидания Веры: она не «вежливая и настороженная»,
а быстрая и ироничная, и трудность не в анкете, а в равенстве — счёт, темп
и место, где можно не быть железной.
"""

from bot.prompts import persona_system_prompt
from bot.scenario import load_scenario
from bot.state import PersonaState


def _scenario():
    return load_scenario("eva_date")


def test_date_is_in_person_and_standalone():
    scenario = _scenario()

    assert scenario.medium == "in_person"
    assert scenario.shows_face
    assert scenario.profile is None
    assert scenario.continues == ""
    assert scenario.heroine == "eva"
    assert scenario.enabled is True
    assert scenario.faces_dir.is_dir()
    assert scenario.turn_limit == 10
    assert scenario.max_score == 12


def test_the_bill_is_about_equality_not_money():
    secrets = " ".join(_scenario().secrets).lower()
    hurts = " ".join(_scenario().hurts).lower()

    assert "пополам" in secrets
    assert "калькулятор" in secrets
    assert "мужчина" in hurts
    # Вера о счетах не думает — это проверка именно Евы.
    assert "равенств" in hurts


def test_slowing_her_down_is_the_deepest_trap():
    hurts = " ".join(_scenario().hurts).lower()
    secrets = " ".join(_scenario().secrets).lower()

    assert "поспокойнее" in secrets
    assert "мотоцикл" in hurts and "опасно" in hurts
    assert "выглядишь уставшей" in hurts


def test_wrap_up_is_her_own():
    reasons = " ".join(_scenario().wrap_up_reasons).lower()

    assert "мотоцикл" in reasons or "промилле" in reasons
    assert _scenario().wrap_up_at == 3


def test_rubric_is_about_moves_not_personality():
    ids = [item.id for item in _scenario().rubric]

    assert ids == [
        "game",
        "her_week",
        "equal_bill",
        "no_slowdown",
        "saw_her",
        "shared_pace",
    ]


def test_prompt_frame_is_the_wine_bar():
    scenario = _scenario()
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)

    assert "Ева" in prompt
    assert "винный бар" in prompt
    assert "Вера" not in prompt
    # speech_extra канала вживую подмешан к голосу героини.
    assert "Вживую Ева живее" in prompt


def test_demo_replies_are_voiced_for_the_date():
    replies = _scenario().demo_replies
    joined = " ".join(replies).lower()

    assert len(replies) >= 3
    assert "пополам" in joined
    assert any(word in joined for word in ("дедлайн", "заказ", "кадр"))
    for vera_detail in ("сальса", "издательств", "караоке"):
        assert vera_detail not in joined
