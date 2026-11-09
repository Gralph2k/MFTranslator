"""Сценарий «Первый звонок»: созвон голосом, продолжение переписки.

Отдельный файл, потому что здесь проверяется не сцена в комнате и не переписка,
а третий канал: только голос, экран звонка и переписка, которую персонаж помнит.
"""

import pytest

from bot.cli import DemoLLM, _demo_debrief, _demo_replies
from bot.engine import DialogueEngine
from bot.llm import FakeLLM
from bot.prompts import (
    backstory_text,
    debrief_messages,
    persona_system_prompt,
    rules_text,
)
from bot.scenario import load_scenario
from bot.state import PersonaState


@pytest.fixture
def scenario():
    return load_scenario("first_call")


def test_call_has_no_face_and_continues_the_chat(scenario):
    assert scenario.is_call
    assert scenario.medium == "call"
    assert not scenario.shows_face
    assert not scenario.is_correspondence
    assert scenario.profile is None
    assert scenario.continues == "first_message"
    assert scenario.canon_history
    assert scenario.opening.startswith("Алло")
    assert scenario.turn_limit == 10
    assert len(scenario.rubric) == 6
    assert scenario.max_score == 12


def test_rules_for_a_call_forbid_actions(scenario):
    rules = rules_text(scenario)

    assert "тренажёр, а не живая женщина" in rules
    assert "звонок" in rules.lower()
    assert "только свою речь" in rules
    assert "Протягиваю ей цветок" not in rules
    assert "Подсказка" not in rules


def test_backstory_mentions_the_phone(scenario):
    backstory = backstory_text(scenario)

    assert backstory.startswith("Что происходит:")
    assert "по телефону" in backstory
    assert scenario.backstory in backstory


def test_call_prompt_keeps_a_living_voice(scenario):
    """Созвон — главный риск сухости: голос должен звучать, а не телеграфировать."""
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)

    assert "Вы говорите по телефону" in prompt
    assert "Так на телефоне сухо" in prompt
    assert "220" in prompt
    assert scenario.persona.speech in prompt
    # «Отвечай суше» было прямой инструкцией на автоответчик.
    assert "суше" not in prompt.lower()
    assert "Смайликов нет" in prompt


def test_canon_chat_comes_into_the_prompt(scenario):
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state, list(scenario.canon_history))

    assert "До этой сцены вы переписывались" in prompt
    assert "сальса" in prompt
    assert "Он: " in prompt and "Ты: " in prompt


def test_engine_keeps_previous_chat(scenario):
    engine = DialogueEngine(FakeLLM([]))
    session = engine.start(scenario, list(scenario.canon_history))

    assert session.previous == list(scenario.canon_history)


def test_debrief_speaks_about_the_phone(scenario):
    messages = debrief_messages(
        scenario,
        [{"role": "user", "content": "Привет"}],
        list(scenario.canon_history),
    )
    system = messages[0]["content"]

    assert "положит трубку" in system
    assert "за это можно потерять переписку" not in system
    assert "До этой сцены вы переписывались" in system


def test_demo_replies_are_voiced_for_the_call():
    call_lines = _demo_replies("call")
    meeting_lines = _demo_replies("in_person")

    assert "Алло" in call_lines[0]
    assert call_lines != meeting_lines
    assert all(len(line) > 30 for line in call_lines)

    llm = DemoLLM(call_lines, _demo_debrief())
    assert llm.replies == call_lines


class _PhotoMessage:
    """Минимальное сообщение: экрану звонка нужен только answer_photo."""

    def __init__(self) -> None:
        self.photos: list[object] = []

    async def answer_photo(self, photo, caption=None):  # noqa: ANN001 - фейк
        self.photos.append(photo)


async def test_call_screen_is_sent_with_her_photo(scenario):
    from bot.telegram_bot import _send_call_screen

    message = _PhotoMessage()
    await _send_call_screen(message, scenario)

    assert message.photos, "экран звонка должен уйти до её первой реплики"
