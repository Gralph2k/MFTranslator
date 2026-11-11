"""Каталог героинь: одна личность на все сценарии, порядок, навигация, случайность."""

import random

import pytest

from bot.heroines import (
    heroines,
    heroine_for,
    load_heroine,
    next_scenario_id,
    random_heroine,
    story_scenarios,
)
from bot.scenario import ScenarioError, all_scenarios, available_scenarios, load_scenario


def test_two_heroines_in_order():
    catalog = heroines()

    assert [heroine.id for heroine in catalog] == ["vera", "eva"]
    assert catalog[0].name == "Вера"
    assert catalog[0].age == 30
    assert "редактор" in catalog[0].job
    assert catalog[1].name == "Ева"
    assert catalog[1].age == 26
    assert "фотограф" in catalog[1].job


def test_vera_has_three_scenarios_in_story_order():
    vera = next(heroine for heroine in heroines() if heroine.id == "vera")

    assert vera.scenarios == ("first_message/vera", "first_call/vera", "first_date/vera")
    assert vera.first_scenario == "first_message/vera"


def test_eva_has_three_scenarios_in_story_order():
    eva = next(heroine for heroine in heroines() if heroine.id == "eva")

    assert eva.scenarios == ("first_message/eva", "first_call/eva", "first_date/eva")
    assert eva.first_scenario == "first_message/eva"
    assert load_scenario(eva.first_scenario).is_correspondence
    assert load_scenario("first_call/eva").is_call
    assert load_scenario("first_date/eva").shows_face


def test_disabled_scenarios_are_out_of_rotation():
    assert "friday_evening/anya" not in available_scenarios()
    assert "reunion_call/ira" not in available_scenarios()
    # Но файлы целы и грузятся по id — «на будущее».
    assert load_scenario("friday_evening/anya").enabled is False
    assert "friday_evening/anya" in all_scenarios()


def test_story_chain_walks_through_heroines_and_wraps():
    assert story_scenarios() == [
        "first_message/vera",
        "first_call/vera",
        "first_date/vera",
        "first_message/eva",
        "first_call/eva",
        "first_date/eva",
    ]
    assert next_scenario_id("first_message/vera") == "first_call/vera"
    assert next_scenario_id("first_call/vera") == "first_date/vera"
    assert next_scenario_id("first_date/vera") == "first_message/eva"
    assert next_scenario_id("first_message/eva") == "first_call/eva"
    assert next_scenario_id("first_call/eva") == "first_date/eva"
    assert next_scenario_id("first_date/eva") == "first_message/vera"
    assert next_scenario_id("нет-такого") == "first_message/vera"


def test_heroine_for_scenario():
    assert heroine_for("first_date/vera").id == "vera"
    assert heroine_for("first_message/eva").id == "eva"
    assert heroine_for("friday_evening/anya") is None


def test_persona_is_shared_between_vera_scenarios():
    """Личность одна: имя, возраст, профессия и характер не расходятся по сценам."""
    personas = {
        scenario_id: load_scenario(scenario_id).persona
        for scenario_id in ("first_message/vera", "first_call/vera", "first_date/vera")
    }
    base = personas["first_message/vera"]

    for persona in personas.values():
        assert persona.name == base.name == "Вера"
        assert persona.age == base.age == 30
        assert persona.job == base.job
        assert persona.traits == base.traits
        assert base.speech in persona.speech
    # От сцены зависит только связь героев.
    assert len({persona.relation for persona in personas.values()}) == 3


def test_persona_is_shared_between_eva_scenarios():
    """Ева в переписке, на созвоне и на свидании — один человек, не три похожие."""
    personas = {
        scenario_id: load_scenario(scenario_id).persona
        for scenario_id in ("first_message/eva", "first_call/eva", "first_date/eva")
    }
    base = personas["first_message/eva"]

    for persona in personas.values():
        assert persona.name == base.name == "Ева"
        assert persona.age == base.age == 26
        assert persona.job == base.job
        assert persona.traits == base.traits
        assert base.speech in persona.speech
    assert len({persona.relation for persona in personas.values()}) == 3


def test_call_and_date_do_not_show_the_profile():
    assert load_scenario("first_message/vera").profile is not None
    assert load_scenario("first_call/vera").profile is None
    assert load_scenario("first_date/vera").profile is None


def test_heroine_file_has_valid_personality():
    vera = load_heroine("vera")

    assert vera.id == "vera"
    assert vera.order == 0
    assert len(vera.traits) >= 8
    assert len(vera.speech) >= 80
    assert "«" in vera.speech
    assert vera.profile is not None
    assert len(vera.profile.photos) == 3


def test_eva_file_has_four_profile_photos():
    eva = load_heroine("eva")

    assert eva.order == 1
    assert eva.profile is not None
    assert len(eva.profile.photos) == 4
    assert set(eva.profile.captions) == set(eva.profile.photos)


def test_missing_heroine_is_a_clear_error():
    with pytest.raises(ScenarioError):
        load_heroine("нет-такой")


def test_random_heroine_avoids_the_previous_one():
    """Антиповтор: если в прошлой сессии была Вера, выпадает Ева."""
    picked = {random_heroine(last="vera", rng=random.Random(seed)).id for seed in range(20)}

    assert picked == {"eva"}


def test_random_heroine_can_pick_either_without_history():
    picked = {
        random_heroine(last=None, rng=random.Random(seed)).id for seed in range(60)
    }

    assert picked == {"vera", "eva"}


def test_random_heroine_returns_catalog_object():
    heroine = random_heroine(rng=random.Random(1))

    assert heroine.id in {"vera", "eva"}
    assert heroine.first_scenario in story_scenarios()
