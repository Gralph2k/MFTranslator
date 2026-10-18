"""Локальная игра в терминале: проверка сценария без Telegram."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from typing import Any

from .config import Settings, load_settings
from .engine import DialogueEngine
from .llm import DeepSeekLLM, LLM
from .prompts import intro_text
from .safety import CrisisDetected, safety_message
from .scenario import load_scenario


@dataclass
class DemoLLM:
    """Демо-режим: заранее заготовленные реплики и разбор, без сети.

    Запрос на разбор узнаём по системному промпту методиста: иначе пришлось бы
    угадывать, сколько ходов сделает пользователь, и очередь разъезжалась.
    """

    replies: list[str]
    debrief: str
    index: int = 0
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
        temperature: float = 0.8,
    ) -> str:
        self.calls.append({"messages": messages, "json_mode": json_mode})
        system = messages[0]["content"] if messages else ""
        if "методист" in system:
            return self.debrief
        if "наблюдатель" in system:
            return json.dumps(
                {
                    "mood": "усталость",
                    "trust": 0.55,
                    "openness": 0.25,
                    "energy": 0.2,
                    "notes": [],
                    "ended": False,
                },
                ensure_ascii=False,
            )
        reply = self.replies[self.index % len(self.replies)]
        self.index += 1
        return reply

    async def aclose(self) -> None:
        return None


def build_llm(provider: str, settings: Settings) -> LLM:
    if provider == "deepseek":
        if not settings.has_llm:
            raise SystemExit(
                "Нет DEEPSEEK_API_KEY. Скопируйте .env.example в .env и впишите ключ, "
                "либо запустите с --provider demo."
            )
        return DeepSeekLLM(
            api_key=settings.deepseek_api_key or "",
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        )
    return DemoLLM(_demo_replies(), _demo_debrief())


def _demo_replies() -> list[str]:
    """Заготовки реплик персонажа: показывают рост открытости."""
    return [
        "Нормально всё, правда. Просто день был длинный.",
        "Ну... неприятно вышло. Не хочу сейчас об этом.",
        "Знаешь, да. Давай потом поужинаем, ладно?",
    ]


def _demo_debrief() -> str:
    payload = {
        "scores": {"noticing": 2, "questions": 1, "validation": 1,
                   "no_rescuing": 2, "self_expression": 1, "care_offer": 1},
        "summary": "Ты заметил состояние и не стал давить — это сработало. "
                   "Вопросов было многовато подряд.",
        "strengths": ["Ты назвал её состояние вслух, а не сделал вид, что всё нормально."],
        "growth": ["Не задавай два вопроса подряд — после первого сделай паузу."],
        "moments": [{"quote": "Ты не хочешь поговорить?",
                     "why": "Вопрос хороший, но в связке со следующим он стал допросом."}],
        "rewrite": {"original": "Ты не хочешь поговорить? Что случилось?",
                    "better": "Ты не хочешь поговорить? Если нет — я просто посижу рядом."},
        "next_time": "Сначала назвать чувство, потом задать один вопрос и замолчать.",
    }
    return json.dumps(payload, ensure_ascii=False)


async def run(provider: str, scenario_name: str) -> int:
    settings = load_settings()
    scenario = load_scenario(scenario_name)
    llm = build_llm(provider, settings)
    engine = DialogueEngine(llm)
    session = engine.start(scenario)

    print(f"=== {scenario.title} ===")
    print(intro_text(scenario))
    print(f"\n{scenario.persona.name}: {scenario.opening}\n")

    interactive = sys.stdin.isatty()
    try:
        while not session.is_over:
            try:
                if interactive:
                    line = input("Вы: ")
                else:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    line = line.rstrip("\n")
            except EOFError:
                break

            command = line.strip().lower()
            if command in {"/finish", "/stop", "/exit", "/quit"}:
                break
            if command == "/state":
                print(f"[состояние: {session.state.to_mapping()}]")
                continue
            if not line.strip():
                continue

            try:
                reply = await engine.reply(session, line)
            except CrisisDetected:
                print("\n" + safety_message(settings.safety_resources))
                return 0
            except Exception as exc:  # сеть/модель: показываем и продолжаем
                print(f"[ошибка модели: {exc}]")
                continue

            print(f"{scenario.persona.name}: {reply}")
            print(f"[состояние: {session.state.to_mapping()} | осталось ходов: {session.turns_left}]\n")
    finally:
        await llm.aclose()

    if session.user_turns == 0:
        print("Пока нечего разбирать.")
        return 0

    try:
        debrief = await engine.debrief(session)
    except Exception as exc:
        print(f"[разбор не получился: {exc}]")
        return 1

    print("\n" + "=" * 40)
    print(debrief.render(scenario))
    return 0


def main(argv: list[str] | None = None) -> int:
    # Консоль Windows по умолчанию не в UTF-8 — иначе русский текст превращается в кашу.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Локальный прогон сценария")
    parser.add_argument("--provider", choices=["demo", "deepseek"], default="demo")
    parser.add_argument("--scenario", default="friday_evening")
    args = parser.parse_args(argv)
    return asyncio.run(run(args.provider, args.scenario))


if __name__ == "__main__":
    raise SystemExit(main())
