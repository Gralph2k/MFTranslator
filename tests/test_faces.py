from pathlib import Path

import pytest

from bot.faces import DEFAULT_FACES_DIR, EMOTIONS, emotion_for_state, face_path, label
from bot.state import PersonaState


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


def test_every_emotion_has_a_picture():
    """Все эмоции должны иметь собственный файл в images/."""
    missing = [
        emotion
        for emotion in EMOTIONS
        if face_path(emotion) is None or not face_path(emotion).stem.endswith(emotion)
    ]
    assert not missing, f"нет картинок для: {missing}"


def test_face_path_returns_existing_file():
    path = face_path("calm")
    assert path is not None and path.exists()
    assert path.parent == DEFAULT_FACES_DIR


def test_missing_directory_is_not_an_error():
    assert face_path("calm", DEFAULT_FACES_DIR.parent / "нет-такой-папки") is None


def test_unknown_emotion_has_no_file():
    assert face_path("восторг") is None


def test_labels_are_russian():
    assert label("tears") == "на глазах слёзы"
    assert label("guarded") == "насторожена"
    assert label("неизвестно") == "неизвестно"


def test_missing_emotion_uses_closest_face():
    """Если файла эмоции нет, берётся ближайшая по смыслу картинка."""
    folder = DEFAULT_FACES_DIR.parent / ".tmp" / "faces-fallback"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "smiling.jpg").write_bytes(b"")

    assert face_path("laughing", folder) == folder / "smiling.jpg"
