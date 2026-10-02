"""Rewrite gold fields on existing jsonl so they match the written line.

Does not change the line text. Used to correct synth_test in place after the
food / duration / prn_max generator bugs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pillclerk.copy_explicit import align_gold
from pillclerk.schema import MedLine

ROOT = Path(__file__).resolve().parents[1]


def correct_rows(rows: list[dict]) -> tuple[list[dict], int]:
    changed = 0
    out: list[dict] = []
    for row in rows:
        gold = MedLine.model_validate(row["gold"])
        fixed = align_gold(gold, row["line"])
        blob = json.loads(fixed.model_dump_json())
        if blob != row["gold"]:
            changed += 1
        new = dict(row)
        new["gold"] = blob
        msgs = new.get("messages")
        if isinstance(msgs, list) and len(msgs) >= 3 and msgs[2].get("role") == "assistant":
            msgs = list(msgs)
            msgs[2] = dict(msgs[2])
            msgs[2]["content"] = fixed.model_dump_json()
            new["messages"] = msgs
        out.append(new)
    return out, changed


def correct_file(path: Path, backup: Path | None = None) -> dict:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if backup and not backup.is_file():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    fixed, n = correct_rows(rows)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in fixed), encoding="utf-8")
    return {"path": str(path), "n": len(fixed), "changed": n, "backup": str(backup) if backup else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="data/synth/synth_test.jsonl")
    ap.add_argument("--backup", default="data/synth/synth_test_gold_v1.jsonl")
    a = ap.parse_args()
    print(json.dumps(correct_file(ROOT / a.set, ROOT / a.backup if a.backup else None), indent=2))


if __name__ == "__main__":
    main()
