"""Сценарий «Первое сообщение»: переписка в приложении, первый ход за игроком.

Отдельный файл, потому что здесь проверяется не сцена в комнате, а переписка:
анкета, пустой opening, красные линии и правила «только текст».
"""

import json

import pytest

from bot.engine import DialogueEngine
from bot.llm import FakeLLM
from bot.prompts import (
    backstory_text,
    debrief_messages,
    persona_system_prompt,
    profile_text,
    rules_text,
    state_messages,
)
from bot.scenario import load_scenario
from bot.state import PersonaState


@pytest.fixture
def scenario():
    return load_scenario("first_message")


def test_chat_scenario_has_profile_and_red_flags(scenario):
    assert scenario.is_correspondence
    assert scenario.medium == "chat"
    assert not scenario.shows_face, "лица в переписке не видно"
    assert scenario.profile is not None
    assert len(scenario.profile.photos) == 3
    assert scenario.profile.hobbies or scenario.profile.interests
    assert scenario.red_flags
    assert scenario.opening == ""


def test_in_person_scenario_shows_the_face():
    date = load_scenario("first_date")

    assert date.shows_face
    assert not date.is_correspondence


def test_player_writes_first(scenario):
    """Пустой opening — старт с пустой стенограммы, бот не шлёт свою реплику."""
    engine = DialogueEngine(FakeLLM([]))
    session = engine.start(scenario)

    assert session.history == []
    assert session.turns_left == scenario.turn_limit


def test_rules_for_correspondence_are_text_only(scenario):
    rules = rules_text(scenario)

    # Сначала рамка тренажёра, потом правила и команды — без подсказки на ход.
    assert "тренажёр, а не живая женщина" in rules
    assert "Команды" in rules
    assert "Подсказка" not in rules
    assert "первое сообщение в переписке" in rules
    assert "только текст" in rules
    assert "Протягиваю ей цветок" not in rules


def test_backstory_has_no_trainer_frame_and_no_repetitions(scenario):
    backstory = backstory_text(scenario)

    assert backstory.startswith("Что происходит:")
    assert "тренажёр" not in backstory.lower()
    # Хвост с именем и «переписываешься» для переписки убран: имя в карточке.
    assert "Ты переписываешься" not in backstory
    assert scenario.backstory in backstory
    # Знакомство описано один раз, без второго «матча» и повторов.
    assert "матч" not in backstory.lower()
    assert backstory.count("познакомились") == 1


def test_rules_for_a_meeting_still_allow_actions():
    rules = rules_text(load_scenario("first_date"))

    assert "Протягиваю ей цветок" in rules


def test_profile_card_text_uses_her_material(scenario):
    text = profile_text(scenario)

    assert "Вера" in text
    assert "30" in text
    assert "издательств" in text
    # Сальса и караоке живут на фото, а не в тексте анкеты: иначе игрок
    # отвечает на готовый список и не учится замечать материал.
    assert "сальса" not in text.lower()
    assert "караоке" not in text.lower()


def test_persona_knows_her_life_and_likes(scenario):
    """Факты из характера попадают в промпт: юмор, комплименты, поездки, планы."""
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)

    assert "необидный юмор" in prompt
    assert "ненавязчивые комплименты" in prompt
    assert "партнёра по танцам" in prompt
    assert "замуж не спешит" in prompt
    assert "Детей нет, но хотела бы" in prompt
    assert "Турции" in prompt and "Египте" in prompt
    assert "риф" in prompt


def test_profile_captions_split_the_story(scenario):
    """«О себе» ушло в подписи к фото: работа, интересы, чего ищет."""
    captions = scenario.profile.captions

    assert set(captions) == set(scenario.profile.photos)
    first = captions["profile_1.jpg"].lower()
    assert "издательств" in first and "правлю" in first
    assert "кофе" in captions["profile_2.jpg"].lower()
    assert "разговор" in captions["profile_3.jpg"].lower()
    for text in captions.values():
        assert "сальса" not in text.lower()
        assert "караоке" not in text.lower()


def test_profile_card_images_have_the_app_ui(scenario):
    """Карточка рисуется кодом поверх фото: имена, счётчик, точки, кнопки."""
    from bot.profile_card import render_profile_cards

    cards = render_profile_cards(scenario)

    assert len(cards) == 3
    for card in cards:
        assert card.is_file()
        assert card.stat().st_size > 10_000


def test_persona_prompt_has_correspondence_and_red_lines(scenario):
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)

    assert "переписываетесь" in prompt
    assert "Лица он не видит" in prompt
    # В переписке смайлики — часть речи, но только на яркой эмоции.
    assert "Смайлики — можно" in prompt
    assert "эмоция яркая" in prompt
    assert "смех, радость, смущение" in prompt
    assert "не в каждой реплике" in prompt
    assert "без смайликов" not in prompt
    assert "Что для тебя недопустимо" in prompt
    assert scenario.red_flags[0] in prompt
    assert "заканчиваешь" in prompt
    assert "без нотаций" in prompt


def test_meeting_prompt_keeps_the_no_emoji_rule():
    """Вживую лицо видно: смайлики там не нужны и остаются запрещёнными."""
    date = load_scenario("first_date")
    prompt = persona_system_prompt(date, PersonaState.from_mapping(date.initial_state))

    assert "без смайликов" in prompt


def test_observer_sets_ended_on_red_line(scenario):
    state = PersonaState.from_mapping(scenario.initial_state)
    system = state_messages(scenario, state, [])[0]["content"]

    assert "красные линии" in system.lower()
    assert "ended=true" in system


def test_debrief_knows_red_lines(scenario):
    system = debrief_messages(scenario, [{"role": "user", "content": "Привет"}])[0]["content"]

    assert "недопустимо" in system


async def test_red_line_ends_the_dialogue(scenario):
    llm = FakeLLM(
        [
            "Ладно, пока.",
            json.dumps(
                {"mood": "брезгливо", "trust": 0.0, "openness": 0.0, "ended": True},
                ensure_ascii=False,
            ),
        ]
    )
    engine = DialogueEngine(llm)
    session = engine.start(scenario)

    await engine.reply(session, "Ты чего такая?")

    assert session.ended_by_persona
    assert session.is_over
