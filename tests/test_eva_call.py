"""Сценарий «Первый созвон» Евы: голосом, после её переписки.

Ева — не копия Веры: её проверка на созвоне — не «услышит ли он моё „посмотрим“»,
а «придётся ли снова тащить всё одной». Проверяем, что сцена осталась её.
"""

from bot.scenario import load_scenario


def _scenario():
    return load_scenario("first_call/eva")


def test_call_continues_eva_chat():
    scenario = _scenario()

    assert scenario.is_call
    assert scenario.shows_face is False
    assert scenario.profile is None
    assert scenario.continues == "first_message/eva"
    assert scenario.heroine == "eva"
    assert scenario.enabled is True
    assert (scenario.faces_dir / "call.jpg").is_file()
    assert scenario.turn_limit == 10
    assert scenario.max_score == 12


def test_canon_chat_is_in_evas_voice():
    canon = _scenario().canon_history
    joined = " ".join(item["content"] for item in canon).lower()

    assert all(item["role"] in {"user", "assistant"} for item in canon)
    # Ева просит предложить место встречи — мостик к свиданию.
    assert "куда пойдём" in joined
    # Её мир: съёмка, поездка, кадры; никаких деталей Веры.
    assert any(word in joined for word in ("кадр", "поездк", "крыш"))
    for vera_detail in ("сальса", "издательств", "караоке"):
        assert vera_detail not in joined


def test_her_fear_is_named_in_secrets():
    secrets = " ".join(_scenario().secrets).lower()

    assert "тащить" in secrets
    assert "планы" in secrets
    # Пассивный «куда скажешь» для неё — ловушка, а не уважение.
    hurts = " ".join(_scenario().hurts).lower()
    assert "куда ты хочешь" in hurts or "куда скажешь" in hurts
    assert "пассажир" in hurts


def test_opening_counts_minutes_like_eva():
    opening = _scenario().opening

    assert "восемь" in opening.lower()
    assert "опазд" in opening.lower()


def test_rubric_rewards_concrete_and_equality():
    ids = [item.id for item in _scenario().rubric]

    assert ids == [
        "pace",
        "her_load",
        "concrete",
        "her_world",
        "her_plans",
        "honesty",
    ]


def test_demo_replies_are_voiced_for_the_call():
    replies = _scenario().demo_replies

    assert len(replies) >= 3
    joined = " ".join(replies).lower()
    assert any(word in joined for word in ("кадр", "мотоцикл", "железе"))
    for vera_detail in ("сальса", "издательств", "караоке"):
        assert vera_detail not in joined
