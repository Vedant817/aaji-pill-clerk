"""Offline replay of saved predictions. Never calls providers or rewrites official runs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from eval.eval import FIELDS, score, summarize, train_lines
from eval.report import mcnemar_exact
from pillclerk.copy_explicit import copy_explicit
from pillclerk.schema import MedLine
from pillclerk.validate import extra_rules

ROOT = Path(__file__).resolve().parents[1]


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def align_predictions(gold: list[dict], predictions: list[dict]) -> list[dict]:
    lines = [r["line"] for r in predictions]
    if len(set(lines)) != len(lines):
        raise ValueError("Duplicate prediction lines make pairing ambiguous")
    by_line = dict(zip(lines, predictions, strict=True))
    gold_lines = {r["line"] for r in gold}
    if set(lines) - gold_lines:
        raise ValueError("Prediction contains lines absent from the gold set")
    missing = gold_lines - set(lines) - train_lines()
    if missing:
        raise ValueError("Predictions are missing gold lines that are not training duplicates")
    # Official SYNTH runs exclude exact training duplicates. Preserve that cohort.
    aligned = [r for r in gold if r["line"] in by_line]
    if len(aligned) != len(predictions):
        raise ValueError("Gold lines are duplicated or predictions are missing")
    return aligned


def audit_set(gold_path: Path, pred_path: Path, system: str) -> dict:
    preds = rows(pred_path)
    gold = align_predictions(rows(gold_path), preds)
    by_line = {r["line"]: r for r in preds}
    before, after, changes = [], [], []
    for g in gold:
        saved = by_line[g["line"]]
        label = MedLine.model_validate(g["gold"])
        pred = MedLine.model_validate(saved["pred"]) if saved.get("pred") else None
        original = score(pred, label, error=saved.get("error"))
        revised = extra_rules(copy_explicit(pred, g["line"])) if pred is not None else None
        replay = score(revised, label, error=saved.get("error"))
        for s, p in ((original, pred), (replay, revised)):
            s["exact_and_ask"] = int(bool(s["exact"]) and p is not None and set(p.needs_check) == set(label.needs_check))
            s["line"] = g["line"]
        before.append(original)
        after.append(replay)
        if pred != revised:
            changes.append({"line": g["line"], "before_exact": original["exact"], "after_exact": replay["exact"],
                            "before_danger": original["danger_v2_norm"], "after_danger": replay["danger_v2_norm"],
                            "changed_fields": [f for f in FIELDS + ["needs_check"] if getattr(pred, f) != getattr(revised, f)]})
    baseline = summarize(system + "_saved", str(gold_path.relative_to(ROOT)), before, None)
    replay = summarize(system + "_offline_replay", str(gold_path.relative_to(ROOT)), after, None)
    for summary, scores in ((baseline, before), (replay, after)):
        summary["exact_and_ask"] = sum(s["exact_and_ask"] for s in scores) / len(scores)
        summary["danger_count"] = sum(s["danger_v2_norm"] for s in scores)
    return {"gold_sha256": hashlib.sha256(gold_path.read_bytes()).hexdigest(),
            "predictions_sha256": hashlib.sha256(pred_path.read_bytes()).hexdigest(),
            "excluded_gold_rows": len(rows(gold_path)) - len(gold),
            "saved": baseline, "replay": replay, "paired": mcnemar_exact(before, after), "changes": changes}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--system", default="ft2")
    ap.add_argument("--out", type=Path, default=ROOT / "eval/out/accuracy_audit.json")
    args = ap.parse_args()
    datasets = [ROOT / "data/synth/synth_test.jsonl", ROOT / "data/heldout/handwritten_realistic.jsonl",
                ROOT / "data/public_labels/hmr100_gold.jsonl"]
    results = {}
    for dataset in datasets:
        pred = ROOT / "eval/out" / f"{args.system}_{dataset.stem}_preds.jsonl"
        results[dataset.stem] = audit_set(dataset, pred, args.system)
    out = {"kind": "offline replay of already postprocessed saved predictions; no new model calls",
           "limitations": ["Not raw model accuracy", "Public set has informed parser changes and is now development evidence",
                           "No photo/OCR or family acceptance measurement", "No new latency measurement"],
           "code_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in [ROOT / "pillclerk/copy_explicit.py", ROOT / "pillclerk/validate.py",
                                     ROOT / "eval/eval.py", ROOT / "eval/audit.py"]}, "sets": results}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, result in results.items():
        a, b = result["saved"], result["replay"]
        print(f"{name}: n={a['n']} exact {a['exact']:.4f} -> {b['exact']:.4f}; "
              f"danger {a['danger_count']} -> {b['danger_count']}; ASK recall {a['ask_recall']} -> {b['ask_recall']}")


if __name__ == "__main__":
    main()
