"""Сценарий Евы: её собственная переписка, а не копия Веры."""

from bot.faces import EMOTIONS
from bot.heroines import load_heroine
from bot.prompts import persona_system_prompt
from bot.scenario import load_scenario
from bot.state import PersonaState


def _scenario():
    return load_scenario("eva_message")


def test_eva_is_a_chat_heroine():
    scenario = _scenario()

    assert scenario.heroine == "eva"
    assert scenario.medium == "chat"
    assert scenario.is_correspondence
    assert not scenario.shows_face
    assert scenario.opening == "", "переписку начинает игрок"
    assert scenario.enabled is True


def test_eva_personality_lives_in_the_heroine_file():
    scenario = _scenario()
    heroine = load_heroine("eva")

    assert scenario.persona.name == "Ева"
    assert scenario.persona.age == 26
    assert "фотограф" in scenario.persona.job
    assert scenario.profile == heroine.profile
    assert len(scenario.profile.photos) == 4
    assert set(scenario.profile.captions) == set(scenario.profile.photos)


def test_eva_has_her_own_voice():
    speech = _scenario().persona.speech

    assert len(speech) >= 80
    assert "«" in speech
    for vera_detail in ("сальса", "караоке", "издательств", "милая"):
        assert vera_detail not in speech.lower()


def test_eva_prompt_is_about_eva_not_vera():
    scenario = _scenario()
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)

    assert "Ева" in prompt
    assert "Вера" not in prompt
    assert "сальса" not in prompt.lower()
    assert "метро, книга" not in prompt
    assert "подписи «Ева»" in prompt


def test_eva_does_not_name_the_day_herself():
    """Общее правило переписки: день и время называет он, она подтверждает."""
    hint = _scenario().contact_hint.lower()

    assert "день и время" in hint
    assert "не назначает" in hint


def test_eva_rubric_and_red_flags():
    scenario = _scenario()

    assert [item.id for item in scenario.rubric] == [
        "hook",
        "honest",
        "need",
        "no_devalued",
        "no_sponsor",
        "pace",
    ]
    assert scenario.max_score == 12
    flags = " ".join(scenario.red_flags).lower()
    assert "агресс" in flags
    assert "нажим" in flags
    assert "унижение" in flags or "обесцен" in flags


def test_eva_traps_explain_why_they_seem_reasonable():
    hurts = _scenario().hurts

    assert len(hurts) >= 5
    for hurt in hurts:
        assert "—" in hurt and len(hurt) > 60
    joined = " ".join(hurts).lower()
    assert "спонсор" in joined
    assert "статус" in joined or "цифрами" in joined
    assert "поспокойнее" in joined or "темп" in joined


def test_eva_profile_photos_do_not_collide_with_emotions():
    for photo in _scenario().profile.photos:
        assert photo.split(".")[0] not in EMOTIONS


def test_eva_starts_closed():
    state = _scenario().initial_state

    assert state["openness"] <= 0.25
    assert 8 <= _scenario().turn_limit <= 12


def test_eva_demo_replies_are_in_her_voice():
    replies = _scenario().demo_replies

    assert len(replies) >= 3
    joined = " ".join(replies).lower()
    assert "сальса" not in joined
    assert "издательств" not in joined
    assert any(word in joined for word in ("мотоцикл", "съёмк", "кадр"))
