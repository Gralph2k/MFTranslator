"""Telegram-бот на aiogram 3: команды, диалог, разбор, проверка анкеты."""

from __future__ import annotations

import asyncio
import io
import logging
from dataclasses import dataclass, field
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

from .config import Settings, load_settings
from .email_debug import send_debug_email
from .engine import DialogueEngine, DialogueSession
from .faces import emotion_for_state, face_path
from .launcher import clear_pid, write_pid
from .llm import DeepSeekLLM, LLM, parse_json_object
from .heroines import random_heroine, story_scenarios
from .menus import (
    after_finish_menu,
    heroine_menu,
    heroines_menu,
)
from .profile_card import render_profile_cards
from .profile_check import (
    PROFILE_BONUS_TURNS,
    PhotoReview,
    TextReview,
    compress_photo,
    consultant_messages,
    load_config,
    parse_name_age,
    parse_photo_review,
    parse_text_review,
    photo_system_prompt,
    photo_user_prompt,
    player_profile_block,
    render_photo_review,
    render_text_review,
    t,
)
from .prompts import backstory_text, format_transcript, profile_text, rules_text, start_intro
from .safety import CrisisDetected, safety_message
from .scenario import Scenario, ScenarioError, load_scenario
from .state import PersonaState
from .storage import Storage, StoredProfileCheck, StoredSession
from .vision import VisionLLM

log = logging.getLogger(__name__)
router = Router()

MAX_MESSAGE = 4000
# Сколько последних сообщений прошлой переписки персонаж помнит в продолжении.
PREVIOUS_MESSAGES = 12


@dataclass
class ProfileFlow:
    """Активный прогон «Проверки анкеты» в памяти.

    Текст и счётчики живут в базе и переживают рестарт; здесь - только то, что
    в базе не хранится: file_id присланных фото (Telegram держит их у себя,
    мы - принципиально нет) и структурные разборы для финального резюме.
    """

    check: StoredProfileCheck
    photo_ids: list[str] = field(default_factory=list)
    name_retries: int = 0
    text_review: TextReview | None = None
    photo_review: PhotoReview | None = None


class Trainer:
    """Связывает Telegram, движок и хранилище. Держит сессии в памяти."""

    def __init__(
        self,
        engine: DialogueEngine,
        storage: Storage,
        default_scenario: Scenario,
        safety_resources: str | None = None,
        with_faces: bool = True,
        vision: VisionLLM | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.engine = engine
        self.storage = storage
        self.default_scenario = default_scenario
        self.safety_resources = safety_resources
        # Фото - часть сценария; флаг нужен тестам, чтобы не звать Telegram.
        self.with_faces = with_faces
        self.sessions: dict[int, DialogueSession] = {}
        self.profile_flows: dict[int, ProfileFlow] = {}
        self._scenarios: dict[str, Scenario] = {default_scenario.id: default_scenario}
        # Telegram хранит загруженный файл у себя: второй раз шлём по file_id,
        # иначе каждый ход тратит время на загрузку полумегабайтной картинки.
        self.face_file_ids: dict[str, str] = {}
        # Vision для оценки фото анкеты; None - ключ не настроен, фаза фото
        # вежливо откажет вместо падения.
        self.vision = vision
        # Для отладочного почтового дублика (включается PROFILE_DEBUG_EMAIL).
        self.settings = settings
        # Замок на пользователя: aiogram обрабатывает апдейты конкурентно
        # (start_polling с handle_as_tasks=True), а ходы одного диалога должны
        # идти по порядку - иначе реплики перемешаются, а разбор задвоится.
        self._user_locks: dict[int, asyncio.Lock] = {}

    def user_lock(self, telegram_id: int) -> asyncio.Lock:
        lock = self._user_locks.get(telegram_id)
        if lock is None:
            lock = asyncio.Lock()
            self._user_locks[telegram_id] = lock
        return lock

    def scenario_by_id(self, scenario_id: str) -> Scenario:
        if scenario_id not in self._scenarios:
            self._scenarios[scenario_id] = load_scenario(scenario_id)
        return self._scenarios[scenario_id]

    def get_session(self, telegram_id: int) -> DialogueSession | None:
        """Берёт сессию из памяти или поднимает незакрытую из базы."""
        if telegram_id in self.sessions:
            return self.sessions[telegram_id]

        user_id = self.storage.ensure_user(telegram_id)
        stored = self.storage.get_active_session(user_id)
        if stored is None:
            return None

        scenario = self.scenario_by_id(stored.scenario)
        session = DialogueSession(
            scenario=scenario,
            state=PersonaState.from_mapping(stored.state),
            history=stored.history,
            user_turns=stored.user_turns,
            ended_by_persona=stored.ended_by_persona,
            finished=stored.finished,
            session_id=stored.id,
            previous=self._previous_chat(user_id, scenario),
        )
        # Бонус за заполненную анкету считаем заново: поле не в базе, а факт
        # «анкета заполнена» - в базе. Иначе после рестарта лимит скакнул бы назад.
        self._apply_profile(user_id, session)
        self.sessions[telegram_id] = session
        return session

    def last_heroine(self, telegram_id: int) -> str | None:
        """Героиня последней сессии - чтобы `/start` не выдавал её же подряд."""
        user_id = self.storage.ensure_user(telegram_id)
        stored = self.storage.last_session(user_id)
        if stored is None:
            return None
        try:
            scenario = self.scenario_by_id(stored.scenario)
        except ScenarioError:
            return None
        return scenario.heroine or None

    def start_session(self, telegram_id: int, scenario_id: str | None = None) -> DialogueSession:
        user_id = self.storage.ensure_user(telegram_id)
        old = self.storage.get_active_session(user_id)
        if old is not None:
            self.storage.save_session(
                old.id,
                old.state,
                old.history,
                old.user_turns,
                finished=True,
                ended_by_persona=old.ended_by_persona,
            )

        scenario = self.default_scenario if scenario_id is None else self.scenario_by_id(scenario_id)
        session = self.engine.start(scenario, self._previous_chat(user_id, scenario))
        self._apply_profile(user_id, session)
        session.session_id = self.storage.create_session(
            user_id, scenario.id, session.state.to_mapping(), session.history
        )
        self.sessions[telegram_id] = session
        return session

    def _apply_profile(self, user_id: int, session: DialogueSession) -> None:
        """Заполненная анкета: +3 хода и выжимка (текст + фото) для промпта героини."""
        profile = self.storage.last_completed_profile(user_id)
        if profile is None:
            return
        session.bonus_turns = PROFILE_BONUS_TURNS
        session.player_profile = player_profile_block(
            profile.name, profile.age, profile.bio, profile.photo_contents
        )

    def _previous_chat(self, user_id: int, scenario: Scenario) -> list[dict[str, str]]:
        """Переписка из сценария-продолжения: последняя удачная попытка или канон.

        Реальную переписку берём, только если она доиграна и персонаж не сбежал:
        после красной линии звонок идёт по канону, без отсылок к тому разговору.
        """
        if not scenario.continues:
            return list(scenario.canon_history)

        stored = self.storage.last_session_for(user_id, scenario.continues)
        if stored is None or not self._is_completed_chat(stored):
            return list(scenario.canon_history)

        return stored.history[-PREVIOUS_MESSAGES:]

    def _is_completed_chat(self, stored: StoredSession) -> bool:
        """Доигранная переписка: есть ходы, есть разбор и она не оборвалась."""
        if stored.ended_by_persona or stored.user_turns == 0 or not stored.history:
            return False
        overview = self.storage.get_overview(stored.id)
        return overview is not None and bool(overview.debrief)

    def persist(self, telegram_id: int, session: DialogueSession) -> None:
        if session.session_id is None:
            return
        self.storage.save_session(
            session.session_id,
            session.state.to_mapping(),
            session.history,
            session.user_turns,
            session.finished,
            ended_by_persona=session.ended_by_persona,
        )

    # --- «Проверка анкеты» --------------------------------------------------

    def get_profile_flow(self, telegram_id: int) -> ProfileFlow | None:
        """Флоу из памяти или, после рестарта бота, из базы (кроме фото-фазы)."""
        flow = self.profile_flows.get(telegram_id)
        if flow is not None:
            return flow if flow.check.is_active else None

        user_id = self.storage.ensure_user(telegram_id)
        stored = self.storage.get_active_profile_check(user_id)
        if stored is None:
            return None
        flow = ProfileFlow(check=stored)
        self.profile_flows[telegram_id] = flow
        return flow

    def start_profile_flow(self, telegram_id: int) -> ProfileFlow:
        user_id = self.storage.ensure_user(telegram_id)
        self.storage.create_profile_check(user_id)
        stored = self.storage.get_active_profile_check(user_id)
        if stored is None:  # не должно случиться: только что создали
            raise RuntimeError("profile_check не создался")
        flow = ProfileFlow(check=stored)
        self.profile_flows[telegram_id] = flow
        return flow

    def save_flow(self, flow: ProfileFlow, **fields: Any) -> None:
        """Пишет поля в базу и синхронизирует копию в памяти."""
        self.storage.update_profile_check(flow.check.id, **fields)
        for key, value in fields.items():
            setattr(flow.check, key, value)

    def close_profile_flow(self, telegram_id: int, completed: bool = False) -> None:
        """Закрывает флоу - завершением, отменой или уходом в сценарий."""
        flow = self.profile_flows.pop(telegram_id, None)
        check = flow.check if flow is not None else None
        if check is None:
            user_id = self.storage.ensure_user(telegram_id)
            stored = self.storage.get_active_profile_check(user_id)
            check = stored
        if check is None:
            return
        self.storage.update_profile_check(
            check.id,
            phase="done" if completed else "abandoned",
            completed=int(completed),
        )

    def profile_flow_active(self, telegram_id: int) -> bool:
        return self.get_profile_flow(telegram_id) is not None


# Единственный экземпляр Trainer на процесс: хендлеры aiogram статичны.
_trainer_instance: Trainer | None = None


def _trainer(message: Message) -> Trainer:
    if _trainer_instance is None:
        raise RuntimeError("Trainer не инициализирован")
    return _trainer_instance


async def _send_long(
    message: Message, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    """Telegram режет сообщения на 4096 символах - делим по строкам.

    Клавиатура цепляется к последнему куску.
    """
    while text:
        if len(text) <= MAX_MESSAGE:
            await message.answer(text, reply_markup=reply_markup)
            return
        cut = text.rfind("\n", 0, MAX_MESSAGE)
        if cut < MAX_MESSAGE // 2:
            cut = MAX_MESSAGE
        await message.answer(text[:cut])
        text = text[cut:].lstrip("\n")


async def _send_face(message: Message, trainer: "Trainer", session: Any, caption: str) -> bool:
    """Лицо под текущее настроение. False - если картинки нет, текст отправит вызывающий.

    В переписке и на созвоне лицо не показываем: там эмоция читается только
    по тексту и смайликам, иначе рушится сама сцена.
    """
    if not trainer.with_faces or not session.scenario.shows_face:
        return False

    emotion = emotion_for_state(session.state)
    # Кеш по паре «сценарий:эмоция»: у каждой героини своё лицо.
    key = f"{session.scenario.id}:{emotion}"
    cached = trainer.face_file_ids.get(key)
    if cached is not None:
        await message.answer_photo(cached, caption=caption[:1024])
        return True

    path = face_path(emotion, session.scenario.faces_dir)
    if path is None:
        return False

    sent = await message.answer_photo(FSInputFile(path), caption=caption[:1024])
    if sent.photo:
        trainer.face_file_ids[key] = sent.photo[-1].file_id
    return True


async def _send_call_screen(target: Message, scenario: Scenario) -> None:
    """Экран исходящего звонка: единственная картинка сцены-созвона.

    Рисуется кодом поверх фото (имя, «мобильный», «Вызов…», кнопка сброса):
    текст на сгенерированных картинках превращается в кашу, поэтому UI - PIL.
    """
    from .call_screen import render_call_screen

    path = render_call_screen(scenario)
    if path is None:
        return
    await target.answer_photo(FSInputFile(path))


async def _send_profile(
    target: Message,
    trainer: "Trainer",
    scenario: Scenario,
) -> None:
    """Карточка анкеты как в приложении: UI рисуется кодом поверх фото.

    Подписи у фото разные: работа и «о себе», интересы, чего ищет. Так текст
    не повторяется отдельным блоком «О себе». Фото анкеты лежат в папке
    сценария с именами `profile_*` - `faces.py` их не трогает.
    """
    profile = scenario.profile
    if profile is None:
        return

    photos = [
        (scenario.faces_dir / name, name)
        for name in profile.photos
        if (scenario.faces_dir / name).is_file()
    ]
    cards = render_profile_cards(scenario) if trainer.with_faces else []
    captions = profile.captions

    def photo_caption(index: int) -> str | None:
        if index >= len(photos):
            return None
        return captions.get(photos[index][1]) or None

    if len(cards) == 1:
        # Одно фото - не альбом: answer_media_group требует хотя бы два кадра.
        await target.answer_photo(
            FSInputFile(cards[0]), caption=photo_caption(0)
        )
    elif cards:
        media = [
            InputMediaPhoto(
                media=FSInputFile(card),
                caption=photo_caption(index),
            )
            for index, card in enumerate(cards)
        ]
        await target.answer_media_group(media)
    else:
        await _send_long(target, profile_text(scenario))


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    trainer = _trainer(message)
    # /start - лендинг бота: что здесь можно и зачем. Сценарий игрок выбирает сам.
    async with trainer.user_lock(message.from_user.id):
        trainer.close_profile_flow(message.from_user.id)
    await _send_long(message, start_intro(), reply_markup=heroines_menu())


async def _begin(
    target: Message,
    trainer: "Trainer",
    telegram_id: int,
    scenario_id: str | None = None,
) -> None:
    """Начинает сценарий: сначала правила, потом описание и картинки."""
    async with trainer.user_lock(telegram_id):
        # Сценарий забирает тексты себе: активная проверка анкеты закрывается,
        # иначе её флоу-хендлер перехватывал бы реплики диалога.
        trainer.close_profile_flow(telegram_id)
        try:
            session = trainer.start_session(telegram_id, scenario_id)
        except ScenarioError:
            await target.answer("Такого сценария нет. /menu - список.")
            return

        trainer.persist(telegram_id, session)
        # 1. «Это тренажёр», как играть и команды - без подсказки на первый ход.
        await _send_long(target, rules_text(session.scenario))

        if session.scenario.is_correspondence:
            # 2. Описание сценария, 3. её анкета - подписи с «о себе» разнесены по фото.
            await _send_long(target, backstory_text(session.scenario))
            # 3. Анкета с картинками и подписями. «Ход твой» уже сказано в описании,
            #    поэтому отдельного сообщения с подсказкой нет.
            await _send_profile(target, trainer, session.scenario)
        elif session.scenario.is_call:
            # 2. Описание сцены, 3. экран исходящего звонка, 4. её «алло».
            await _send_long(target, backstory_text(session.scenario))
            await _send_call_screen(target, session.scenario)
            if session.scenario.opening.strip():
                await target.answer(session.scenario.opening)
        else:
            # 2. Описание сцены, 3. первая реплика персонажа приходит с её лицом.
            await _send_long(target, backstory_text(session.scenario))
            opening = session.scenario.opening
            if not await _send_face(target, trainer, session, opening):
                await target.answer(opening)


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("Выбери героиню:", reply_markup=heroines_menu())


@router.message(Command("scenario"))
async def cmd_scenario(message: Message) -> None:
    trainer = _trainer(message)
    parts = (message.text or "").split(maxsplit=1)

    if len(parts) == 1:
        await message.answer("Выбери героиню:", reply_markup=heroines_menu())
        return

    scenario_id = parts[1].strip()
    try:
        scenario = trainer.scenario_by_id(scenario_id)
    except ScenarioError:
        await message.answer("Такого сценария нет. /menu - список героинь.")
        return
    if not scenario.enabled:
        await message.answer("Этот сценарий выключен. /menu - выбрать героиню.")
        return
    await _begin(message, trainer, message.from_user.id, scenario_id)


@router.message(Command("restart"))
async def cmd_restart(message: Message) -> None:
    trainer = _trainer(message)
    current = trainer.get_session(message.from_user.id)
    # Активную сцену повторяем; выключенную или отсутствующую - меняем на случайную
    # героиню, чтобы /restart не запускал сценарий «на будущее».
    if current is not None and current.scenario.enabled:
        scenario_id = current.scenario.id
    else:
        last = trainer.last_heroine(message.from_user.id)
        scenario_id = random_heroine(last).first_scenario
    await _begin(message, trainer, message.from_user.id, scenario_id)


@router.message(Command("finish"))
async def cmd_finish(message: Message) -> None:
    trainer = _trainer(message)
    async with trainer.user_lock(message.from_user.id):
        session = trainer.get_session(message.from_user.id)
        if session is None or session.user_turns == 0:
            await message.answer("Разбирать пока нечего: сначала поговори с ней. /start")
            return
        if session.debrief_sent:
            await message.answer("Разбор уже был выше. Новый разговор - /restart.")
            return

        await _deliver_debrief(message, trainer, message.from_user.id, session)


async def _deliver_debrief(
    target: Message,
    trainer: "Trainer",
    telegram_id: int,
    session: DialogueSession,
) -> None:
    if session.debrief_sent:
        # Второй разбор того же разговора не тратит запрос и не дублирует текст.
        # Страховка на случай гонки апдейтов сверх замка пользователя.
        return
    await target.answer("Секунду, собираю разбор...")
    try:
        debrief = await trainer.engine.debrief(session)
    except Exception as exc:
        log.exception("debrief failed")
        await target.answer(f"Разбор не получился: {exc}. Попробуй ещё раз позже.")
        return

    text = debrief.render(session.scenario)
    trainer.persist(telegram_id, session)
    if session.session_id is not None:
        trainer.storage.save_debrief(session.session_id, text)
    session.debrief_sent = True
    # Отчёт владельцу: переписка и разбор каждого завершённого сценария.
    _notify_owner(
        target.bot,
        trainer,
        _scenario_report(telegram_id, session, text),
    )
    await _send_face(target, trainer, session, "Так она закончила разговор.")
    await _send_long(target, text)
    await target.answer(
        "Что дальше?", reply_markup=after_finish_menu(session.scenario.id)
    )


def _scenario_report(
    telegram_id: int, session: DialogueSession, debrief_text: str
) -> str:
    """Текст отчёта о завершённом сценарии: кто, где, переписка, разбор."""
    scenario = session.scenario
    header = (
        f"Сценарий: {scenario.title} ({scenario.id})\n"
        f"Игрок: tg {telegram_id}\n"
    )
    transcript = format_transcript(session.history, scenario.persona.name)
    return f"{header}\nПереписка:\n{transcript}\n\nРазбор:\n{debrief_text}"


# --- «Проверка анкеты»: флоу ----------------------------------------------
# Хендлеры регистрируются ДО on_text: иначе тексты анкеты уйдут в диалог.
# Команды (/check, /cancel) зарегистрированы ещё раньше и перехватываются
# своими Command-фильтрами.


def _review_keyboard(rework_allowed: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if rework_allowed:
        rows.append(
            [InlineKeyboardButton(text="Доработать текст", callback_data="profile:rework")]
        )
    rows.append([InlineKeyboardButton(text="Перейти к фото", callback_data="profile:to_photos")])
    rows.append([InlineKeyboardButton(text="Пропустить фото", callback_data="profile:skip_photos")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _photos_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оценить фото", callback_data="profile:evaluate")],
            [InlineKeyboardButton(text="Завершить без фото", callback_data="profile:finish")],
        ]
    )


def _after_photo_review_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Прислать другие фото", callback_data="profile:to_photos")],
            [InlineKeyboardButton(text="Завершить", callback_data="profile:finish")],
        ]
    )


def _finish_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Завершить", callback_data="profile:finish")]]
    )


def _vision_provider_label(trainer: "Trainer") -> str:
    """Куда на самом деле уходят фото: имя провайдера и модель из настроек.

    Текст предупреждения не должен врать при смене VISION_*: провайдера
    вычисляем из base_url, а не пишем руками в конфиг.
    """
    settings = trainer.settings
    if settings is None or not settings.vision_base_url:
        return "внешняя нейросеть"
    host = settings.vision_base_url.split("//")[-1].split("/")[0].lower()
    if "z.ai" in host or "bigmodel" in host:
        provider = "GLM"
    elif "openrouter" in host:
        provider = "OpenRouter"
    else:
        provider = host
    return f"{provider}, модель {settings.vision_model}"


def _privacy_warning(trainer: "Trainer") -> str:
    """Предупреждение перед фото: внешний сервис анализа и что мы ничего не храним.

    Отладочный дублик разработчику в тексте не упоминаем (решение владельца:
    не пугать пользователей) - он уходит тихо, сам текст предупреждения не меняет.
    """
    return load_config()["privacy_warning"].format(provider=_vision_provider_label(trainer))


async def _run_check(target: Message, trainer: "Trainer", telegram_id: int) -> None:
    """/check: новый прогон или возобновление после рестарта. Лок уже взят."""
    flow = trainer.get_profile_flow(telegram_id)
    if flow is None:
        flow = trainer.start_profile_flow(telegram_id)
        await target.answer(t("ask_name"))
        return

    phase = flow.check.phase
    if phase == "name":
        await target.answer(t("ask_name"))
    elif phase == "bio":
        await target.answer(t("ask_bio"))
    elif phase == "menu":
        cfg = load_config()
        await target.answer(
            t("flow_active_hint"),
            reply_markup=_review_keyboard(
                flow.check.text_iterations < cfg["max_text_iterations"]
            ),
        )
    else:  # photos
        await target.answer(t("photo_phase_reset", max=cfg_max_photos()))
        await target.answer(t("ask_photos", max=cfg_max_photos()), reply_markup=_photos_keyboard())


def cfg_max_photos() -> int:
    return int(load_config()["max_photos"])


@router.message(Command("check"))
async def cmd_check(message: Message) -> None:
    trainer = _trainer(message)
    async with trainer.user_lock(message.from_user.id):
        await _run_check(message, trainer, message.from_user.id)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message) -> None:
    trainer = _trainer(message)
    async with trainer.user_lock(message.from_user.id):
        had_flow = trainer.get_profile_flow(message.from_user.id) is not None
        trainer.close_profile_flow(message.from_user.id)
    if had_flow:
        await message.answer(t("cancel"))


async def _review_text(
    target: Message,
    trainer: "Trainer",
    telegram_id: int,
    flow: ProfileFlow,
    bio: str,
) -> None:
    """Разбор текста анкеты: deepseek, счёт считает код. Лок уже взят."""
    cfg = load_config()
    if len(bio) > cfg["max_length"]:
        await target.answer(t("bio_too_long", length=len(bio), max=cfg["max_length"]))
        return

    trainer.save_flow(flow, bio=bio)
    await target.answer(t("analyzing_text"))
    try:
        raw = await trainer.engine.llm.complete(
            consultant_messages(
                flow.check.name, flow.check.age or 0, bio,
                prev_rewrite=flow.check.last_rewrite,
            ),
            json_mode=True,
            temperature=0.3,
        )
        review = parse_text_review(parse_json_object(raw))
    except Exception as exc:
        log.exception("разбор анкеты не получился")
        await target.answer(f"Разбор не получился: {exc}. Пришли текст ещё раз.")
        return

    rendered = render_text_review(review)
    flow.text_review = review
    trainer.save_flow(
        flow,
        text_iterations=flow.check.text_iterations + 1,
        last_text_score=review.score,
        last_text_verdict=rendered,
        last_rewrite=review.rewrite_after,
        phase="menu",
    )
    await _send_long(target, rendered)
    # Отладочный дублик на время тестирования: анкета и разбор владельцу
    # сразу, не дожидаясь сценария или оценки фото. Пользователю об этом
    # не сообщаем (решение владельца на период тестирования).
    bot = getattr(target, "bot", None)
    if bot is not None:
        _schedule_debug_dump(bot, trainer, telegram_id, flow, [])
    rework_allowed = flow.check.text_iterations < cfg["max_text_iterations"]
    if not rework_allowed:
        await target.answer(t("text_iterations_over"))
    await target.answer("Что дальше?", reply_markup=_review_keyboard(rework_allowed))


async def _download_photos(bot: Bot, file_ids: list[str]) -> list[bytes]:
    """Скачивает и сжимает параллельно; битые кадры молча пропускает."""

    async def fetch(file_id: str) -> bytes | None:
        try:
            file = await bot.get_file(file_id)
            if file.file_path is None:
                return None
            buffer = io.BytesIO()
            await bot.download_file(file.file_path, destination=buffer)
            return compress_photo(buffer.getvalue())
        except Exception:
            log.exception("не скачал фото")
            return None

    results = await asyncio.gather(*(fetch(file_id) for file_id in file_ids))
    return [item for item in results if item is not None]


async def _send_debug_dump(
    bot: Bot,
    chat_id: int,
    caption: str,
    text: str,
    images: list[bytes],
) -> None:
    """Отладочный дублик владельцу в Telegram: фото альбомом + переписка текстом.

    Замена почтовому дублику: хостер режет исходящие SMTP-порты (465/587),
    а Telegram-канал у бота уже есть.
    """
    if images:
        media = [
            InputMediaPhoto(
                media=BufferedInputFile(image, filename=f"photo_{index + 1}.jpg"),
                caption=caption[:1024] if index == 0 else None,
            )
            for index, image in enumerate(images[:10])
        ]
        await bot.send_media_group(chat_id, media=media)
    # Длинный текст режем по строкам, как _send_long, но через bot.send_message.
    while text:
        chunk, text = text[:MAX_MESSAGE], text[MAX_MESSAGE:]
        if text:
            cut = chunk.rfind("\n")
            if cut > MAX_MESSAGE // 2:
                chunk, text = chunk[:cut], chunk[cut:] + text
        await bot.send_message(chat_id, chunk.strip())


def _schedule_debug_dump(
    bot: Bot,
    trainer: "Trainer",
    telegram_id: int,
    flow: ProfileFlow,
    images: list[bytes],
) -> None:
    """Планирует отправку дублика в фоне: чат владельца или почта, что включено."""
    settings = trainer.settings
    if settings is None:
        return
    check = flow.check
    caption = f"Анкета: {check.name or '-'} ({check.age or '?'}) - tg {telegram_id}"
    body = (
        f"telegram_id: {telegram_id}\n"
        f"Имя: {check.name}\nВозраст: {check.age}\n"
        f"Разборов текста: {check.text_iterations}, оценок фото: {check.photo_reviews}\n\n"
        f"Текст анкеты:\n{check.bio or '-'}\n\n"
        f"Последний разбор текста:\n{check.last_text_verdict or '-'}\n\n"
        f"Последний разбор фото:\n{check.last_photo_verdict or '-'}"
    )
    if settings.debug_chat_enabled and settings.profile_debug_chat_id is not None:
        async def _to_chat() -> None:
            try:
                await _send_debug_dump(
                    bot, settings.profile_debug_chat_id, caption, body, images
                )
            except Exception:
                log.exception("отладочный дублик в Telegram не ушёл")

        asyncio.create_task(_to_chat())
        return
    if settings.debug_email_enabled:
        send_debug_email(
            settings,
            caption,
            body,
            [(f"photo_{index + 1}.jpg", image) for index, image in enumerate(images)],
        )


def _notify_owner(bot: Bot, trainer: "Trainer", text: str) -> None:
    """Отчёт владельцу о завершённом сценарии: переписка и разбор.

    Каналы независимы: Telegram (пока SMTP на VPS закрыт хостером - основной)
    и почта, если SMTP_* и PROFILE_DEBUG_EMAIL настроены и доступны.
    """
    settings = trainer.settings
    if settings is None:
        return
    subject = text.splitlines()[0][:100] if text else "Разбор сценария"
    if settings.debug_chat_enabled and settings.profile_debug_chat_id is not None:
        chat_id = settings.profile_debug_chat_id

        async def _to_chat() -> None:
            try:
                await _send_debug_dump(bot, chat_id, subject, text, [])
            except Exception:
                log.exception("отчёт о сценарии в Telegram не ушёл")

        asyncio.create_task(_to_chat())
    if settings.debug_email_enabled:
        send_debug_email(settings, subject, text, [])


async def _evaluate_photos(
    target: Message,
    trainer: "Trainer",
    telegram_id: int,
    flow: ProfileFlow,
) -> None:
    """Оценка набора фото одним vision-вызовом. Лок уже взят."""
    cfg = load_config()
    if not flow.photo_ids:
        await target.answer(t("photo_empty"))
        return
    if trainer.vision is None:
        await target.answer(t("photo_unavailable"), reply_markup=_finish_keyboard())
        return
    if flow.check.photo_reviews >= cfg["max_photo_reviews"]:
        await _finish_flow(target, trainer, telegram_id, flow)
        return

    await target.answer(t("photo_analyzing"))
    bot = target.bot
    if bot is None:
        return
    images = await _download_photos(bot, flow.photo_ids)
    if not images:
        await target.answer("Не получилось скачать фотографии. Пришли ещё раз.")
        return

    try:
        data = await trainer.vision.review_photos(
            photo_system_prompt(),
            photo_user_prompt(flow.check.name, flow.check.age),
            images,
        )
        review = parse_photo_review(data, expected=len(images))
    except Exception as exc:
        log.exception("оценка фото не получилась")
        await target.answer(f"Не получилось оценить фото: {exc}. Попробуй ещё раз.")
        return

    rendered = render_photo_review(review)
    flow.photo_review = review
    trainer.save_flow(
        flow,
        photo_reviews=flow.check.photo_reviews + 1,
        last_photo_verdict=rendered,
        photo_contents=review.contents,
    )
    await _send_long(target, rendered)
    # Отладочный дублик на время тестирования: фото и их разбор владельцу
    # сразу после разбора, не дожидаясь сценария. Fire-and-forget: доставка
    # не задерживает ответ. Пользователю об этом не сообщаем.
    _schedule_debug_dump(bot, trainer, telegram_id, flow, images)
    if flow.check.photo_reviews >= cfg["max_photo_reviews"]:
        await target.answer(t("photo_review_limit", max=cfg["max_photo_reviews"]))
        await _finish_flow(target, trainer, telegram_id, flow)
        return
    await target.answer("Что дальше?", reply_markup=_after_photo_review_keyboard())


async def _finish_flow(
    target: Message,
    trainer: "Trainer",
    telegram_id: int,
    flow: ProfileFlow,
) -> None:
    """Меню героинь после проверки анкеты. Лок уже взят."""
    completed = bool(flow.check.bio.strip())
    trainer.close_profile_flow(telegram_id, completed=completed)
    await target.answer("Выбери героиню:", reply_markup=heroines_menu())


async def _handle_photo_batch(
    trigger: Message,
    trainer: "Trainer",
    messages: list[Message],
) -> None:
    """Батч фото (альбом целиком или одиночное): копим или оцениваем. Лок берём здесь."""
    telegram_id = trigger.from_user.id
    async with trainer.user_lock(telegram_id):
        flow = trainer.get_profile_flow(telegram_id)
        if flow is None or flow.check.phase != "photos":
            return

        max_photos = cfg_max_photos()
        fresh = [m.photo[-1].file_id for m in messages if m.photo]
        if len(fresh) > max_photos:
            await trigger.answer(t("album_extra", max=max_photos))
            fresh = fresh[:max_photos]

        room = max_photos - len(flow.photo_ids)
        taken = fresh[:room]
        if not taken:
            await trigger.answer(t("photos_full", max=max_photos), reply_markup=_photos_keyboard())
            return
        flow.photo_ids.extend(taken)
        count = len(flow.photo_ids)

        # Альбом - полный комплект, 4-е одиночное фото - потолок: оцениваем сразу.
        if len(messages) > 1 or count >= max_photos:
            await _evaluate_photos(trigger, trainer, telegram_id, flow)
            return
        await trigger.answer(
            t("photo_more_coming", count=count, max=max_photos),
            reply_markup=_photos_keyboard(),
        )


class _PhotoCollector:
    """Собирает альбом из параллельных апдейтов с одним media_group_id.

    Замок здесь не берём принципиально: апдейты альбома приходят параллельными
    тасками, и первый, удерживающий лок, не дал бы буферу наполниться. Лок
    берёт _handle_photo_batch, когда батч уже собран.
    """

    def __init__(self) -> None:
        self._groups: dict[str, list[Message]] = {}
        self._timers: dict[str, asyncio.Task] = {}
        self._done: set[str] = set()

    def is_done(self, group_id: str) -> bool:
        return group_id in self._done

    def add(self, group_id: str, message: Message) -> None:
        group = self._groups.setdefault(group_id, [])
        if len(group) < 10:  # альбом Telegram длиннее 10 не бывает
            group.append(message)
        timer = self._timers.get(group_id)
        if timer is not None:
            timer.cancel()
        self._timers[group_id] = asyncio.create_task(self._flush(group_id))

    async def _flush(self, group_id: str) -> None:
        await asyncio.sleep(1.2)
        messages = self._groups.pop(group_id, [])
        self._timers.pop(group_id, None)
        self._done.add(group_id)
        if not messages:
            return
        trainer = _trainer_instance
        if trainer is None:
            return
        await _handle_photo_batch(messages[0], trainer, messages)


_collector = _PhotoCollector()


@router.message(F.photo)
async def on_photo(message: Message) -> None:
    trainer = _trainer(message)
    if message.photo is None:
        return
    # Фото вне «Проверки анкеты» бот игнорирует - как и до неё.
    flow = trainer.get_profile_flow(message.from_user.id)
    if flow is None:
        return
    if flow.check.phase != "photos":
        # На фазах имени и текста фото молча ждёт своего этапа; в «menu»
        # подсказываем кнопки - разбор уже есть, кнопки под ним.
        if flow.check.phase == "menu":
            await message.answer(t("flow_active_hint"))
        return

    group_id = message.media_group_id
    if group_id:
        if _collector.is_done(group_id):
            return  # опоздавший кадр уже обработанного альбома
        _collector.add(group_id, message)
        return
    await _handle_photo_batch(message, trainer, [message])


async def _profile_text_filter(message: Message) -> bool:
    """Текст принадлежит флоу анкеты, а не диалогу с героиней.

    Команды отсекаем: их разбирают Command-хендлеры выше по цепочке,
    а неизвестное «/что-то» не должно попадать в текст анкеты.
    """
    trainer = _trainer_instance
    if trainer is None or message.from_user is None:
        return False
    text = message.text or ""
    if not text.strip() or text.startswith("/"):
        return False
    return trainer.profile_flow_active(message.from_user.id)


@router.message(_profile_text_filter)
async def on_profile_text(message: Message) -> None:
    trainer = _trainer(message)
    text = (message.text or "").strip()
    async with trainer.user_lock(message.from_user.id):
        flow = trainer.get_profile_flow(message.from_user.id)
        if flow is None:
            return

        phase = flow.check.phase
        if phase == "name":
            parsed = parse_name_age(text, *load_config()["age_range"])
            if parsed is None:
                flow.name_retries += 1
                if flow.name_retries >= 3:
                    trainer.close_profile_flow(message.from_user.id)
                    await message.answer(t("name_give_up"))
                    return
                await message.answer(t("name_retry"))
                return
            name, age = parsed
            trainer.save_flow(flow, name=name, age=age, phase="bio")
            await message.answer(t("ask_bio"))
            return

        if phase == "bio":
            await _review_text(message, trainer, message.from_user.id, flow, text)
            return

        # menu / photos: текст не ждём, подсказываем кнопки
        await message.answer(t("flow_active_hint"))


@router.message(F.text)
async def on_text(message: Message) -> None:
    trainer = _trainer(message)
    text = (message.text or "").strip()
    if not text:
        return

    # Замок держим на весь ход, включая разбор: быстрые сообщения одного
    # пользователя обрабатываются по порядку и не дублируют разбор.
    async with trainer.user_lock(message.from_user.id):
        session = trainer.get_session(message.from_user.id)
        if session is None:
            await message.answer("Диалог ещё не начат. /start")
            return
        if session.is_over:
            await message.answer(
                "Этот разговор закончен. Новый - /restart или /menu."
            )
            return

        try:
            reply = await trainer.engine.reply(session, text)
        except CrisisDetected:
            session.finished = True
            trainer.persist(message.from_user.id, session)
            await _send_long(message, safety_message(trainer.safety_resources))
            return
        except Exception as exc:
            log.exception("reply failed")
            await message.answer(
                f"Не получилось ответить: {exc}. Попробуй отправить сообщение ещё раз."
            )
            return

        trainer.persist(message.from_user.id, session)
        # Имя перед репликой не пишем: в переписке сообщение и так от неё.
        reply_text = reply
        if len(reply_text) > 1024:
            # Не влезает в подпись к фото - шлём картинку и текст отдельно.
            await _send_face(message, trainer, session, "")
            await _send_long(message, reply_text)
        elif not await _send_face(message, trainer, session, reply_text):
            await _send_long(message, reply_text)

        if session.ended_by_persona:
            # Красная линия: она закончила разговор. Разбор объяснит, на каком ходу.
            if session.scenario.is_call:
                farewell = "Она положила трубку. Сейчас будет разбор - почему."
            elif session.scenario.is_correspondence:
                farewell = "Она закрыла переписку. Сейчас будет разбор - почему."
            else:
                farewell = "Она ушла от разговора. Сейчас будет разбор - почему."
            await message.answer(farewell)

        if session.is_over:
            # Сюжет закончился (кончились ходы или персонаж закрыл тему) - разбираем сразу.
            await _deliver_debrief(message, trainer, message.from_user.id, session)


@router.callback_query(F.data.startswith("menu:"))
async def on_menu(callback: CallbackQuery) -> None:
    trainer = _trainer(callback.message)
    await callback.answer()

    action = (callback.data or "").split(":", 1)[1]
    if action == "main":
        await callback.message.answer("Главное меню:", reply_markup=heroines_menu())
        return
    if action == "list":
        await callback.message.answer("Выбери героиню:", reply_markup=heroines_menu())
        return
    if action.startswith("heroine:"):
        heroine_id = action.split(":", 1)[1]
        await callback.message.answer(
            "Выбери сцену:", reply_markup=heroine_menu(heroine_id)
        )
        return
    if action.startswith("start:"):
        await _begin(
            callback.message, trainer, callback.from_user.id, action.split(":", 1)[1]
        )


@router.callback_query(F.data.startswith("profile:"))
async def on_profile(callback: CallbackQuery) -> None:
    trainer = _trainer(callback.message)
    await callback.answer()
    target = callback.message
    telegram_id = callback.from_user.id
    action = (callback.data or "").split(":", 1)[1]

    if action == "start":
        async with trainer.user_lock(telegram_id):
            await _run_check(target, trainer, telegram_id)
        return

    async with trainer.user_lock(telegram_id):
        flow = trainer.get_profile_flow(telegram_id)
        if flow is None:
            return
        if action == "rework":
            if flow.check.phase != "menu":
                return
            trainer.save_flow(flow, phase="bio")
            await target.answer(t("rework_hint"))
        elif action == "to_photos":
            if flow.check.phase not in ("menu", "photos"):
                return
            flow.photo_ids = []
            trainer.save_flow(flow, phase="photos")
            await _send_long(target, _privacy_warning(trainer))
            await target.answer(
                t("ask_photos", max=cfg_max_photos()), reply_markup=_photos_keyboard()
            )
        elif action == "evaluate":
            if flow.check.phase == "photos":
                await _evaluate_photos(target, trainer, telegram_id, flow)
        elif action in ("skip_photos", "finish"):
            await _finish_flow(target, trainer, telegram_id, flow)


async def _run(settings: Settings, scenario: Scenario) -> None:
    if not settings.has_telegram:
        raise SystemExit("Нет TELEGRAM_BOT_TOKEN: создай бота у @BotFather и заполни .env")
    if not settings.has_llm:
        raise SystemExit("Нет DEEPSEEK_API_KEY: без модели бот не ответит ни слова")

    # Telegram в РФ часто недоступен напрямую: при необходимости задаём прокси
    # в TELEGRAM_PROXY (http://... или socks5://...).
    session = (
        AiohttpSession(proxy=settings.telegram_proxy)
        if settings.telegram_proxy
        else None
    )
    bot = Bot(token=settings.telegram_bot_token or "", session=session)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)

    llm: LLM = DeepSeekLLM(
        api_key=settings.deepseek_api_key or "",
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
    )
    # Vision для «Проверки анкеты»: без ключа фаза фото вежливо откажет.
    vision = (
        VisionLLM(
            api_key=settings.vision_api_key or "",
            base_url=settings.vision_base_url,
            model=settings.vision_model,
        )
        if settings.has_vision
        else None
    )
    storage = Storage(settings.db_path)
    trainer = Trainer(
        DialogueEngine(llm),
        storage,
        scenario,
        settings.safety_resources,
        vision=vision,
        settings=settings,
    )
    global _trainer_instance
    _trainer_instance = trainer
    # PID-файл - чтобы следующий run-bot мог закрыть именно этот процесс.
    try:
        write_pid()
    except OSError as exc:
        log.warning("не записал PID-файл: %s", exc)

    log.info("Бот запущен, сценарий: %s", scenario.title)
    try:
        await dispatcher.start_polling(bot)
    except TelegramUnauthorizedError:
        raise SystemExit(
            "Telegram не принял токен (401). Перевыпустите его у @BotFather и обновите .env."
        ) from None
    except TelegramNetworkError as exc:
        raise SystemExit(
            "Нет соединения с Telegram. Включите VPN или задайте TELEGRAM_PROXY в .env, "
            f"затем проверьте: python -m bot.doctor. Подробности: {exc}"
        ) from None
    finally:
        clear_pid()
        await llm.aclose()
        if vision is not None:
            await vision.aclose()
        storage.close()
        await bot.session.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    scenario = load_scenario(story_scenarios()[0])
    asyncio.run(_run(settings, scenario))


if __name__ == "__main__":
    main()
