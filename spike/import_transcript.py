"""Импортирует ручной транскрипт (из чата Gemini) в формат прогона.

Транскрипт — обычный текст, где реплики помечены `Я:` (игрок) и `Она:` (героиня).
Дальше такой прогон можно оценить внутренним разбором: `spike/redo_debrief.py`.

Запуск из корня проекта:
    python spike/import_transcript.py --file spike/runs/manual_gemini/raw.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bot.scenario import load_scenario  # noqa: E402

MARKER = re.compile(r"^(Я|Она)\s*:\s*(.*)$")


def parse(text: str) -> list[dict]:
    turns: list[dict] = []
    speaker: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal speaker, buffer
        if speaker is None:
            buffer = []
            return
        message = "\n".join(buffer).strip()
        if speaker == "Я":
            turns.append({"n": len([t for t in turns if t.get("player")]) + 1, "player": message})
        elif turns and message:
            turns[-1]["heroine"] = message
        speaker = None
        buffer = []

    for line in text.splitlines():
        match = MARKER.match(line)
        if match:
            flush()
            speaker, rest = match.group(1), match.group(2).strip()
            buffer = [rest] if rest else []
        elif speaker is not None:
            buffer.append(line)

    flush()
    # Последний ход игрока мог остаться без ответа — это нормально.
    return turns


def main() -> int:
    parser = argparse.ArgumentParser(description="Импорт ручного транскрипта")
    parser.add_argument("--file", required=True)
    parser.add_argument("--run", default="spike/runs/manual_gemini")
    args = parser.parse_args()

    run = ROOT / args.run
    run.mkdir(parents=True, exist_ok=True)
    raw = (ROOT / args.file).read_text(encoding="utf-8")
    turns = parse(raw)
    if not turns:
        print("не нашёл ни одной реплики вида «Я: …»")
        return 1

    scenario = load_scenario("first_message")
    lines = []
    for turn in turns:
        lines.append(f"Я: {turn['player']}")
        if turn.get("heroine"):
            lines.append(f"Она: {turn['heroine']}")
        lines.append("")

    (run / "transcript.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    (run / "transcript.jsonl").write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in turns) + "\n", encoding="utf-8"
    )
    meta = {
        "scenario": "first_message",
        "persona": "average / ручной прогон (Gemini)",
        "mode": "живой человек (без рамки тренажёра и советов)",
        "turn_limit": scenario.turn_limit,
        "turns_played": len(turns),
        "ended_by": "unclear",
    }
    (run / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    judge = (ROOT / "spike" / "first_message" / "judge.md").read_text(encoding="utf-8")
    pack = (
        "# Пакет для анализа: ручной прогон «Первое сообщение»\n\n"
        "Ниже — задание судьи и транскрипт переписки. Прочитай задание и верни только JSON.\n\n"
        "---\n\n"
        + judge.rstrip()
        + "\n\n---\n\n## Транскрипт\n\n"
        + "\n".join(lines).strip()
        + "\n"
    )
    (run / "gemini_pack.md").write_text(pack, encoding="utf-8")

    print(f"импортировано ходов: {len(turns)} -> {run}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
