"""Пересобирает разбор для сохранённого прогона: без повторной игры героини.

Нужен, когда финальный разбор в спайке упал (сеть/сертификат) или чтобы проверить,
насколько разбор устойчив: один и тот же диалог, несколько независимых оценок.

Запуск из корня проекта:
    python spike/redo_debrief.py --run spike/runs/run_saboteur --repeat 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.config import load_settings  # noqa: E402
from bot.engine import DialogueEngine, DialogueSession  # noqa: E402
from bot.llm import DeepSeekLLM  # noqa: E402
from bot.scenario import load_scenario  # noqa: E402
from bot.state import PersonaState  # noqa: E402

SCENARIO = "first_message"


def rebuild_session(run: Path) -> DialogueSession:
    scenario = load_scenario(SCENARIO)
    turns = [
        json.loads(line)
        for line in (run / "transcript.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    history: list[dict[str, str]] = []
    last_state = scenario.initial_state
    sent = 0
    for turn in turns:
        if turn.get("note") == "player_end":
            continue
        history.append({"role": "user", "content": turn["player"]})
        sent += 1
        if turn.get("heroine"):
            history.append({"role": "assistant", "content": turn["heroine"]})
        if turn.get("state"):
            last_state = turn["state"]
    return DialogueSession(
        scenario=scenario,
        state=PersonaState.from_mapping(last_state),
        history=history,
        user_turns=sent,
    )


async def main(run: Path, repeat: int) -> int:
    settings = load_settings()
    session = rebuild_session(run)
    llm = DeepSeekLLM(
        api_key=settings.deepseek_api_key or "",
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
    )
    engine = DialogueEngine(llm)
    try:
        for i in range(1, repeat + 1):
            debrief = await engine.debrief(session)
            text = debrief.render(session.scenario)
            (run / f"prod_debrief_{i}.md").write_text(text, encoding="utf-8")
            print(f"--- разбор {i}: {debrief.total}/{debrief.max_total} ---")
            print(text.split("\n\n", 1)[1][:400])
    finally:
        await llm.aclose()
    return 0


def main_cli() -> int:
    parser = argparse.ArgumentParser(description="Пересобрать разбор сохранённого прогона")
    parser.add_argument("--run", default="spike/runs/run_saboteur")
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    return asyncio.run(main(ROOT / args.run, args.repeat))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main_cli())
