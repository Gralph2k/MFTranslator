"""P0: сверяет оценки строгого судьи с ожиданиями для policy probes.

Каждый пробник ломает ровно один навык или одно правило, поэтому у него есть эталон:
какой пункт рубрики обязан упасть, сколько красных флагов должно сработать и каким
должен быть потолок итогового балла. Если судья этого не видит — чинить надо судью,
а не героиню.

Запуск из корня проекта:
    .venv\\Scripts\\python.exe spike/check_probes.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "spike" / "runs"

ITEMS = ("hook", "question", "listening", "no_evaluation", "self", "pace")

# Пробник -> ожидания. max — потолок балла по пункту; min_flags — сколько красных
# флагов обязано сработать; total_max — потолок итогового балла.
EXPECTED: dict[str, dict] = {
    "probe_template": {"max": {"hook": 0, "question": 0}},
    "probe_no_questions": {"max": {"hook": 2, "question": 0}},
    "probe_two_questions": {"max": {"listening": 1}},
    "probe_status": {"max": {"self": 0}},
    "probe_rusher": {"max": {"pace": 1}},
    "probe_one_word": {"max": {"hook": 0, "question": 0, "listening": 0}},
    "probe_devalue": {"max": {"no_evaluation": 0}},
    # Новые ловушки и красные флаги из отзыва на «интеллигента».
    "probe_creep": {"min_flags": 1, "total_max": 6},
    "probe_manipulator": {"min_flags": 1, "total_max": 6},
    "probe_interrogator": {"max": {"no_evaluation": 1}, "total_max": 8},
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    failures = 0
    for run_name, expected in EXPECTED.items():
        run = RUNS / run_name
        path = run / "strict_judge.json"
        if not path.exists():
            print(f"{run_name}: нет strict_judge.json (прогон не оценён)")
            failures += 1
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        scores = {k: int((data.get("scores") or {}).get(k, 0)) for k in ITEMS}
        total = sum(scores.values())
        flags = len(data.get("red_flags_fired") or [])
        meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))

        problems = [
            f"{item}={scores[item]} > {limit}"
            for item, limit in (expected.get("max") or {}).items()
            if scores[item] > limit
        ]
        if "min_flags" in expected and flags < expected["min_flags"]:
            problems.append(f"красных флагов {flags} < {expected['min_flags']}")
        if "total_max" in expected and total > expected["total_max"]:
            problems.append(f"итог {total} > {expected['total_max']}")

        status = "OK" if not problems else "FAIL: " + "; ".join(problems)
        print(
            f"{run_name:<24} ходов={meta.get('turns_played'):>2} "
            f"ended={meta.get('ended_by'):<8} итог={total:>2} "
            f"флаги={flags}  " + ", ".join(f"{k}={scores[k]}" for k in ITEMS) + f"  -> {status}"
        )
        failures += 1 if problems else 0

    print()
    print("Все пробники прошли" if not failures else f"Провалили сверку: {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
