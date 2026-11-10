"""P0: прогоняет строгий промпт судьи по сохранённым транскриптам и сравнивает прогоны.

Шкала должна быть монотонной: saboteur < borderline < average < ideal.
Пока этого нет, оценки героини ничего не значат.

Запуск из корня проекта:
    .venv\\Scripts\\python.exe spike/score_runs.py
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
from bot.llm import DeepSeekLLM, LLMError, parse_json_object  # noqa: E402

RUNS = ROOT / "spike" / "runs"
TEMPLATE = ROOT / "spike" / "judge_strict.md"
SCENARIO_FILE = ROOT / "scenarios" / "first_message" / "scenario.json"


def scenario_block() -> tuple[str, str, str]:
    data = json.loads(SCENARIO_FILE.read_text(encoding="utf-8"))

    scenario = [
        f"Название: «{data.get('title', '')}»",
        f"Навык: {data.get('skill', '')}",
        f"Задача игрока: {data.get('one_liner', '')}",
        f"Контакт: {data.get('contact_hint', '')}",
    ]
    profile = data.get("profile") or {}
    scenario.append(f"Анкета: {profile.get('about', '')}")
    if profile.get("hobbies"):
        scenario.append("Хобби: " + ", ".join(profile["hobbies"]))
    if profile.get("interests"):
        scenario.append("Интересы: " + ", ".join(profile["interests"]))
    captions = profile.get("captions") or {}
    for name, caption in captions.items():
        scenario.append(f"Фото ({name}): {caption}")

    rubric = "\n".join(
        f"- {item['id']} «{item['label']}», 0..{item['max']}: {item['what']}"
        for item in data.get("rubric", [])
    )
    red_flags = "\n".join(f"- {item}" for item in data.get("red_flags", []))
    return "\n".join(scenario), rubric, red_flags


def build_prompt(scenario: str, rubric: str, red_flags: str) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    return (
        template.replace("{{SCENARIO}}", scenario)
        .replace("{{RUBRIC}}", rubric)
        .replace("{{RED_FLAGS}}", red_flags)
    )


def load_runs(selected: list[str] | None) -> list[Path]:
    runs = sorted(p for p in RUNS.iterdir() if p.is_dir() and (p / "transcript.jsonl").exists())
    if selected:
        wanted = set(selected)
        runs = [p for p in runs if p.name in wanted]
    return runs


def player_facts(run: Path) -> str:
    """Считает объективные вещи кодом: судья на них опирается, а не угадывает."""
    turns = [
        json.loads(line)
        for line in (run / "transcript.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    messages = [turn.get("player", "") for turn in turns if turn.get("player")]
    with_question = [m for m in messages if "?" in m]
    two_plus = [m for m in messages if m.count("?") >= 2]
    lines = [
        f"- реплик игрока: {len(messages)}",
        f"- из них с вопросительным знаком: {len(with_question)}",
        f"- реплик с двумя и более вопросами: {len(two_plus)}",
    ]
    for index, message in enumerate(with_question, start=1):
        lines.append(f"- вопрос игрока {index}: {message}")
    return "\n".join(lines)


async def score(llm: DeepSeekLLM, prompt: str, transcript: str, facts: str) -> dict:
    raw = await llm.complete(
        [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    "## Посчитано кодом (доверяй этим фактам)\n\n"
                    + facts
                    + "\n\n## Транскрипт\n\n"
                    + transcript
                ),
            },
        ],
        json_mode=True,
        temperature=0.2,
    )
    return parse_json_object(raw)


async def main(selected: list[str] | None) -> int:
    settings = load_settings()
    llm = DeepSeekLLM(
        api_key=settings.deepseek_api_key or "",
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
    )
    scenario, rubric, red_flags = scenario_block()
    prompt = build_prompt(scenario, rubric, red_flags)
    rows: list[tuple[str, str, int, dict]] = []
    try:
        for run in load_runs(selected):
            transcript = (run / "transcript.md").read_text(encoding="utf-8")
            meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))
            try:
                data = await score(llm, prompt, transcript, player_facts(run))
            except LLMError as exc:
                print(f"{run.name}: судья не ответил — {exc}")
                continue
            scores = data.get("scores") or {}
            total = sum(int(scores.get(key, 0)) for key in (
                "hook", "question", "listening", "no_evaluation", "self", "pace"
            ))
            (run / "strict_judge.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            rows.append((run.name, meta.get("persona", "?"), total, data))
    finally:
        await llm.aclose()

    print(f"{'прогон':<22} {'игрок':<12} {'балл':>4}  разбивка")
    for name, persona, total, data in sorted(rows, key=lambda r: r[2]):
        scores = data.get("scores") or {}
        breakdown = ", ".join(f"{k}={scores.get(k, 0)}" for k in (
            "hook", "question", "listening", "no_evaluation", "self", "pace"
        ))
        flags = f" | красные: {len(data.get('red_flags_fired') or [])}"
        print(f"{name:<22} {persona:<12} {total:>4}  {breakdown}{flags}")
    return 0


def main_cli() -> int:
    parser = argparse.ArgumentParser(description="Строгая оценка сохранённых прогонов")
    parser.add_argument("--runs", nargs="*", help="имена папок в spike/runs")
    args = parser.parse_args()
    return asyncio.run(main(args.runs))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main_cli())
