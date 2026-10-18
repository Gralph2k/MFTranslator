import json

import pytest

from bot.engine import DialogueEngine
from bot.llm import FakeLLM, LLMError, parse_json_object
from bot.prompts import debrief_messages, intro_text, persona_system_prompt
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


def test_intro_is_honest_about_being_a_simulator(scenario):
    text = intro_text(scenario)
    assert "тренажёр" in text.lower()
    assert scenario.title in text


def test_persona_prompt_contains_hidden_material(scenario):
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)
    assert scenario.persona.name in prompt
    assert scenario.secrets[0] in prompt
    assert "JSON" in prompt


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
    assert session.state.trust == 0.9
    assert session.state.mood == "мягче"
    assert session.user_turns == 1
    assert session.history[-2]["role"] == "user"
    assert session.history[-1] == {"role": "assistant", "content": "Нормально всё."}
    # Реплика — обычным текстом, состояние — отдельным JSON-запросом.
    assert llm.calls[0]["json_mode"] is False
    assert llm.calls[1]["json_mode"] is True


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
