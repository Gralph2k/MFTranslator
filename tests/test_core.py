import json

import pytest

from bot.engine import DialogueEngine
from bot.llm import FakeLLM, LLMError, parse_json_object
from bot.prompts import (
    backstory_text,
    debrief_messages,
    persona_system_prompt,
    rules_text,
    state_guidance,
    state_messages,
)
from bot.scenario import available_scenarios, load_scenario
from bot.state import PersonaState


@pytest.fixture
def scenario():
    return load_scenario("friday_evening")


def test_scenario_loads_and_is_complete(scenario):
    assert scenario.id == "friday_evening"
    assert "friday_evening" in available_scenarios()
    assert len(scenario.rubric) == 6
    assert scenario.max_score == 12
    assert scenario.persona.name == "Аня"
    assert scenario.initial_state["trust"] == 0.55
    assert scenario.secrets and scenario.helps and scenario.hurts


def test_unknown_scenario_reports_clearly():
    with pytest.raises(ValueError):
        load_scenario("нет_такого")


def test_scenario_loads_by_id_folder_or_file():
    """Сценарий — папка, но старый способ «по id» должен работать."""
    from bot.scenario import SCENARIO_DIR

    by_id = load_scenario("first_date")
    by_folder = load_scenario(SCENARIO_DIR / "first_date")
    by_file = load_scenario(SCENARIO_DIR / "first_date" / "scenario.json")

    assert by_id.id == by_folder.id == by_file.id == "first_date"
    assert by_folder.dir == by_file.dir == SCENARIO_DIR / "first_date"
    assert by_id.faces_dir == SCENARIO_DIR / "first_date" / "images"


def test_backstory_is_separate_from_rules(scenario):
    backstory = backstory_text(scenario)
    rules = rules_text(scenario)

    assert "тренажёр" in backstory.lower()
    assert scenario.title in backstory
    assert scenario.backstory in backstory

    assert "Как играть" in rules
    # Команда /state убрана из бота: нечего и подсказывать.
    assert "/state" not in rules
    assert scenario.backstory not in rules, "правила не должны пересказывать предысторию"


def test_persona_prompt_contains_hidden_material(scenario):
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)
    assert scenario.persona.name in prompt
    assert scenario.secrets[0] in prompt
    assert "JSON" in prompt


def test_persona_prompt_teaches_a_living_voice(scenario):
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)

    # Голос из данных сценария попадает в промпт: сухой speech снова сделает её холодной.
    assert scenario.persona.speech in prompt
    assert "Как звучит живая женщина" in prompt
    assert "Так звучит сухо" in prompt
    # «Отвечай суше» было прямой инструкцией на автоответчик.
    assert "суше" not in prompt.lower()
    # Регрессии, пойманные на реальных сессиях: не принимать починку,
    # писать ремарки от третьего лица и засыпать вопросами.
    assert "Броня не становится стеной" in prompt
    assert "только свою речь" in prompt
    assert "одного вопроса" in prompt


def test_state_prompt_asks_for_a_live_mood(scenario):
    state = PersonaState.from_mapping(scenario.initial_state)
    system = state_messages(scenario, state, [])[0]["content"]

    assert "наблюдатель" in system
    assert "живое описание" in system
    assert "trust растёт не больше чем на 0.1" in system
    assert "Числа до этой реплики" in system


def test_state_guidance_changes_contact_initiative():
    closed = PersonaState(trust=0.3, openness=0.1, energy=0.2)
    open_ = PersonaState(trust=0.8, openness=0.9, energy=0.7)

    closed_text = state_guidance(closed)
    open_text = state_guidance(open_)

    assert "ты почти закрыта" in closed_text
    assert "не предлагай" in closed_text
    assert "тянись первой" in open_text or "иди на контакт активнее" in open_text
    assert closed_text != open_text


def test_contact_step_comes_from_scenario():
    """Шаг к нему — свойство сцены: дома объятие, на свидании продолжение."""
    date = load_scenario("first_date")
    open_ = PersonaState(trust=0.8, openness=0.9, energy=0.7)

    assert date.contact_hint in state_guidance(open_, date)
    # Без сценария остаётся прежнее поведение для пары, живущей вместе.
    assert "попроси объятие" in state_guidance(open_)


def test_frame_replaces_the_couple_only_intro(scenario):
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)

    assert scenario.frame in prompt
    assert "с тем, с кем живёт" not in prompt
    assert "Тебе сейчас нехорошо" not in prompt


def test_rules_use_scenario_hint():
    date = load_scenario("first_date")
    assert date.hint in rules_text(date)
    # Без своей подсказки сценарий получает общую.
    assert "не угадывай" in rules_text(load_scenario("friday_evening"))


def test_persona_prompt_reflects_current_state(scenario):
    closed = PersonaState(trust=0.3, openness=0.1, energy=0.2)
    open_ = PersonaState(trust=0.8, openness=0.9, energy=0.7)

    closed_prompt = persona_system_prompt(scenario, closed)
    open_prompt = persona_system_prompt(scenario, open_)

    assert "ты почти закрыта" in closed_prompt
    assert "ты совсем открыта" in open_prompt
    # Открытая героиня не должна изображать прежнюю закрытость.
    assert "не изображай прежнюю закрытость" in open_prompt
    assert closed_prompt != open_prompt


def test_state_guidance_names_trust_and_energy():
    state = PersonaState(trust=0.2, openness=0.7, energy=0.2)
    text = state_guidance(state)

    assert "не уверена" in text
    assert "сил мало" in text


def test_state_guidance_uses_mood_and_notes():
    state = PersonaState(
        mood="устала, но тянет к нему",
        trust=0.7,
        openness=0.7,
        energy=0.4,
        notes=["он уже предложил чай"],
    )
    text = state_guidance(state)

    assert "настроение" in text
    assert "устала, но тянет к нему" in text
    assert "помни, что уже было" in text


def test_debrief_prompt_lists_every_rubric_id(scenario):
    messages = debrief_messages(scenario, [{"role": "user", "content": "Привет"}])
    system = messages[0]["content"]
    for item in scenario.rubric:
        assert item.id in system


def test_state_clamps_and_keeps_notes():
    state = PersonaState.from_mapping({"mood": "злость", "trust": 3, "openness": -1})
    assert state.trust == 1.0
    assert state.openness == 0.0
    assert state.energy == 0.5

    state.apply({"trust": 0.9, "notes": ["он заметил"]})
    state.apply({"trust": 0.7, "notes": ["он заметил", "он давит"]})
    assert state.trust == 0.7
    assert state.notes == ["он заметил", "он давит"]


def test_state_ignores_garbage():
    state = PersonaState()
    state.apply({"trust": "много", "mood": None, "unknown": 1})
    assert state.trust == 0.5
    assert state.mood == "спокойно"


def test_state_grows_slowly_but_falls_fast():
    state = PersonaState(trust=0.5, openness=0.5, energy=0.5)

    state.apply({"trust": 0.95, "openness": 0.95, "energy": 0.95})
    assert state.trust == pytest.approx(0.6)
    assert state.openness == pytest.approx(0.65)
    assert state.energy == pytest.approx(0.55)

    # Падение не ограничиваем: доверие теряется быстрее, чем растёт.
    state.apply({"trust": 0.1, "openness": 0.1})
    assert state.trust == pytest.approx(0.1)
    assert state.openness == pytest.approx(0.1)


def test_parse_json_object_handles_code_fences():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(LLMError):
        parse_json_object("просто текст")


async def test_reply_updates_state_and_history(scenario):
    state_payload = json.dumps(
        {"mood": "мягче", "trust": 0.9, "openness": 0.8, "energy": 0.4},
        ensure_ascii=False,
    )
    llm = FakeLLM(["Нормально всё.", state_payload])
    engine = DialogueEngine(llm)
    session = engine.start(scenario)

    reply = await engine.reply(session, "Я вижу, что ты не в порядке")

    assert reply == "Нормально всё."
    # Рост зажат в коде: 0.55 + 0.1, 0.15 + 0.15, 0.2 + 0.05.
    assert session.state.trust == pytest.approx(0.65)
    assert session.state.openness == pytest.approx(0.30)
    assert session.state.energy == pytest.approx(0.25)
    assert session.state.mood == "мягче"
    assert session.user_turns == 1
    assert session.history[-2]["role"] == "user"
    assert session.history[-1] == {"role": "assistant", "content": "Нормально всё."}
    # Реплика — обычным текстом, состояние — отдельным JSON-запросом.
    assert llm.calls[0]["json_mode"] is False
    assert llm.calls[1]["json_mode"] is True


async def test_reply_updates_state_and_next_prompt_uses_it(scenario):
    """Состояние меняется после хода и попадает в промпт следующей реплики."""
    llm = FakeLLM(
        [
            "Ладно.",
            json.dumps(
                {"trust": 0.9, "openness": 0.9, "energy": 0.7},
                ensure_ascii=False,
            ),
        ]
    )
    engine = DialogueEngine(llm)
    session = engine.start(scenario)
    session.state = PersonaState(trust=0.7, openness=0.7, energy=0.6)

    await engine.reply(session, "Я рядом.")

    # 0.7 + 0.1, 0.7 + 0.15, 0.6 + 0.05.
    assert session.state.trust == pytest.approx(0.8)
    assert session.state.openness == pytest.approx(0.85)
    assert session.state.energy == pytest.approx(0.65)

    next_prompt = persona_system_prompt(scenario, session.state)
    assert "ты совсем открыта" in next_prompt
    assert "силы есть" in next_prompt


async def test_state_failure_does_not_break_reply(scenario):
    llm = FakeLLM(["Ну не знаю. Устала просто."])  # на второй запрос ответов нет
    engine = DialogueEngine(llm)
    session = engine.start(scenario)

    reply = await engine.reply(session, "Привет")

    assert reply == "Ну не знаю. Устала просто."
    assert session.state.trust == 0.55  # состояние не тронуто


async def test_debrief_scores_are_clamped(scenario):
    payload = json.dumps(
        {
            "scores": {"noticing": 5, "questions": -1, "validation": 2},
            "summary": "Разговор получился.",
            "strengths": ["Ты заметил."],
            "growth": ["Меньше вопросов подряд."],
            "moments": [{"quote": "Ты как?", "why": "Слишком общее."}],
            "rewrite": {"original": "Успокойся", "better": "Я рядом, хочешь — расскажешь."},
            "next_time": "Назвать чувство и замолчать.",
        },
        ensure_ascii=False,
    )
    llm = FakeLLM(
        [
            "Ладно.",
            json.dumps({"trust": 0.5}, ensure_ascii=False),
            payload,
        ]
    )
    engine = DialogueEngine(llm)
    session = engine.start(scenario)
    await engine.reply(session, "Привет")

    debrief = await engine.debrief(session)

    assert debrief.scores["noticing"] == 2
    assert debrief.scores["questions"] == 0
    assert debrief.scores["care_offer"] == 0
    assert debrief.total == 4
    assert debrief.max_total == 12
    assert session.finished is True

    text = debrief.render(scenario)
    assert "4 из 12" in text
    assert "Заметил состояние — 2/2" in text
    assert "Успокойся" in text


async def test_debrief_without_messages_is_refused(scenario):
    engine = DialogueEngine(FakeLLM([]))
    session = engine.start(scenario)
    with pytest.raises(LLMError):
        await engine.debrief(session)


async def test_demo_llm_tells_dialogue_from_debrief(scenario):
    """Демо-режим не должен отдавать реплику персонажа вместо разбора."""
    from bot.cli import DemoLLM, _demo_debrief, _demo_replies
    from bot.prompts import debrief_messages, persona_messages, state_messages

    llm = DemoLLM(_demo_replies(), _demo_debrief())
    state = PersonaState.from_mapping(scenario.initial_state)

    reply_raw = await llm.complete(persona_messages(scenario, state, []))
    assert reply_raw and not reply_raw.startswith("{")

    state_raw = await llm.complete(state_messages(scenario, state, []), json_mode=True)
    assert "trust" in json.loads(state_raw)

    debrief_raw = await llm.complete(
        debrief_messages(scenario, [{"role": "user", "content": "Привет"}]), json_mode=True
    )
    assert json.loads(debrief_raw)["scores"]["noticing"] == 2
