import pytest

from bot.engine import DialogueEngine
from bot.llm import FakeLLM
from bot.safety import CrisisDetected, detect_crisis, safety_message
from bot.scenario import load_scenario


@pytest.fixture
def scenario():
    return load_scenario("friday_evening")


@pytest.mark.parametrize(
    "text",
    [
        "Я не хочу жить",
        "мне кажется, я хочу умереть",
        "меня бьёт муж",
        "он угрожает убить меня",
        "хочу её ударить",
    ],
)
def test_crisis_is_detected(text):
    assert detect_crisis(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "Привет, как ты?",
        "Я не хочу об этом говорить",
        "Она меня не слышит",
        "Устал, хочу спать",
    ],
)
def test_ordinary_messages_are_not_crisis(text):
    assert detect_crisis(text) is False


def test_detection_is_case_and_yo_insensitive():
    assert detect_crisis("МЕНЯ БЬЕТ МУЖ") is True
    assert detect_crisis("меня бьёт муж") is True


def test_safety_message_points_to_help():
    text = safety_message("Телефон доверия: 000")
    assert "112" in text
    assert "Телефон доверия: 000" in text
    assert "тренажёр" in text.lower()


def test_safety_message_without_resources_still_works():
    text = safety_message()
    assert "112" in text
    assert "службу психологической помощи" in text.lower()


async def test_engine_stops_scene_and_does_not_call_model(scenario):
    # Пустой FakeLLM: если движок всё-таки пойдёт в модель, тест упадёт с LLMError.
    engine = DialogueEngine(FakeLLM([]))
    session = engine.start(scenario)

    with pytest.raises(CrisisDetected):
        await engine.reply(session, "Я больше не хочу жить")

    assert session.history[-1] == {"role": "user", "content": "Я больше не хочу жить"}
    assert session.user_turns == 1
