"""Контракт сценария и героини: каждый файл в scenarios/ и heroines/ должен ему соответствовать."""

import json

import pytest

from bot.faces import EMOTIONS
from bot.heroines import load_heroine
from bot.scenario import SCENARIO_DIR, SCENARIO_ID_ALIASES, all_scenarios, load_scenario


@pytest.mark.parametrize("name", all_scenarios())
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
    assert scenario.contact_hint, "нужно, что значит шаг к ней в этой сцене"
    # Сценарий — папка: рядом со scenario.json лежит images/ с фотографиями.
    assert scenario.dir.is_dir(), "нет папки сценария"
    assert scenario.faces_dir.is_dir(), "нет папки для фотографий"
    # id — путь под scenarios/: папка и id не разъезжаются.
    assert scenario.id == scenario.dir.relative_to(SCENARIO_DIR).as_posix()
    assert scenario.id not in SCENARIO_ID_ALIASES, "id должен быть новым, а не алиасом"

    # По скилу ловушка пишется как «ход — почему кажется разумным и что ломает».
    for hurt in scenario.hurts:
        assert "—" in hurt and len(hurt) > 60, f"ловушка без объяснения: {hurt}"

    # Среди рабочих ходов должна быть граница — просьба о ясности или отказ.
    assert any(
        ("скажи" in help_.lower() or "границ" in help_.lower())
        for help_ in scenario.helps
    )

    if scenario.demo_replies:
        assert all(reply.strip() for reply in scenario.demo_replies)

    # Личность живёт в heroines/, сценарий хранит только сцену.
    raw = json.loads((scenario.dir / "scenario.json").read_text(encoding="utf-8"))
    if scenario.enabled:
        assert scenario.heroine, "у включённого сценария должна быть героиня"
        assert "persona" not in raw, "личность героини живёт в heroines/<slug>/heroine.json"
        assert "profile" not in raw, "анкета героини живёт в heroines/<slug>/heroine.json"
        assert raw.get("relation"), "сцене нужна связь героев (relation)"
    else:
        assert not scenario.heroine, "выключенный старый сценарий живёт без героини"

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


@pytest.mark.parametrize("name", all_scenarios())
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


def test_heroine_files_are_complete():
    """У каждой героини из ротации есть валидная личность и анкета."""
    slugs = {
        load_scenario(name).heroine
        for name in all_scenarios()
        if load_scenario(name).enabled
    }
    assert slugs == {"vera", "eva"}

    for slug in slugs:
        heroine = load_heroine(slug)
        assert heroine.name and heroine.job
        assert heroine.age > 0
        assert heroine.traits
        assert len(heroine.speech) >= 80
        assert "«" in heroine.speech
        assert heroine.profile is not None, "у героини в ротации должна быть анкета"
        assert len(heroine.profile.photos) >= 3
