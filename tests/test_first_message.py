"""Сценарий «Первое сообщение»: переписка в приложении, первый ход за игроком.

Отдельный файл, потому что здесь проверяется не сцена в комнате, а переписка:
анкета, пустой opening, красные линии и правила «только текст».
"""

import json
import logging

import pytest

from bot.engine import DialogueEngine
from bot.llm import FakeLLM
from bot.prompts import (
    backstory_text,
    debrief_messages,
    persona_system_prompt,
    profile_text,
    rules_text,
    state_guidance,
    state_messages,
)
from bot.scenario import load_scenario
from bot.state import PersonaState


@pytest.fixture
def scenario():
    return load_scenario("first_message/vera")


def test_chat_scenario_has_profile_and_red_flags(scenario):
    assert scenario.is_correspondence
    assert scenario.medium == "chat"
    assert not scenario.shows_face, "лица в переписке не видно"
    assert scenario.profile is not None
    assert len(scenario.profile.photos) == 3
    assert scenario.profile.hobbies or scenario.profile.interests
    assert scenario.red_flags
    assert scenario.opening == ""


def test_in_person_scenario_shows_the_face():
    date = load_scenario("first_date/vera")

    assert date.shows_face
    assert not date.is_correspondence


def test_player_writes_first(scenario):
    """Пустой opening — старт с пустой стенограммы, бот не шлёт свою реплику."""
    engine = DialogueEngine(FakeLLM([]))
    session = engine.start(scenario)

    assert session.history == []
    assert session.turns_left == scenario.turn_limit


def test_rules_for_correspondence_are_text_only(scenario):
    rules = rules_text(scenario)

    # Сначала рамка тренажёра, потом правила и команды — без подсказки на ход.
    assert "тренажёр, а не живая женщина" in rules
    assert "Команды" in rules
    assert "Подсказка" not in rules
    assert "первое сообщение в переписке" in rules
    assert "только текст" in rules
    assert "Протягиваю ей цветок" not in rules


def test_backstory_has_no_trainer_frame_and_no_repetitions(scenario):
    backstory = backstory_text(scenario)

    assert backstory.startswith("Что происходит:")
    assert "тренажёр" not in backstory.lower()
    # Хвост с именем и «переписываешься» для переписки убран: имя в карточке.
    assert "Ты переписываешься" not in backstory
    assert scenario.backstory in backstory
    # Знакомство описано один раз, без второго «матча» и повторов.
    assert "матч" not in backstory.lower()
    assert backstory.count("познакомились") == 1


def test_rules_for_a_meeting_still_allow_actions():
    rules = rules_text(load_scenario("first_date/vera"))

    assert "Протягиваю ей цветок" in rules


def test_profile_card_text_uses_her_material(scenario):
    text = profile_text(scenario)

    assert "Вера" in text
    assert "30" in text
    assert "издательств" in text
    # Текстовая карточка (CLI и запасной вариант) показывает хобби и интересы,
    # а не только место работы.
    assert "Хобби" in text
    assert "танцы" in text.lower()
    assert "Интересы" in text


def test_card_uses_the_caption_of_each_photo(scenario):
    """На карточке — подпись своего кадра, а не одна профессия на все."""
    from bot.profile_card import card_caption

    assert "издательств" in card_caption(scenario, "profile_1.jpg")
    assert "Хобби" in card_caption(scenario, "profile_2.jpg")
    assert "Интересы" in card_caption(scenario, "profile_3.jpg")
    # Нет подписи — остаётся профессия, а не пустое место.
    assert card_caption(scenario, "нет-такого.jpg") == scenario.persona.job


def test_persona_knows_her_life_and_likes(scenario):
    """Факты из характера попадают в промпт: юмор, комплименты, поездки, планы."""
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)

    assert "необидный юмор" in prompt
    assert "ненавязчивые комплименты" in prompt
    assert "партнёра по танцам" in prompt
    assert "замуж не спешит" in prompt
    assert "Детей нет, но хотела бы" in prompt
    assert "Турции" in prompt and "Египте" in prompt
    assert "риф" in prompt


def test_profile_captions_split_the_story(scenario):
    """Подписи к фото: работа, хобби, интересы — у каждого кадра своя."""
    captions = scenario.profile.captions

    assert set(captions) == set(scenario.profile.photos)
    assert "издательств" in captions["profile_1.jpg"].lower()
    second = captions["profile_2.jpg"].lower()
    assert "хобби" in second and "танцы" in second
    third = captions["profile_3.jpg"].lower()
    assert "интересы" in third and "кофе" in third
    # «Раз в год» владелец убрал: интересы без срока.
    assert "раз в год" not in " ".join(captions.values()).lower()
    # Хобби есть и в данных профиля: карточка называет их текстом.
    assert "танцы" in scenario.profile.hobbies


def test_profile_card_images_have_the_app_ui(scenario):
    """Карточка рисуется кодом поверх фото: имена, счётчик, точки, кнопки."""
    from bot.profile_card import render_profile_cards

    cards = render_profile_cards(scenario)

    assert len(cards) == 3
    for card in cards:
        assert card.is_file()
        assert card.stat().st_size > 10_000


def test_persona_prompt_has_correspondence_and_red_lines(scenario):
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)

    assert "переписываетесь" in prompt
    assert "Лица он не видит" in prompt
    # В переписке смайлики — часть речи, но только на яркой эмоции.
    assert "Смайлики — можно" in prompt
    assert "эмоция яркая" in prompt
    assert "смех, радость, смущение" in prompt
    assert "не в каждой реплике" in prompt
    assert "без смайликов" not in prompt
    assert "Что для тебя недопустимо" in prompt
    assert scenario.red_flags[0] in prompt
    assert "заканчиваешь" in prompt
    assert "без нотаций" in prompt


def test_meeting_prompt_keeps_the_no_emoji_rule():
    """Вживую лицо видно: смайлики там не нужны и остаются запрещёнными."""
    date = load_scenario("first_date/vera")
    prompt = persona_system_prompt(date, PersonaState.from_mapping(date.initial_state))

    assert "без смайликов" in prompt


def test_persona_prompt_has_no_examiner_voice(scenario):
    """В переписке она реагирует, а не оценивает его первое сообщение."""
    state = PersonaState.from_mapping(scenario.initial_state)
    prompt = persona_system_prompt(scenario, state)

    assert "Ты не экзаменатор" in prompt
    assert "не оцениваешь его сообщения" in prompt
    assert "оставь зацепку" in prompt
    assert "Не веди счёт" in prompt
    assert "Не комментируй сам разговор" in prompt
    # Регрессии голоса: «одно-два слова» и «укол вместо ответа» возвращали
    # автоответчик и экзаменатора, а не живую женщину.
    assert "одно-два слова" not in scenario.persona.speech
    assert "укол вместо ответа" not in scenario.persona.speech


def test_state_guidance_at_low_openness_gives_content(scenario):
    """Даже закрытая реплика в переписке содержит деталь, а не только оценку."""
    text = state_guidance(
        PersonaState(trust=0.3, openness=0.1, energy=0.2), scenario
    )

    assert "одна короткая фраза" in text
    assert "деталь" in text
    assert "не оценивай" in text
    assert "не предлагай" in text


def test_heroine_does_not_schedule_the_call_herself(scenario):
    """Шаг игрока (contact_hint) не должен становиться шагом героини в переписке.

    Иначе при высокой открытости она сама назначает день и время созвона —
    и пункт «дошёл до конкретики» перестаёт проверять навык игрока.
    """
    open_ = PersonaState(trust=0.8, openness=0.9, energy=0.7)
    text = state_guidance(open_, scenario)

    assert scenario.contact_hint not in text
    assert "назовёт он" in text
    assert "Не подсказывай" in text

    almost_open = PersonaState(trust=0.7, openness=0.7, energy=0.6)
    middle = state_guidance(almost_open, scenario)

    assert scenario.contact_hint not in middle
    assert "день и время называет он" in middle
    assert "ни созвон, ни встречу" in middle
    assert "Не подсказывай" in middle


def test_drained_heroine_in_chat_does_not_offer_physical_contact(scenario):
    """Открытая, но выдохшаяся героиня в переписке не предлагает обнять.

    Ветку «открыта, но сил нет» писали для встречи, и до правки она попадала
    в переписку без развилки по medium: героиня звала «посидеть рядом»
    в приложении знакомств, где они вживую ещё не виделись.
    """
    drained = PersonaState(trust=0.7, openness=0.7, energy=0.2)

    text = state_guidance(drained, scenario)

    assert "обнять" not in text
    assert "посидеть рядом" not in text
    assert "день и время называет он" in text

    # На встрече то же состояние остаётся тихим шагом к близости.
    in_person = state_guidance(drained, load_scenario("first_date/vera"))
    assert "посидеть рядом" in in_person


def test_red_flag_pressure_after_refusal_ends_the_chat(scenario):
    """Игнорирование прямого «нет» — красная линия, а не очередная ловушка."""
    prompt = persona_system_prompt(
        scenario, PersonaState.from_mapping(scenario.initial_state)
    )

    assert "второй раз просит то же самое" in prompt
    assert any("Давление после отказа" in item for item in scenario.red_flags)


def test_observer_ends_chat_on_explicit_goodbye(scenario):
    """Если она попрощалась, разговор закончен, даже если он написал ещё раз."""
    system = state_messages(
        scenario,
        PersonaState.from_mapping(scenario.initial_state),
        [{"role": "user", "content": "Привет"}],
    )[0]["content"]

    assert "Не жди его ответа" in system


def test_new_red_flags_cover_sexual_and_manipulation(scenario):
    text = "\n".join(scenario.red_flags)

    assert "Ранняя сексуализация" in text
    assert "Манипуляция" in text


def test_new_hurts_cover_interrogation_and_short_answers(scenario):
    text = "\n".join(scenario.hurts)

    assert "зачем ты здесь" in text
    assert "не скучно тебе с книжками" in text
    assert "Односложные ответы" in text


def test_sexual_red_flag_distinguishes_explicit_and_ambiguous(scenario):
    """Явный намёк — сразу уход; двусмысленный — одна граница и только потом уход."""
    text = "\n".join(scenario.red_flags)

    assert "явный намёк" in text
    assert "Двусмысленный" in text

    prompt = persona_system_prompt(scenario, PersonaState.from_mapping(scenario.initial_state))
    assert "Двусмысленный намёк" in prompt


def test_red_flag_block_ends_on_sexual_and_manipulation(scenario):
    prompt = persona_system_prompt(scenario, PersonaState.from_mapping(scenario.initial_state))

    assert "сексуальным намёкам" in prompt
    assert "манипулирует" in prompt


def test_observer_does_not_score_his_answers(scenario):
    """Наблюдатель не превращает заметки в обвинительный список и не судит старт."""
    system = state_messages(
        scenario, PersonaState.from_mapping(scenario.initial_state), []
    )[0]["content"]

    assert "обвинительный" in system
    assert "по делу" in system
    assert "не в ноль" in system
    assert "больше не ждёт" in system  # запрещённая формулировка-приговор


def test_first_template_is_a_soft_line(scenario):
    """Первый шаблон — не красная линия: короткий ответ без счёта, повтор — уход."""
    first = scenario.red_flags[0]

    assert "без счёта" in first
    assert "без оценки" in first
    assert "повторяет шаблон" in first


def test_situation_has_no_scoreboard(scenario):
    """Счёт «ты восьмой» приходил из данных сценария; его там быть не должно."""
    text = " ".join([scenario.situation, *scenario.persona.traits])

    assert "восемь" not in text
    assert "десяток" not in text
    assert "книг" in scenario.situation.lower()


def test_turn_limit_leaves_room_for_wind_down(scenario):
    """Лимит не обрывает разговор: у Веры есть запас на предупреждение и прощание."""
    assert scenario.turn_limit == 12
    assert scenario.wrap_up_at >= 2
    assert scenario.wrap_up_reasons


def test_persona_winds_down_before_the_limit(scenario):
    state = PersonaState.from_mapping(scenario.initial_state)

    early = persona_system_prompt(scenario, state, turns_left=8)
    assert "подходит к концу" not in early

    warning = persona_system_prompt(scenario, state, turns_left=2)
    assert "осталось 2" in warning
    assert "пора заканчивать" in warning
    assert scenario.wrap_up_reasons[0] in warning

    final = persona_system_prompt(scenario, state, turns_left=0)
    assert "последняя реплика" in final
    assert "Попрощайся" in final
    assert scenario.wrap_up_reasons[0] in final


def test_observer_sets_ended_on_red_line(scenario):
    state = PersonaState.from_mapping(scenario.initial_state)
    system = state_messages(scenario, state, [])[0]["content"]

    assert "красные линии" in system.lower()
    assert "ended=true" in system


def test_debrief_knows_red_lines(scenario):
    system = debrief_messages(scenario, [{"role": "user", "content": "Привет"}])[0]["content"]

    assert "недопустимо" in system


async def test_red_line_ends_the_dialogue(scenario):
    llm = FakeLLM(
        [
            "Ладно, пока.",
            json.dumps(
                {"mood": "брезгливо", "trust": 0.0, "openness": 0.0, "ended": True},
                ensure_ascii=False,
            ),
        ]
    )
    engine = DialogueEngine(llm)
    session = engine.start(scenario)

    await engine.reply(session, "Ты чего такая?")

    assert session.ended_by_persona
    assert session.is_over


async def test_end_marker_closes_the_dialogue(scenario, caplog):
    """Маркер [[конец]] закрывает сессию сам, не дожидаясь наблюдателя."""
    caplog.set_level(logging.INFO)
    llm = FakeLLM(
        [
            "Всё, пока. Хорошего вечера. [[конец]]",
            json.dumps(
                {"mood": "спокойно", "trust": 0.1, "openness": 0.0, "ended": False},
                ensure_ascii=False,
            ),
        ]
    )
    engine = DialogueEngine(llm)
    session = engine.start(scenario)

    reply = await engine.reply(session, "Скинь номер")

    assert session.ended_by_persona
    assert session.is_over
    assert "[[конец]]" not in reply
    assert "[[конец]]" not in session.history[-1]["content"]
    assert "маркером" in caplog.text


async def test_engine_ends_on_farewell_phrase(scenario):
    """«Пока»/«Удачи» без маркера всё равно закрывают разговор — это страховка."""
    llm = FakeLLM(
        [
            "Всё, пока.",
            json.dumps(
                {"mood": "спокойно", "trust": 0.2, "openness": 0.1, "ended": False},
                ensure_ascii=False,
            ),
        ]
    )
    engine = DialogueEngine(llm)
    session = engine.start(scenario)

    reply = await engine.reply(session, "Скинь номер")

    assert reply == "Всё, пока."
    assert session.ended_by_persona
    assert session.is_over


async def test_engine_does_not_end_on_planned_goodbye(scenario):
    """«До завтра» — не конец: договорились продолжить."""
    llm = FakeLLM(
        [
            "До завтра.",
            json.dumps(
                {"mood": "спокойно", "trust": 0.2, "openness": 0.1, "ended": False},
                ensure_ascii=False,
            ),
        ]
    )
    engine = DialogueEngine(llm)
    session = engine.start(scenario)

    await engine.reply(session, "Тогда завтра?")

    assert not session.ended_by_persona
    assert not session.is_over


def test_persona_prompt_explains_end_marker(scenario):
    prompt = persona_system_prompt(scenario, PersonaState.from_mapping(scenario.initial_state))

    assert "[[конец]]" in prompt


def test_debrief_has_computed_question_facts(scenario):
    history = [
        {"role": "user", "content": "Привет. А что за книга? И как тебе метро?"},
        {"role": "assistant", "content": "Привет. Книга про море. А ты?"},
        {"role": "user", "content": "Понял."},
    ]
    system = debrief_messages(scenario, history)[0]["content"]

    assert "Посчитано кодом" in system
    assert "всего «?»: 2" in system
    assert "реплик с двумя и более вопросами: 1" in system
