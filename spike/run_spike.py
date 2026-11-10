"""Спайк: слепой прогон «среднего» игрока против настоящей героини.

Героиня играется тем же движком и промптами, что в проде (bot.engine + bot.prompts).
Игрок — отдельный вызов DeepSeek с промптом из `player_<persona>.md`; он не видит
сценарий, состояние, рубрику и счётчик ходов. Всё, что он знает, — его персона
и `bundle_player_view.md`.

Запуск из корня проекта:
    python spike/run_spike.py --persona average
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.config import load_settings  # noqa: E402
from bot.engine import DialogueEngine  # noqa: E402
from bot.llm import DeepSeekLLM, LLMError  # noqa: E402
from bot.scenario import load_scenario  # noqa: E402

SPIKE = Path(__file__).resolve().parent
SCENARIO = "first_message"
PLAYER_TEMPERATURE = 1.1


def clean_player_message(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^(Игорь|Артём|Максим|Я|Ответ|Он)\s*:\s*", "", text, flags=re.IGNORECASE)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)
    text = text.strip("*_ ")
    text = text.strip("«»\"'` ")
    return text.strip()


def build_player_system(persona: str) -> str:
    player = (SPIKE / "first_message" / f"player_{persona}.md").read_text(encoding="utf-8")
    bundle = (SPIKE / "first_message" / "bundle_player_view.md").read_text(encoding="utf-8")
    return player.rstrip() + "\n\n" + bundle.rstrip() + "\n"


def write_outputs(
    out: Path,
    *,
    persona: str,
    player_system: str,
    turns: list[dict],
    ended_by: str,
    turn_limit: int,
    states: list[dict],
    debrief_text: str | None,
    started_at: str,
    finished_at: str,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    transcript_lines = []
    for turn in turns:
        transcript_lines.append(f"Я: {turn['player']}")
        if turn.get("heroine"):
            transcript_lines.append(f"Она: {turn['heroine']}")
        transcript_lines.append("")
    transcript = "\n".join(transcript_lines).strip() + "\n"

    (out / "transcript.md").write_text(transcript, encoding="utf-8")
    (out / "transcript.jsonl").write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in turns) + "\n",
        encoding="utf-8",
    )
    (out / "player_system_prompt.md").write_text(player_system, encoding="utf-8")
    (out / "states.jsonl").write_text(
        "\n".join(json.dumps(s, ensure_ascii=False) for s in states) + "\n",
        encoding="utf-8",
    )
    if debrief_text:
        (out / "prod_debrief.md").write_text(debrief_text, encoding="utf-8")

    settings = load_settings()
    meta = {
        "scenario": SCENARIO,
        "persona": persona,
        "mode": "живой человек (без рамки тренажёра и советов)",
        "heroine_model": settings.deepseek_model,
        "player_model": settings.deepseek_model,
        "player_temperature": PLAYER_TEMPERATURE,
        "turn_limit": turn_limit,
        "turns_played": len(turns),
        "ended_by": ended_by,
        "started_at": started_at,
        "finished_at": finished_at,
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    judge = (SPIKE / "first_message" / "judge.md").read_text(encoding="utf-8")
    pack = (
        "# Пакет для анализа: прогон «Первое сообщение»\n\n"
        "Ниже — задание судьи и транскрипт переписки. Прочитай задание и верни только JSON.\n\n"
        "---\n\n"
        + judge.rstrip()
        + "\n\n---\n\n"
        "## Транскрипт\n\n"
        + transcript
    )
    (out / "gemini_pack.md").write_text(pack, encoding="utf-8")

    print("=" * 60)
    print(transcript)
    print("=" * 60)
    print(f"Ходов: {len(turns)}, закончил: {ended_by}")


async def run(persona: str, out: Path) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    settings = load_settings()
    scenario = load_scenario(SCENARIO)
    player_system = build_player_system(persona)

    heroine_llm = DeepSeekLLM(
        api_key=settings.deepseek_api_key or "",
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
    )
    player_llm = DeepSeekLLM(
        api_key=settings.deepseek_api_key or "",
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
    )

    engine = DialogueEngine(heroine_llm)
    session = engine.start(scenario)

    started_at = datetime.now(timezone.utc).isoformat()
    history: list[dict[str, str]] = [{"role": "system", "content": player_system}]
    turns: list[dict] = []
    states: list[dict] = []
    ended_by = "turn_limit"

    try:
        while not session.is_over:
            try:
                raw = await player_llm.complete(history, temperature=PLAYER_TEMPERATURE)
            except LLMError as exc:
                print(f"игрок не ответил: {exc}", file=sys.stderr)
                ended_by = "player_error"
                break
            message = clean_player_message(raw)
            if not message:
                ended_by = "player_error"
                break
            if "<конец>" in message:
                ended_by = "player"
                turns.append(
                    {
                        "n": session.user_turns + 1,
                        "player": message.replace("<конец>", "").strip(),
                        "heroine": "",
                        "note": "player_end",
                    }
                )
                break

            try:
                reply = await engine.reply(session, message)
            except LLMError as exc:
                print(f"героиня не ответила: {exc}", file=sys.stderr)
                ended_by = "heroine_error"
                break

            history.append({"role": "assistant", "content": message})
            history.append({"role": "user", "content": reply})
            turns.append(
                {
                    "n": session.user_turns,
                    "player": message,
                    "heroine": reply,
                    "state": session.state.to_mapping(),
                }
            )
            states.append({"n": session.user_turns, **session.state.to_mapping()})
            print(f"[{session.user_turns}/{scenario.turn_limit}] Я: {message}")
            print(f"           Она: {reply}")

        if session.ended_by_persona:
            ended_by = "heroine"
        elif session.turns_left == 0 and ended_by == "turn_limit":
            ended_by = "turn_limit"
    finally:
        await heroine_llm.aclose()
        await player_llm.aclose()

    debrief_text = None
    if session.user_turns:
        try:
            debrief = await DialogueEngine(DeepSeekLLM(
                api_key=settings.deepseek_api_key or "",
                base_url=settings.deepseek_base_url,
                model=settings.deepseek_model,
            )).debrief(session)
            debrief_text = debrief.render(scenario)
        except Exception as exc:  # noqa: BLE001 — разбор не должен ронять спайк
            debrief_text = f"[разбор не получился: {exc}]"

    write_outputs(
        out,
        persona=persona,
        player_system=player_system,
        turns=turns,
        ended_by=ended_by,
        turn_limit=scenario.turn_limit,
        states=states,
        debrief_text=debrief_text,
        started_at=started_at,
        finished_at=datetime.now(timezone.utc).isoformat(),
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Слепой прогон игрока против героини")
    parser.add_argument("--persona", default="average")
    parser.add_argument("--out", default="spike/runs/run1")
    args = parser.parse_args()
    persona_file = SPIKE / "first_message" / f"player_{args.persona}.md"
    if not persona_file.exists():
        raise SystemExit(f"нет промпта игрока: {persona_file}")
    out = ROOT / args.out
    return asyncio.run(run(args.persona, out))


if __name__ == "__main__":
    raise SystemExit(main())
