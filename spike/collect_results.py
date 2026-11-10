"""Сводка по всем прогонам в spike/runs: баллы внутреннего разбора и метаданные.

Запуск из корня проекта:
    python spike/collect_results.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "spike" / "runs"
TOTAL = re.compile(r"Итог:\s*(\d+)\s*из\s*(\d+)")
ITEM = re.compile(r"^(?P<label>[^—]+?)\s*—\s*(?P<score>\d+)/(?P<max>\d+)$")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for run in sorted(p for p in RUNS.iterdir() if p.is_dir()):
        meta_path = run / "meta.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        print(f"== {run.name}: persona={meta.get('persona')} turns={meta.get('turns_played')} "
              f"ended={meta.get('ended_by')}")
        debriefs = sorted(run.glob("prod_debrief*.md"))
        if not debriefs:
            print("   разбора нет")
            continue
        for path in debriefs:
            text = path.read_text(encoding="utf-8")
            total = TOTAL.search(text)
            if not total:
                print(f"   {path.name}: разбор не удался")
                continue
            items = [
                f"{m.group('label').strip()}={m.group('score')}"
                for m in (ITEM.match(line.strip()) for line in text.splitlines())
                if m
            ]
            print(f"   {path.name}: {total.group(1)}/{total.group(2)}  [{', '.join(items)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
