"""Telegram-бот на aiogram 3: команды, диалог, разбор."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError, TelegramUnauthorizedError
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message

from .config import Settings, load_settings
from .engine import DialogueEngine, DialogueSession
from .faces import emotion_for_state, face_path
from .launcher import clear_pid, write_pid
from .llm import DeepSeekLLM, LLM
from .heroines import random_heroine
from .menus import (
    after_finish_menu,
    heroine_menu,
    heroines_menu,
)
from .profile_card import render_profile_cards
from .prompts import backstory_text, profile_text, rules_text
from .safety import CrisisDetected, safety_message
from .scenario import Scenario, ScenarioError, available_scenarios, load_scenario
from .state import PersonaState
from .storage import Storage, StoredSession

log = logging.getLogger(__name__)
router = Router()

MAX_MESSAGE = 4000
# Сколько последних сообщений прошлой переписки персонаж помнит в продолжении.
PREVIOUS_MESSAGES = 12


class Trainer:
    """Связывает Telegram, движок и хранилище. Держит сессии в памяти."""

    def __init__(
        self,
        engine: DialogueEngine,
        storage: Storage,
        default_scenario: Scenario,
        safety_resources: str | None = None,
        with_faces: bool = True,
    ) -> None:
        self.engine = engine
        self.storage = storage
        self.default_scenario = default_scenario
        self.safety_resources = safety_resources
        # Фото — часть сценария; флаг нужен тестам, чтобы не звать Telegram.
        self.with_faces = with_faces
        self.sessions: dict[int, DialogueSession] = {}
        self._scenarios: dict[str, Scenario] = {default_scenario.id: default_scenario}
        # Telegram хранит загруженный файл у себя: второй раз шлём по file_id,
        # иначе каждый ход тратит время на загрузку полумегабайтной картинки.
        self.face_file_ids: dict[str, str] = {}

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
        self.sessions[telegram_id] = session
        return session

    def last_heroine(self, telegram_id: int) -> str | None:
        """Героиня последней сессии — чтобы `/start` не выдавал её же подряд."""
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
        session.session_id = self.storage.create_session(
            user_id, scenario.id, session.state.to_mapping(), session.history
        )
        self.sessions[telegram_id] = session
        return session

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


# Единственный экземпляр Trainer на процесс: хендлеры aiogram статичны.
_trainer_instance: Trainer | None = None


def _trainer(message: Message) -> Trainer:
    if _trainer_instance is None:
        raise RuntimeError("Trainer не инициализирован")
    return _trainer_instance


async def _send_long(message: Message, text: str) -> None:
    """Telegram режет сообщения на 4096 символах — делим по строкам."""
    while text:
        if len(text) <= MAX_MESSAGE:
            await message.answer(text)
            return
        cut = text.rfind("\n", 0, MAX_MESSAGE)
        if cut < MAX_MESSAGE // 2:
            cut = MAX_MESSAGE
        await message.answer(text[:cut])
        text = text[cut:].lstrip("\n")


async def _send_face(message: Message, trainer: "Trainer", session: Any, caption: str) -> bool:
    """Лицо под текущее настроение. False — если картинки нет, текст отправит вызывающий.

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
    текст на сгенерированных картинках превращается в кашу, поэтому UI — PIL.
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
    сценария с именами `profile_*` — `faces.py` их не трогает.
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
        # Одно фото — не альбом: answer_media_group требует хотя бы два кадра.
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
    # /start выбирает случайную героиню: повторная команда не даёт ту же подряд.
    last = trainer.last_heroine(message.from_user.id)
    heroine = random_heroine(last)
    await _begin(message, trainer, message.from_user.id, heroine.first_scenario)


async def _begin(
    target: Message,
    trainer: "Trainer",
    telegram_id: int,
    scenario_id: str | None = None,
) -> None:
    """Начинает сценарий: сначала правила, потом описание и картинки."""
    try:
        session = trainer.start_session(telegram_id, scenario_id)
    except ScenarioError:
        await target.answer("Такого сценария нет. /menu — список.")
        return

    trainer.persist(telegram_id, session)
    # 1. «Это тренажёр», как играть и команды — без подсказки на первый ход.
    await _send_long(target, rules_text(session.scenario))

    if session.scenario.is_correspondence:
        # 2. Описание сценария, 3. её анкета — подписи с «о себе» разнесены по фото.
        await _send_long(target, backstory_text(session.scenario))
        # 3. Анкета с картинками и подписями. «Ход твой» уже сказан в описании,
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
        await message.answer("Такого сценария нет. /menu — список героинь.")
        return
    if not scenario.enabled:
        await message.answer("Этот сценарий выключен. /menu — выбрать героиню.")
        return
    await _begin(message, trainer, message.from_user.id, scenario_id)


@router.message(Command("restart"))
async def cmd_restart(message: Message) -> None:
    trainer = _trainer(message)
    current = trainer.get_session(message.from_user.id)
    # Активную сцену повторяем; выключенную или отсутствующую — меняем на случайную
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
    session = trainer.get_session(message.from_user.id)
    if session is None or session.user_turns == 0:
        await message.answer("Разбирать пока нечего: сначала поговори с ней. /start")
        return
    if session.debrief_sent:
        await message.answer("Разбор уже был выше. Новый разговор — /restart.")
        return

    await _deliver_debrief(message, trainer, message.from_user.id, session)


async def _deliver_debrief(
    target: Message,
    trainer: "Trainer",
    telegram_id: int,
    session: DialogueSession,
) -> None:
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
    await _send_face(target, trainer, session, "Так она закончила разговор.")
    await _send_long(target, text)
    await target.answer(
        "Что дальше?", reply_markup=after_finish_menu(session.scenario.id)
    )


@router.message(F.text)
async def on_text(message: Message) -> None:
    trainer = _trainer(message)
    text = (message.text or "").strip()
    if not text:
        return

    session = trainer.get_session(message.from_user.id)
    if session is None:
        await message.answer("Диалог ещё не начат. /start")
        return
    if session.is_over:
        await message.answer(
            "Этот разговор закончен. Новый — /restart или /menu."
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
        # Не влезает в подпись к фото — шлём картинку и текст отдельно.
        await _send_face(message, trainer, session, "")
        await _send_long(message, reply_text)
    elif not await _send_face(message, trainer, session, reply_text):
        await _send_long(message, reply_text)

    if session.ended_by_persona:
        # Красная линия: она закончила разговор. Разбор объяснит, на каком ходу.
        if session.scenario.is_call:
            farewell = "Она положила трубку. Сейчас будет разбор — почему."
        elif session.scenario.is_correspondence:
            farewell = "Она закрыла переписку. Сейчас будет разбор — почему."
        else:
            farewell = "Она ушла от разговора. Сейчас будет разбор — почему."
        await message.answer(farewell)

    if session.is_over:
        # Сюжет закончился (кончились ходы или персонаж закрыл тему) — разбираем сразу.
        await _deliver_debrief(message, trainer, message.from_user.id, session)


@router.callback_query(F.data.startswith("menu:"))
async def on_menu(callback: CallbackQuery) -> None:
    trainer = _trainer(callback.message)
    await callback.answer()

    action = (callback.data or "").split(":", 1)[1]
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
    storage = Storage(settings.db_path)
    trainer = Trainer(
        DialogueEngine(llm),
        storage,
        scenario,
        settings.safety_resources,
    )
    global _trainer_instance
    _trainer_instance = trainer
    # PID-файл — чтобы следующий run-bot мог закрыть именно этот процесс.
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
        storage.close()
        await bot.session.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    scenario = load_scenario(available_scenarios()[0])
    asyncio.run(_run(settings, scenario))


if __name__ == "__main__":
    main()
