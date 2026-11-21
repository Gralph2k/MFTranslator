"""«Проверка анкеты»: парсинг, счёт, флоу, хранение, бонус ходов."""

import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from bot import telegram_bot
from bot.engine import DialogueEngine
from bot.llm import FakeLLM
from bot.profile_check import (
    PROFILE_BONUS_TURNS,
    consultant_messages,
    load_config,
    parse_name_age,
    parse_photo_review,
    parse_text_review,
    player_profile_block,
    render_photo_review,
    render_text_review,
)
from bot.prompts import persona_messages, rules_text
from bot.scenario import load_scenario
from bot.state import PersonaState
from bot.storage import Storage
from bot.telegram_bot import Trainer

TMP_ROOT = Path(__file__).resolve().parent.parent / ".tmp"


@pytest.fixture
def store():
    folder = TMP_ROOT / f"check-{uuid.uuid4().hex[:8]}"
    folder.mkdir(parents=True, exist_ok=True)
    storage = Storage(folder / "test.db")
    yield storage
    storage.close()


def _trainer(storage) -> Trainer:
    return Trainer(DialogueEngine(FakeLLM([])), storage, load_scenario(), with_faces=False)


class FakeMessage:
    """Минимальный Message: хендлеру нужны text, from_user.id и answer()."""

    def __init__(self, text: str, user_id: int = 1) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)
        self.sent: list[str] = []

    async def answer(self, text: str, **kwargs) -> None:
        self.sent.append(text)


# --- парсинг и счёт --------------------------------------------------------


def test_parse_name_age_variants():
    assert parse_name_age("Саша, 32") == ("Саша", 32)
    assert parse_name_age("саша 32 года") == ("Саша", 32)
    assert parse_name_age("Мне 35, зовут Дима") == ("Дима", 35)
    assert parse_name_age("Дима, мне 35") == ("Дима", 35)


def test_parse_name_age_rejects_garbage():
    assert parse_name_age("Саша") is None  # нет возраста
    assert parse_name_age("Саша, 7") is None  # вне диапазона
    assert parse_name_age("32") is None  # нет имени
    assert parse_name_age("") is None


def test_consultant_own_rewrite_rule():
    """Свой прошлый rewrite: без него блока нет, с ним - блок и правило «не критикуй моё»."""
    system = consultant_messages("Саша", 32, "Текст анкеты")[0]["content"]
    assert "прошлая рекомендация" not in system

    system = consultant_messages(
        "Саша", 32, "Текст анкеты", prev_rewrite="Инженер, горы по выходным"
    )[0]["content"]
    assert "Твоя прошлая рекомендация" in system
    assert "Инженер, горы по выходным" in system
    assert "к собственной рекомендации запрещено" in system


def test_consultant_no_flag_minimum_and_factual_rule():
    """0 флагов - легальный ответ; претензия должна быть фактически верной цитате."""
    system = consultant_messages("Саша", 32, "Текст анкеты")[0]["content"]
    assert "0 - нормальный ответ" in system
    assert "не выдумывай претензии ради минимума" in system
    assert "Претензия должна быть фактически верной для своей цитаты" in system


def test_config_has_limits_and_flags():
    cfg = load_config()
    assert cfg["max_photos"] == 4
    assert cfg["max_text_iterations"] == 6
    assert cfg["max_photo_reviews"] == 3
    assert len(cfg["text_red_flags"]) >= 10
    assert len(cfg["text_green_flags"]) >= 5
    assert len(cfg["photo_red_flags"]) >= 10
    assert len(cfg["photo_green_flags"]) >= 5
    assert cfg["recommended_length"] == [50, 150]


# --- разборы модели --------------------------------------------------------

PROFILE_REVIEW = json.dumps(
    {
        "verdict": "Живой текст, но начало звучит как выговор.",
        "flags": [
            {"type": "red", "title": "Негатив", "quote": "меркантильные мимо",
             "comment": "Убери фильтр, расскажи о себе."},
            {"type": "green", "title": "Конкретика", "comment": "Горы цепляют."},
        ],
        "rewrite": "Инженер, горы по выходным. Ищу ту, с кем интересно спорить.",
    },
    ensure_ascii=False,
)

PHOTO_REVIEW = json.dumps(
    {
        "photos": [
            {"index": 1, "keep": True, "verdict": "Портрет в дневном свете.",
             "flags": [{"type": "green", "title": "Лицо открыто", "comment": "Хорошее первое фото."}]},
            {"index": 2, "keep": False, "verdict": "Селфи в зеркале.",
             "flags": [{"type": "red", "title": "Зеркало и телефон", "comment": "Замени."}]},
        ],
        "set": {"verdict": "Планов мало.", "flags": [{"type": "red", "title": "Нет роста", "comment": "Добавь фото в рост."}],
                "advice": "Добавь ростовое фото с хобби."},
        "contents": ["портрет на улице", "селфи в зеркале лифта"],
        "same_person": True,
    },
    ensure_ascii=False,
)


def test_parse_and_render_text_review():
    review = parse_text_review(json.loads(PROFILE_REVIEW))
    assert review.score == 0  # один зелёный, один красный
    assert review.greens == 1 and review.reds == 1

    text = render_text_review(review)
    assert "Счёт" not in text
    assert "Негатив" in text and "«меркантильные мимо»" in text
    assert "Как звучит лучше:" in text and "Было:" not in text
    assert "Инженер, горы по выходным. Ищу ту, с кем интересно спорить." in text


def test_parse_and_render_photo_review():
    review = parse_photo_review(json.loads(PHOTO_REVIEW))
    assert len(review.photos) == 2
    assert review.photos[0].keep is True
    assert review.same_person is True
    assert review.contents == ["портрет на улице", "селфи в зеркале лифта"]

    text = render_photo_review(review)
    assert "✅ Фото 1" in text and "❌ Фото 2" in text
    assert "- +" not in text  # баллов у фото больше нет
    assert "Набор целиком" in text
    assert "Главный совет: Добавь ростовое" in text
    assert "разные люди" not in text  # same_person=True - предупреждения нет


def test_parse_photo_review_limits_contents_to_expected():
    """Модель дорисовала contents за несуществующие кадры - режем по expected."""
    review = parse_photo_review(
        {"photos": [], "set": {}, "contents": ["а", "б", "в", "г", "д"]}, expected=2
    )
    assert review.contents == ["а", "б"]


def test_photo_review_flags_different_people():
    review = parse_photo_review({"photos": [], "set": {}, "same_person": False})
    assert "разные люди" in render_photo_review(review)


# --- промпт героини и ходы -------------------------------------------------


def test_player_profile_block_is_sanitized():
    block = player_profile_block("Саша", 32, "Люблю горы и велосипед")
    assert "Саша" in block and "горы" in block
    assert "Счёт" not in block  # оценки и разборы героине не уходят


def test_player_profile_block_includes_photo_contents():
    """Содержимое фото доступно героине: любопытство, а не экзамен."""
    block = player_profile_block(
        "Саша", 32, "Люблю горы", photo_contents=["гольф, кадр в рост", "квадроцикл в пустыне"]
    )
    assert "гольф" in block and "квадроцикл" in block
    assert "не экзаменатор" in block.replace("не как экзаменатор", "не экзаменатор") or "любопытно" in block
    # Установка «не зацикливаться» присутствует
    assert "не возвращайся к фотографиям в каждом сообщении" in block

    without = player_profile_block("Саша", 32, "Люблю горы")
    assert "На фотографиях" not in without


def test_persona_prompt_gets_profile_block():
    scenario = load_scenario("first_message/vera")
    state = PersonaState.from_mapping(scenario.initial_state)
    with_profile = persona_messages(
        scenario, state, [], player_profile=player_profile_block("Саша", 32, "Люблю горы")
    )
    assert "Саша" in with_profile[0]["content"]

    without = persona_messages(scenario, state, [])
    assert "Саша" not in without[0]["content"]


def test_rules_text_does_not_mention_turn_count():
    """Количество сообщений в правилах не называется: лимит - страховка движка,
    а не условие игры; игрок, считающий ходы, играет в счётчик."""
    scenario = load_scenario("first_message/vera")
    text = rules_text(scenario)
    assert "сообщений" not in text.replace("текст сообщений", "")
    assert str(scenario.turn_limit) not in text
    assert "разбор придёт сам" in text
    # Бонус за анкету остаётся в движке, просто не афишируется.
    assert PROFILE_BONUS_TURNS == 3


# --- хранение ---------------------------------------------------------------


def test_profile_check_lifecycle(store):
    user_id = store.ensure_user(1)
    check_id = store.create_profile_check(user_id)

    stored = store.get_active_profile_check(user_id)
    assert stored is not None and stored.id == check_id and stored.phase == "name"

    store.update_profile_check(check_id, name="Саша", age=32, bio="Люблю горы", phase="menu")
    stored = store.get_active_profile_check(user_id)
    assert stored.name == "Саша" and stored.age == 32 and stored.phase == "menu"

    store.update_profile_check(check_id, phase="done", completed=1)
    assert store.get_active_profile_check(user_id) is None

    completed = store.last_completed_profile(user_id)
    assert completed is not None and completed.bio == "Люблю горы"
    assert store.has_completed_profile(user_id) is True


def test_new_check_abandons_previous_active(store):
    user_id = store.ensure_user(1)
    store.create_profile_check(user_id)
    store.update_profile_check(store.get_active_profile_check(user_id).id, phase="photos")
    store.create_profile_check(user_id)  # второй прогон

    active = store.get_active_profile_check(user_id)
    assert active is not None and active.phase == "name"


def test_update_profile_check_ignores_unknown_fields(store):
    user_id = store.ensure_user(1)
    check_id = store.create_profile_check(user_id)
    store.update_profile_check(check_id, name="Саша", evil="; DROP TABLE users;")
    stored = store.get_active_profile_check(user_id)
    assert stored.name == "Саша"
    assert store.count_sessions() >= 0  # база жива


def test_photo_contents_roundtrip(store):
    """Содержимое фото: список в памяти, JSON в базе, список при чтении."""
    user_id = store.ensure_user(1)
    check_id = store.create_profile_check(user_id)
    store.update_profile_check(
        check_id,
        name="Саша",
        bio="Люблю горы",
        phase="done",
        completed=1,
        photo_contents=["гольф, кадр в рост", "квадроцикл"],
    )

    profile = store.last_completed_profile(user_id)
    assert profile is not None
    assert profile.photo_contents == ["гольф, кадр в рост", "квадроцикл"]


def test_last_rewrite_roundtrip(store):
    """Своя рекомендация переживает рестарт: колонка в базе, поле в объекте."""
    user_id = store.ensure_user(1)
    check_id = store.create_profile_check(user_id)
    store.update_profile_check(check_id, last_rewrite="Инженер, горы по выходным")

    stored = store.get_active_profile_check(user_id)
    assert stored is not None
    assert stored.last_rewrite == "Инженер, горы по выходным"


def test_profile_checks_deleted_with_user(store):
    user_id = store.ensure_user(42)
    check_id = store.create_profile_check(user_id)
    store.update_profile_check(check_id, name="Саша", bio="текст")

    store.delete_user(42)

    assert store.get_active_profile_check(user_id) is None
    with store._lock:
        row = store._conn.execute(
            "SELECT COUNT(*) AS total FROM profile_checks WHERE user_id = ?", (user_id,)
        ).fetchone()
    assert row["total"] == 0


# --- флоу в боте ------------------------------------------------------------


async def test_flow_from_name_to_text_review(store, monkeypatch):
    llm = FakeLLM([PROFILE_REVIEW])
    trainer = Trainer(DialogueEngine(llm), store, load_scenario(), with_faces=False)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)

    flow = trainer.start_profile_flow(1)
    assert flow.check.phase == "name"

    await telegram_bot.on_profile_text(FakeMessage("Саша, 32"))
    assert flow.check.phase == "bio"
    assert flow.check.name == "Саша" and flow.check.age == 32

    message = FakeMessage("Нормальный парень, меркантильные мимо. Люблю горы.")
    await telegram_bot.on_profile_text(message)

    assert flow.check.phase == "menu"
    assert flow.check.text_iterations == 1
    assert flow.check.last_text_score == 0
    assert all("Счёт" not in text for text in message.sent)


async def test_flow_name_retries_give_up(store, monkeypatch):
    trainer = _trainer(store)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    flow = trainer.start_profile_flow(1)

    await telegram_bot.on_profile_text(FakeMessage("без возраста"))
    await telegram_bot.on_profile_text(FakeMessage("опять не то"))
    assert flow.check.phase == "name"

    third = FakeMessage("и снова мимо")
    await telegram_bot.on_profile_text(third)
    assert trainer.get_profile_flow(1) is None  # флоу закрыт
    assert any("проверку заново" in text.lower() for text in third.sent)


async def test_flow_survives_restart_in_text_phase(store, monkeypatch):
    trainer = _trainer(store)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    trainer.start_profile_flow(1)
    flow = trainer.get_profile_flow(1)
    trainer.save_flow(flow, name="Саша", age=32, phase="bio")

    # Новый Trainer - как после рестарта процесса: флоу поднимается из базы.
    second = _trainer(store)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", second)
    restored = second.get_profile_flow(1)
    assert restored is not None
    assert restored.check.phase == "bio"
    assert restored.check.name == "Саша"


async def test_begin_closes_profile_flow(store, monkeypatch):
    trainer = _trainer(store)
    monkeypatch.setattr(telegram_bot, "_trainer_instance", trainer)
    trainer.start_profile_flow(1)

    await telegram_bot._begin(FakeMessage("start"), trainer, 1, "first_message/vera")

    assert trainer.get_profile_flow(1) is None
    user_id = store.ensure_user(1)
    assert store.get_active_profile_check(user_id) is None


async def test_completed_profile_adds_bonus_turns(store):
    trainer = _trainer(store)
    flow = trainer.start_profile_flow(1)
    trainer.save_flow(flow, name="Саша", age=32, bio="Люблю горы")
    trainer.close_profile_flow(1, completed=True)

    assert store.has_completed_profile(store.ensure_user(1))

    session = trainer.start_session(1)
    assert session.bonus_turns == PROFILE_BONUS_TURNS
    assert session.player_profile is not None and "Саша" in session.player_profile
    assert session.turns_left == session.scenario.turn_limit + PROFILE_BONUS_TURNS

    # Восстановление из базы: бонус не теряется и не дублируется.
    second = _trainer(store)
    restored = second.get_session(1)
    assert restored is not None
    assert restored.bonus_turns == PROFILE_BONUS_TURNS
    assert restored.turns_left == restored.scenario.turn_limit + PROFILE_BONUS_TURNS


async def test_session_without_profile_has_no_bonus(store):
    trainer = _trainer(store)
    session = trainer.start_session(1)
    assert session.bonus_turns == 0
    assert session.player_profile is None
    assert session.turns_left == session.scenario.turn_limit


# --- отладочный дублик в Telegram ------------------------------------------


class FakeBot:
    """Минимальный Bot для _send_debug_dump: медиагруппа и сообщения."""

    def __init__(self) -> None:
        self.media: list[tuple[int, list]] = []
        self.messages: list[str] = []

    async def send_media_group(self, chat_id: int, media: list) -> None:
        self.media.append((chat_id, media))

    async def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append(text)


async def test_debug_dump_photos_and_split_text():
    bot = FakeBot()
    long_text = "строка про анкету\n" * 800  # ~14К знаков - больше лимита Telegram

    await telegram_bot._send_debug_dump(bot, 42, "Анкета: Саша (32)", long_text, [b"img1", b"img2"])

    assert bot.media and bot.media[0][0] == 42
    assert len(bot.media[0][1]) == 2
    assert bot.media[0][1][0].caption.startswith("Анкета: Саша")
    assert len(bot.messages) > 1
    assert all(len(text) <= telegram_bot.MAX_MESSAGE for text in bot.messages)
    assert "строка про анкету" in "".join(bot.messages)


async def test_debug_dump_without_photos_sends_text_only():
    bot = FakeBot()
    await telegram_bot._send_debug_dump(bot, 7, "капшен", "короткий текст", [])
    assert bot.media == []
    assert bot.messages == ["короткий текст"]


# --- предупреждение о внешнем сервисе ---------------------------------------


def _settings(vision_base_url: str, vision_model: str):
    from bot.config import Settings

    return Settings(
        telegram_bot_token=None,
        telegram_proxy=None,
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
        db_path=TMP_ROOT / "warning.db",
        safety_resources=None,
        vision_api_key="key",
        vision_base_url=vision_base_url,
        vision_model=vision_model,
        smtp_host=None,
        smtp_port=465,
        smtp_user=None,
        smtp_pass=None,
        profile_debug_email=None,
        profile_debug_chat_id=None,
    )


def test_privacy_warning_names_real_provider(store):
    """Провайдер в предупреждении - из настроек: GLM на проде, без OpenRouter."""
    trainer = Trainer(
        DialogueEngine(FakeLLM([])), store, load_scenario(),
        with_faces=False, settings=_settings("https://api.z.ai/api/paas/v4", "glm-4.6v"),
    )
    text = telegram_bot._privacy_warning(trainer)
    assert "GLM, модель glm-4.6v" in text
    assert "OpenRouter" not in text
    assert "Gemini" not in text
    assert "У нас ничего не хранится" in text


def test_privacy_warning_follows_provider_change(store):
    trainer = Trainer(
        DialogueEngine(FakeLLM([])), store, load_scenario(),
        with_faces=False,
        settings=_settings("https://openrouter.ai/api/v1", "google/gemini-2.5-flash-lite"),
    )
    text = telegram_bot._privacy_warning(trainer)
    assert "OpenRouter, модель google/gemini-2.5-flash-lite" in text
