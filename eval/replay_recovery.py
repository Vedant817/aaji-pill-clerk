"""Replay frozen raw completions offline; never overwrite hosted-run evidence."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from eval.audit import align_predictions, rows
from eval.compare_candidate import metrics, page_delta_ci
from pillclerk.config import ROOT
from pillclerk.infer import process_completion
from pillclerk.privacy import strip_pii


def replay(dataset: Path, system: str) -> dict:
    prefix = ROOT / "eval/out" / f"{system}_{dataset.stem}"
    raw_path, pred_path = Path(str(prefix) + "_raw.jsonl"), Path(str(prefix) + "_preds.jsonl")
    saved, raw = rows(pred_path), rows(raw_path)
    gold = align_predictions(rows(dataset), saved)
    if [r["line"] for r in raw] != [r["line"] for r in saved]:
        raise ValueError("Raw and saved prediction cohorts differ")
    after, recovery_counts, valid_changes = [], Counter(), 0
    for original, completion in zip(saved, raw, strict=True):
        if completion.get("raw") is None:
            after.append(original)  # A transport failure is not a recoverable model object.
            continue
        clean, _ = strip_pii(original["line"])
        pred, meta = process_completion(completion["raw"], clean)
        recovery_counts[meta["recovery_kind"] or "raw_valid"] += 1
        valid_changes += int(meta["raw_schema_valid"] and pred.model_dump() != original.get("pred"))
        after.append({"line": original["line"], "pred": pred.model_dump(),
                      "error": "raw_schema" if meta["recovery_used"] else None})
    before_summary, before_scores = metrics(gold, saved)
    after_summary, after_scores = metrics(gold, after)
    return {"n": len(gold), "before": before_summary, "after": after_summary,
            "recovery_counts": dict(recovery_counts), "raw_valid_output_changes": valid_changes,
            "exact_fixes": sum(not a["exact"] and b["exact"] for a, b in zip(before_scores, after_scores, strict=True)),
            "exact_regressions": sum(a["exact"] and not b["exact"] for a, b in zip(before_scores, after_scores, strict=True)),
            "exact_delta_page_bootstrap_ci95": page_delta_ci(before_scores, after_scores),
            "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (dataset, raw_path, pred_path)}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "eval/out/structural_recovery_replay.json")
    args = ap.parse_args()
    datasets = [ROOT / "data/synth/synth_test.jsonl", ROOT / "data/heldout/handwritten_realistic.jsonl",
                ROOT / "data/public_labels/hmr100_gold.jsonl", ROOT / "data/reference/hmr_ai_v1/ai_reference.jsonl"]
    report = {"kind": "offline replay of saved raw completions; no provider calls",
              "limitations": "Development evidence only; AI-reference labels exploratory; no OCR or clinical acceptance",
              "code_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                              for name in ("pillclerk/infer.py", "pillclerk/recovery.py", "pillclerk/copy_explicit.py", "pillclerk/validate.py")},
              "systems": {s: {p.stem: replay(p, s) for p in datasets} for s in ("ft2_current", "ft5")}}
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for system, sets in report["systems"].items():
        for name, result in sets.items():
            a, b = result["before"], result["after"]
            print(f"{system} {name}: exact {a['exact_count']} -> {b['exact_count']}/{a['n']}; "
                  f"danger {a['danger_count']} -> {b['danger_count']}; "
                  f"raw-valid changes {result['raw_valid_output_changes']}")


if __name__ == "__main__":
    main()
