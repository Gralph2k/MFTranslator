"""Контракт сценария: каждый файл в scenarios/ должен ему соответствовать."""

import pytest

from bot.faces import EMOTIONS
from bot.scenario import available_scenarios, load_scenario


@pytest.mark.parametrize("name", available_scenarios())
def test_scenario_meets_contract(name):
    scenario = load_scenario(name)

    assert scenario.skill, "навык сформулирован одним предложением"
    assert scenario.medium in {"in_person", "chat", "call"}
    if scenario.medium == "in_person":
        assert scenario.shows_face, "в сцене вживую лицо показывается"
    assert len(scenario.rubric) == 6, "рубрика — ровно 6 пунктов"
    assert scenario.max_score == 12
    assert 8 <= scenario.turn_limit <= 12
    assert scenario.initial_state["openness"] <= 0.25, "на старте она закрыта"
    assert len(scenario.secrets) >= 3

    # Голос персонажа описан подробно и с примерами интонации: иначе модель
    # понимает «закрыта» буквально и получается вежливый автоответчик.
    assert len(scenario.persona.speech) >= 80, "голос персонажа описан слишком коротко"
    assert "«" in scenario.persona.speech, "в speech нужен пример интонации"

    assert len(scenario.helps) >= 4
    assert len(scenario.hurts) >= 4

    # Рамка и шаг к нему берутся из сценария: без них промпт описывает пару,
    # которая живёт вместе, и врёт про первое свидание.
    assert scenario.frame, "нужна рамка разговора"
    assert scenario.contact_hint, "нужно, что значит шаг к нему в этой сцене"
    # Сценарий — папка: рядом со scenario.json лежит images/ с фотографиями.
    assert scenario.dir.is_dir(), "нет папки сценария"
    assert scenario.faces_dir.is_dir(), "нет папки для фотографий"

    # По скилу ловушка пишется как «ход — почему кажется разумным и что ломает».
    for hurt in scenario.hurts:
        assert "—" in hurt and len(hurt) > 60, f"ловушка без объяснения: {hurt}"

    # Среди рабочих ходов должна быть граница — просьба о ясности или отказ.
    assert any(("скажи" in help_.lower() or "границ" in help_.lower()) for help_ in scenario.helps)

    # Сценарий-продолжение: у него есть эталонная переписка и живой предшественник.
    if scenario.continues:
        assert scenario.canon_history, "у продолжения нужна канонная переписка"
        assert all(
            item["role"] in {"user", "assistant"} for item in scenario.canon_history
        )
        assert load_scenario(scenario.continues), "продолжение ссылается на живой сценарий"

    # Созвон: лица нет, анкеты уже нет, а экран звонка — единственная картинка.
    if scenario.medium == "call":
        assert not scenario.shows_face, "на созвоне лица не видно"
        assert scenario.profile is None, "у созвона не может быть карточки анкеты"
        assert (scenario.faces_dir / "call.jpg").is_file(), "нет фото для экрана звонка"


@pytest.mark.parametrize("name", available_scenarios())
def test_profile_scenarios_meet_contract(name):
    """Анкета — признак переписки: игрок начинает первым, фото не путаются с эмоциями."""
    scenario = load_scenario(name)
    if scenario.profile is None:
        return

    assert scenario.is_correspondence
    assert scenario.medium == "chat"
    assert not scenario.shows_face, "в переписке лица не видно — только текст и смайлики"
    assert scenario.opening == "", "переписку начинает игрок"
    assert len(scenario.profile.photos) >= 3, "в анкете нужно минимум 3 фото"
    assert scenario.profile.about, "в анкете нужен текст о себе"
    assert scenario.profile.hobbies or scenario.profile.interests, (
        "в анкете нужны увлечения или интересы"
    )
    assert scenario.red_flags, "у переписки должны быть красные линии"

    # Имена фото анкеты не должны совпадать с эмоциями: иначе faces.py
    # подставит фото из анкеты в диалог как кадр настроения.
    for photo in scenario.profile.photos:
        assert photo.split(".")[0] not in EMOTIONS, f"фото анкеты спорит с эмоцией: {photo}"

    # Подписи — только к существующим фото; их можно не задавать.
    assert set(scenario.profile.captions) <= set(scenario.profile.photos)
