"""Контракт сценария: каждый файл в scenarios/ должен ему соответствовать."""

import pytest

from bot.scenario import available_scenarios, load_scenario


@pytest.mark.parametrize("name", available_scenarios())
def test_scenario_meets_contract(name):
    scenario = load_scenario(name)

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
