"""Движок диалога: один ход, состояние, финальный разбор."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .llm import LLM, LLMError, parse_json_object
from .prompts import debrief_messages, persona_messages, state_messages
from .safety import CrisisDetected, detect_crisis
from .scenario import RubricItem, Scenario
from .state import PersonaState

log = logging.getLogger(__name__)

MAX_REPLY_CHARS = 700


@dataclass
class DialogueSession:
    """Один разговор: сценарий, состояние персонажа и стенограмма."""

    scenario: Scenario
    state: PersonaState
    history: list[dict[str, str]] = field(default_factory=list)
    user_turns: int = 0
    ended_by_persona: bool = False
    finished: bool = False
    # Разбор уже отправлен: повторный /finish не должен тратить запрос и дублировать текст.
    debrief_sent: bool = False
    # Номер сессии в базе: без него после перезапуска процесса некуда писать разбор.
    session_id: int | None = None

    @property
    def turns_left(self) -> int:
        return max(0, self.scenario.turn_limit - self.user_turns)

    @property
    def is_over(self) -> bool:
        return self.finished or self.ended_by_persona or self.turns_left == 0


@dataclass
class Debrief:
    scores: dict[str, int]
    summary: str
    strengths: list[str]
    growth: list[str]
    moments: list[dict[str, str]]
    rewrite: dict[str, str]
    next_time: str
    total: int
    max_total: int

    def render(self, scenario: Scenario) -> str:
        lines = [f"Разбор: «{scenario.title}»", f"Итог: {self.total} из {self.max_total}", ""]
        for item in scenario.rubric:
            lines.append(f"{item.label} — {self.scores.get(item.id, 0)}/{item.max}")
        if self.summary:
            lines.extend(["", self.summary])
        if self.strengths:
            lines.extend(["", "Что получилось:"])
            lines.extend(f"• {x}" for x in self.strengths)
        if self.growth:
            lines.extend(["", "Что можно иначе:"])
            lines.extend(f"• {x}" for x in self.growth)
        for moment in self.moments[:3]:
            quote = moment.get("quote", "").strip()
            why = moment.get("why", "").strip()
            if quote:
                lines.extend(["", f"«{quote}» — {why}"])
        original = self.rewrite.get("original", "").strip()
        better = self.rewrite.get("better", "").strip()
        if original and better:
            lines.extend(["", "Как сказать иначе:", f"Было: {original}", f"Лучше: {better}"])
        if self.next_time:
            lines.extend(["", f"В следующий раз: {self.next_time}"])
        return "\n".join(lines)


class DialogueEngine:
    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def start(self, scenario: Scenario) -> DialogueSession:
        session = DialogueSession(
            scenario=scenario,
            state=PersonaState.from_mapping(scenario.initial_state),
        )
        session.history.append({"role": "assistant", "content": scenario.opening})
        return session

    async def reply(self, session: DialogueSession, text: str) -> str:
        """Один ход пользователя: реплика персонажа плюс обновление состояния."""
        text = text.strip()
        if not text:
            raise ValueError("пустое сообщение")

        session.history.append({"role": "user", "content": text})
        session.user_turns += 1

        if detect_crisis(text):
            # Упражнение останавливается: продолжать сцену в такой момент нельзя.
            raise CrisisDetected(text)

        raw = await self.llm.complete(
            persona_messages(session.scenario, session.state, session.history),
            json_mode=False,
            temperature=0.85,
        )
        reply, embedded_state, ended = _parse_persona_reply(raw)

        if embedded_state is None:
            # Обычный текстовый ответ: состояние оцениваем отдельным запросом.
            state_delta, ended = await self._read_state(session)
        else:
            state_delta = embedded_state

        session.state.apply(state_delta)
        session.ended_by_persona = ended
        session.history.append({"role": "assistant", "content": reply})
        return reply

    async def _read_state(self, session: DialogueSession) -> tuple[dict[str, Any], bool]:
        """Оценка состояния. Сбой здесь не должен ломать реплику."""
        try:
            raw = await self.llm.complete(
                state_messages(session.scenario, session.state, session.history),
                json_mode=True,
                temperature=0.2,
            )
            data = parse_json_object(raw)
        except LLMError as exc:
            log.warning("состояние не обновлено: %s", exc)
            return {}, False

        delta = {
            key: data[key]
            for key in ("mood", "trust", "openness", "energy", "notes")
            if key in data
        }
        return delta, bool(data.get("ended"))

    async def debrief(self, session: DialogueSession) -> Debrief:
        if session.user_turns == 0:
            raise LLMError("разбирать нечего: пользователь ещё ничего не написал")

        raw = await self.llm.complete(
            debrief_messages(session.scenario, session.history),
            json_mode=True,
            temperature=0.3,
        )
        data = parse_json_object(raw)
        session.finished = True
        return _parse_debrief(data, session.scenario)


def _parse_persona_reply(raw: str) -> tuple[str, dict[str, Any] | None, bool]:
    """Разбирает ответ модели.

    Обычно это просто текст реплики. Но если модель всё-таки вернула JSON
    с полем reply — используем его, чтобы не терять состояние из лишнего запроса.
    None во втором элементе значит «состояния в ответе нет».
    """
    try:
        data = parse_json_object(raw)
    except LLMError:
        return _trim(raw), None, False

    reply = str(data.get("reply", "")).strip()
    if not reply:
        return _trim(raw), None, False

    embedded = data.get("state")
    return (
        _trim(reply),
        embedded if isinstance(embedded, dict) else {},
        bool(data.get("ended")),
    )


def _trim(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= MAX_REPLY_CHARS:
        return text
    cut = text[:MAX_REPLY_CHARS]
    stop = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return (cut[: stop + 1] if stop > 200 else cut).strip()


def _as_text_list(value: Any, limit: int = 4) -> list[str]:
    if not isinstance(value, list):
        return []
    result = [str(item).strip() for item in value if str(item).strip()]
    return result[:limit]


def _parse_debrief(data: dict[str, Any], scenario: Scenario) -> Debrief:
    raw_scores = data.get("scores")
    raw_scores = raw_scores if isinstance(raw_scores, dict) else {}

    scores: dict[str, int] = {}
    for item in scenario.rubric:
        scores[item.id] = _score(raw_scores.get(item.id), item)

    moments_raw = data.get("moments")
    moments = []
    if isinstance(moments_raw, list):
        for moment in moments_raw[:3]:
            if isinstance(moment, dict):
                moments.append(
                    {
                        "quote": str(moment.get("quote", "")).strip(),
                        "why": str(moment.get("why", "")).strip(),
                    }
                )

    rewrite_raw = data.get("rewrite")
    rewrite = {}
    if isinstance(rewrite_raw, dict):
        rewrite = {
            "original": str(rewrite_raw.get("original", "")).strip(),
            "better": str(rewrite_raw.get("better", "")).strip(),
        }

    return Debrief(
        scores=scores,
        summary=str(data.get("summary", "")).strip(),
        strengths=_as_text_list(data.get("strengths")),
        growth=_as_text_list(data.get("growth")),
        moments=moments,
        rewrite=rewrite,
        next_time=str(data.get("next_time", "")).strip(),
        total=sum(scores.values()),
        max_total=scenario.max_score,
    )


def _score(value: Any, item: RubricItem) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(item.max, number))
