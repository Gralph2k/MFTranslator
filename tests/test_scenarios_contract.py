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

    assert len(scenario.helps) >= 4
    assert len(scenario.hurts) >= 4
    # По скилу ловушка пишется как «ход — почему кажется разумным и что ломает».
    for hurt in scenario.hurts:
        assert "—" in hurt and len(hurt) > 60, f"ловушка без объяснения: {hurt}"

    # Среди рабочих ходов должна быть граница — просьба о ясности или отказ.
    assert any(("скажи" in help_.lower() or "границ" in help_.lower()) for help_ in scenario.helps)
