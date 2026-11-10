"""Собирает review-пакет для внешнего анализа (Gemini) из материалов прогона."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
SCENARIO = ROOT / "scenarios" / "first_message" / "scenario.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def main() -> int:
    data = json.loads(SCENARIO.read_text(encoding="utf-8"))
    scenario_block = []

    for key in ("title", "skill", "one_liner", "backstory", "situation", "contact_hint"):
        scenario_block.append(f"**{key}:** {data.get(key, '')}\n")

    persona = data.get("persona", {})
    scenario_block.append("**persona:**\n")
    for key in ("name", "age", "job", "relation", "traits", "speech"):
        value = persona.get(key)
        if isinstance(value, list):
            value = "; ".join(value)
        scenario_block.append(f"- {key}: {value}\n")

    scenario_block.append("\n**secrets (скрыто от игрока):**\n")
    for item in data.get("secrets", []):
        scenario_block.append(f"- {item}\n")

    levers = data.get("levers", {})
    scenario_block.append("\n**levers.helps:**\n")
    for item in levers.get("helps", []):
        scenario_block.append(f"- {item}\n")
    scenario_block.append("\n**levers.hurts:**\n")
    for item in levers.get("hurts", []):
        scenario_block.append(f"- {item}\n")

    scenario_block.append("\n**rubric:**\n")
    for item in data.get("rubric", []):
        scenario_block.append(
            f"- {item.get('id')} «{item.get('label')}», 0..{item.get('max')}: {item.get('what')}\n"
        )

    scenario_block.append("\n**red_flags:**\n")
    for item in data.get("red_flags", []):
        scenario_block.append(f"- {item}\n")

    scenarios = "".join(scenario_block)

    states_lines = []
    for line in read(RUN / "states.jsonl").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        states_lines.append(
            f"ход {row.get('n')}: mood={row.get('mood')}; trust={row.get('trust')}; "
            f"openness={row.get('openness')}; energy={row.get('energy')}"
        )
    states = "\n".join(states_lines)

    meta = json.loads(read(RUN / "meta.json"))
    meta_block = (
        f"- сценарий: {meta['scenario']}\n"
        f"- режим входа: {meta['mode']}\n"
        f"- модель героини: {meta['heroine_model']} (прод-температуры движка 0.85/0.2/0.3)\n"
        f"- модель игрока: {meta['player_model']}, temperature {meta['player_temperature']}\n"
        f"- лимит ходов: {meta['turn_limit']}, сыграно: {meta['turns_played']}\n"
        f"- кто закончил: {meta['ended_by']}\n"
        f"- ограничения стенда: модели игрока и героини — одна семья (DeepSeek); один прогон;\n"
        f"  токены и цена не считаются; реплики передавались напрямую, без Telegram-интерфейса;\n"
        f"  судья внутри бота — та же модель, что и героиня.\n"
    )

    parts = [
        read(RUN / "review_header.md"),
        "\n### 1. Что видел игрок (его системный промпт и вход)\n\n```\n",
        read(RUN / "player_system_prompt.md"),
        "\n```\n\n### 2. Транскрипт\n\n```\n",
        read(RUN / "transcript.md"),
        "\n```\n\n### 3. Замысел сценария и скрытые материалы (что игрок не видел)\n\n",
        scenarios,
        "\n### 4. Внутреннее состояние героини по ходам (игрок его не видит)\n\n```\n",
        states,
        "\n```\n\n### 5. Встроенный разбор бота (та же модель, что играла героиню)\n\n```\n",
        read(RUN / "prod_debrief.md"),
        "\n```\n\n### 6. Метаданные прогона и ограничения\n\n",
        meta_block,
    ]

    out = RUN / "gemini_review_pack.md"
    out.write_text("".join(parts), encoding="utf-8")
    print(f"written: {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
