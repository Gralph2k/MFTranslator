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
from aiogram.types import CallbackQuery, FSInputFile, Message

from .config import Settings, load_settings
from .engine import DialogueEngine, DialogueSession
from .faces import emotion_for_state, face_path, label
from .llm import DeepSeekLLM, LLM
from .menus import after_finish_menu, scenario_title, scenarios_menu
from .prompts import intro_text
from .safety import CrisisDetected, safety_message
from .scenario import Scenario, ScenarioError, available_scenarios, load_scenario
from .state import PersonaState
from .storage import Storage

log = logging.getLogger(__name__)
router = Router()

MAX_MESSAGE = 4000


class Trainer:
    """Связывает Telegram, движок и хранилище. Держит сессии в памяти."""

    def __init__(
        self,
        engine: DialogueEngine,
        storage: Storage,
        default_scenario: Scenario,
        safety_resources: str | None = None,
        faces_dir: Path | None = None,
    ) -> None:
        self.engine = engine
        self.storage = storage
        self.default_scenario = default_scenario
        self.safety_resources = safety_resources
        self.faces_dir = faces_dir
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

        session = DialogueSession(
            scenario=self.scenario_by_id(stored.scenario),
            state=PersonaState.from_mapping(stored.state),
            history=stored.history,
            user_turns=stored.user_turns,
            finished=stored.finished,
            session_id=stored.id,
        )
        self.sessions[telegram_id] = session
        return session

    def start_session(self, telegram_id: int, scenario_id: str | None = None) -> DialogueSession:
        user_id = self.storage.ensure_user(telegram_id)
        old = self.storage.get_active_session(user_id)
        if old is not None:
            self.storage.save_session(
                old.id, old.state, old.history, old.user_turns, finished=True
            )

        scenario = self.default_scenario if scenario_id is None else self.scenario_by_id(scenario_id)
        session = self.engine.start(scenario)
        session.session_id = self.storage.create_session(
            user_id, scenario.id, session.state.to_mapping(), session.history
        )
        self.sessions[telegram_id] = session
        return session

    def persist(self, telegram_id: int, session: DialogueSession) -> None:
        if session.session_id is None:
            return
        self.storage.save_session(
            session.session_id,
            session.state.to_mapping(),
            session.history,
            session.user_turns,
            session.finished,
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


async def _send_face(message: Message, trainer: "Trainer", state: Any, caption: str) -> bool:
    """Лицо под текущее настроение. False — если картинки нет, текст отправит вызывающий."""
    if trainer.faces_dir is None:
        return False

    emotion = emotion_for_state(state)
    cached = trainer.face_file_ids.get(emotion)
    if cached is not None:
        await message.answer_photo(cached, caption=caption[:1024])
        return True

    path = face_path(emotion, trainer.faces_dir)
    if path is None:
        return False

    sent = await message.answer_photo(FSInputFile(path), caption=caption[:1024])
    if sent.photo:
        trainer.face_file_ids[emotion] = sent.photo[-1].file_id
    return True


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await _begin(message, _trainer(message), message.from_user.id)


async def _begin(
    target: Message,
    trainer: "Trainer",
    telegram_id: int,
    scenario_id: str | None = None,
) -> None:
    """Начинает сценарий и присылает вступление с первой репликой."""
    try:
        session = trainer.start_session(telegram_id, scenario_id)
    except ScenarioError:
        await target.answer("Такого сценария нет. /scenario — список.")
        return

    trainer.persist(telegram_id, session)
    await _send_long(target, intro_text(session.scenario))
    opening = f"{session.scenario.persona.name}: {session.scenario.opening}"
    if not await _send_face(target, trainer, session.state, opening):
        await target.answer(opening)


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("Что делаем?", reply_markup=scenarios_menu())


@router.message(Command("scenario"))
async def cmd_scenario(message: Message) -> None:
    trainer = _trainer(message)
    parts = (message.text or "").split(maxsplit=1)

    if len(parts) == 1:
        await message.answer("Выбери сценарий:", reply_markup=scenarios_menu())
        return

    await _begin(message, trainer, message.from_user.id, parts[1].strip())


@router.message(Command("restart"))
async def cmd_restart(message: Message) -> None:
    trainer = _trainer(message)
    current = trainer.get_session(message.from_user.id)
    scenario_id = current.scenario.id if current is not None else None
    await _begin(message, trainer, message.from_user.id, scenario_id)


@router.message(Command("state"))
async def cmd_state(message: Message) -> None:
    trainer = _trainer(message)
    session = trainer.get_session(message.from_user.id)
    if session is None:
        await message.answer("Сейчас нет активного диалога. Начни с /start.")
        return
    state = session.state
    emotion = emotion_for_state(state)
    text = (
        f"{session.scenario.persona.name} сейчас: {label(emotion)}.\n"
        f"Доверие — {state.trust:.0%}, готовность говорить — {state.openness:.0%}, "
        f"силы — {state.energy:.0%}.\n"
        f"Осталось ходов: {session.turns_left}."
    )
    if not await _send_face(message, trainer, state, text):
        await message.answer(text)


@router.message(Command("finish"))
async def cmd_finish(message: Message) -> None:
    trainer = _trainer(message)
    session = trainer.get_session(message.from_user.id)
    if session is None or session.user_turns == 0:
        await message.answer("Разбирать пока нечего: сначала поговори с ней. /start")
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
    await _send_face(target, trainer, session.state, "Так она закончила разговор.")
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
    reply_text = f"{session.scenario.persona.name}: {reply}"
    if len(reply_text) > 1024:
        # Не влезает в подпись к фото — шлём картинку и текст отдельно.
        await _send_face(message, trainer, session.state, "")
        await _send_long(message, reply_text)
    elif not await _send_face(message, trainer, session.state, reply_text):
        await _send_long(message, reply_text)

    if session.is_over:
        # Сюжет закончился (кончились ходы или персонаж закрыл тему) — разбираем сразу.
        await _deliver_debrief(message, trainer, message.from_user.id, session)


@router.callback_query(F.data.startswith("menu:"))
async def on_menu(callback: CallbackQuery) -> None:
    trainer = _trainer(callback.message)
    await callback.answer()

    action = (callback.data or "").split(":", 1)[1]
    if action == "list":
        await callback.message.answer("Выбери сценарий:", reply_markup=scenarios_menu())
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
        settings.faces_dir,
    )
    global _trainer_instance
    _trainer_instance = trainer

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
        await llm.aclose()
        storage.close()
        await bot.session.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings()
    scenario = load_scenario()
    asyncio.run(_run(settings, scenario))


if __name__ == "__main__":
    main()
