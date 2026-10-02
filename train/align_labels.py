"""Re-align gold in existing train/val jsonl to tokens on the line.

Does not retrain. Writes eval/out/train_label_bugs.json with counts.
"""

from __future__ import annotations

import json
from pathlib import Path

from pillclerk.copy_explicit import align_gold
from pillclerk.schema import MedLine

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "out" / "train_label_bugs.json"


def align_file(path: Path) -> dict:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    n_food = n_dur = n_prn = n_any = 0
    out: list[dict] = []
    for row in rows:
        gold = MedLine.model_validate(row["gold"])
        line = row["line"]
        fixed = align_gold(gold, line)
        changed = json.loads(gold.model_dump_json()) != json.loads(fixed.model_dump_json())
        if changed:
            n_any += 1
            if gold.food != fixed.food:
                n_food += 1
            if gold.duration_days != fixed.duration_days:
                n_dur += 1
            if gold.prn_max_per_day != fixed.prn_max_per_day:
                n_prn += 1
            row = dict(row)
            row["gold"] = json.loads(fixed.model_dump_json())
            if row.get("messages"):
                row["messages"] = list(row["messages"])
                row["messages"][-1] = {
                    "role": "assistant",
                    "content": fixed.model_dump_json(),
                }
        out.append(row)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "n": len(rows),
        "n_changed": n_any,
        "food": n_food,
        "duration_days": n_dur,
        "prn_max_per_day": n_prn,
    }


def main() -> dict:
    stats = {
        "note": "align_gold on existing train/val. Weights not retrained. Generator already calls align_gold in pair_row.",
        "files": [
            align_file(ROOT / "data" / "synth" / "train.jsonl"),
            align_file(ROOT / "data" / "synth" / "val.jsonl"),
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return stats


if __name__ == "__main__":
    main()
