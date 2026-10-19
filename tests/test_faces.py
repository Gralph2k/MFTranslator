import uuid
from pathlib import Path

import pytest

from bot.faces import EMOTIONS, emotion_for_state, face_path, label
from bot.scenario import available_scenarios, load_scenario
from bot.state import PersonaState

# %TEMP% в этой среде закрыт песочницей, поэтому фикстуру tmp_path не используем.
TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp"


def _folder(name: str) -> Path:
    folder = TMP_ROOT / f"faces-{name}-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


@pytest.mark.parametrize(
    ("mood", "extra", "expected"),
    [
        ("на глазах слёзы", {}, "tears"),
        ("плачет", {}, "tears"),
        ("улыбается", {}, "smiling"),
        ("смеётся", {}, "laughing"),
        ("настороженная, цепкая", {}, "guarded"),
        ("обижена", {}, "hurt"),
        ("теплеет", {}, "warming"),
        ("раздражение под усталостью", {}, "irritated"),
        ("спокойно", {"trust": 0.3}, "irritated"),
        ("усталость", {"energy": 0.15, "openness": 0.2}, "tired"),
        ("спокойно", {"energy": 0.5, "openness": 0.2}, "calm"),
        ("спокойно", {"energy": 0.5, "openness": 0.4, "trust": 0.5}, "closed"),
        ("спокойно", {"energy": 0.5, "openness": 0.7, "trust": 0.6}, "warming"),
    ],
)
def test_emotion_mapping(mood, extra, expected):
    state = PersonaState(mood=mood, **extra)
    assert emotion_for_state(state) == expected


def test_emotion_is_case_and_yo_insensitive():
    assert emotion_for_state(PersonaState(mood="ОБИЖЕНА")) == "hurt"
    assert emotion_for_state(PersonaState(mood="слёзы")) == "tears"


def test_faces_live_next_to_the_scenario():
    """Фотографии — часть сценария, а не общая папка на всех."""
    for name in available_scenarios():
        scenario = load_scenario(name)
        assert scenario.dir.name == name
        assert scenario.faces_dir == scenario.dir / "images"


@pytest.mark.parametrize("name", ["friday_evening", "reunion_call"])
def test_every_emotion_has_a_picture(name):
    """У сценариев с готовым набором есть файл на каждую эмоцию."""
    scenario = load_scenario(name)
    missing = [emotion for emotion in EMOTIONS if face_path(emotion, scenario.faces_dir) is None]
    assert not missing, f"{name}: нет картинок для {missing}"


def test_scenario_without_photos_falls_back_to_text():
    """Пока у Веры нет кадров, бот просто не шлёт фото — это не ошибка."""
    folder = _folder("empty")
    assert face_path("calm", folder) is None


def test_missing_directory_is_not_an_error():
    assert face_path("calm", TMP_ROOT / "нет-такой-папки") is None


def test_unknown_emotion_has_no_file():
    scenario = load_scenario("friday_evening")
    assert face_path("восторг", scenario.faces_dir) is None


def test_labels_are_russian():
    assert label("tears") == "на глазах слёзы"
    assert label("guarded") == "насторожена"
    assert label("неизвестно") == "неизвестно"


def test_missing_emotion_uses_closest_face():
    """Если файла эмоции нет, берётся ближайшая по смыслу картинка."""
    folder = _folder("fallback")
    (folder / "smiling.jpg").write_bytes(b"")

    assert face_path("laughing", folder) == folder / "smiling.jpg"
