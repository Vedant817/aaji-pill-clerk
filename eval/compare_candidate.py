"""Compare fresh matched predictions; AI references remain exploratory."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random

from eval.eval import FIELDS, drop_train_duplicates, field_eq, score
from eval.report import mcnemar_exact
from pillclerk.config import ROOT
from pillclerk.schema import MedLine


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def metrics(gold: list[dict], predictions: list[dict]) -> tuple[dict, list[dict]]:
    if len(gold) != len(predictions) or any(g["line"] != p["line"] for g, p in zip(gold, predictions, strict=True)):
        raise ValueError("Gold and predictions must have exactly matching ordered cohorts")
    scores, ask_tp, ask_fp, ask_fn = [], 0, 0, 0
    field_counts = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    selective, selective_exact = 0, 0
    unflagged = defaultdict(int)
    for g, p in zip(gold, predictions, strict=True):
        label = MedLine.model_validate(g["gold"])
        pred = MedLine.model_validate(p["pred"]) if p.get("pred") else None
        s = score(pred, label, error=p.get("error"))
        want, have = set(label.needs_check), set(pred.needs_check) if pred else set()
        s.update(line=g["line"], image=g.get("image", g["line"]), exact_and_ask=int(bool(s["exact"]) and pred is not None and want == have))
        ask_tp += len(want & have)
        ask_fp += len(have - want)
        ask_fn += len(want - have)
        for field in want | have:
            key = "tp" if field in want & have else "fp" if field in have else "fn"
            field_counts[field][key] += 1
        if pred is not None and not have:
            selective += 1
            selective_exact += s["exact"]
        if pred is not None:
            for name in FIELDS:
                flag = "schedule" if name in {"form", "kind", "every_n_days", "taper"} else "dose" if name == "prn_max_per_day" else name
                if not field_eq(pred, label, name, normalize=True) and flag not in have:
                    unflagged[name] += 1
        scores.append(s)
    n = len(scores)
    return {"n": n, "exact_count": sum(s["exact"] for s in scores),
            "exact": sum(s["exact"] for s in scores) / n,
            "exact_and_ask": sum(s["exact_and_ask"] for s in scores) / n,
            "danger_count": sum(s["danger_v2_norm"] for s in scores),
            "ASK_field_precision": ask_tp / (ask_tp + ask_fp) if ask_tp + ask_fp else None,
            "ASK_field_recall": ask_tp / (ask_tp + ask_fn) if ask_tp + ask_fn else None,
            "ASK_field_counts": dict(field_counts), "selective_coverage": selective / n,
            "selective_accuracy": selective_exact / selective if selective else None,
            "unflagged_field_errors": dict(unflagged)}, scores


def page_delta_ci(before: list[dict], after: list[dict], iterations: int = 1000) -> list[float]:
    groups = defaultdict(list)
    for a, b in zip(before, after, strict=True):
        groups[a["image"]].append(b["exact"] - a["exact"])
    keys = sorted(groups)
    rng = random.Random(20261003)
    means = []
    for _ in range(iterations):
        sample = [delta for key in rng.choices(keys, k=len(keys)) for delta in groups[key]]
        means.append(sum(sample) / len(sample))
    means.sort()
    return [means[int(iterations * 0.025)], means[int(iterations * 0.975)]]


def compare(path: Path, baseline: str, candidate: str) -> dict:
    gold, _, _ = drop_train_duplicates(rows(path), None)
    pred_paths = {name: ROOT / "eval/out" / f"{name}_{path.stem}_preds.jsonl" for name in (baseline, candidate)}
    summaries, scored = {}, {}
    for name, pred_path in pred_paths.items():
        summaries[name], scored[name] = metrics(gold, rows(pred_path))
        run = json.loads((pred_path.parent / f"{name}_{path.stem}.json").read_text(encoding="utf-8"))
        expected_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if run.get("dataset_sha256") != expected_hash:
            raise ValueError("Evaluation dataset bytes changed; comparison is stale")
        summaries[name]["raw_schema_failures"] = run.get("raw_schema_failures")
        summaries[name]["sampling_compute_upper_usd"] = run.get("sampling_compute_upper_usd")
    return {"dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "results": summaries,
            "exact_delta_page_bootstrap_ci95": page_delta_ci(scored[baseline], scored[candidate]),
            "paired_line_McNemar": mcnemar_exact(scored[baseline], scored[candidate]),
            "exploratory_AI_reference": any(r.get("label_origin") == "ai_single_agent" for r in gold),
            "limitations": "Postprocessed parser outputs; no OCR, caregiver acceptance or independent clinical accuracy"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", default="ft2_current")
    ap.add_argument("--candidate", default="ft5")
    ap.add_argument("--out", type=Path, default=ROOT / "eval/out/ft5_comparison.json")
    args = ap.parse_args()
    datasets = [ROOT / "data/synth/synth_test.jsonl", ROOT / "data/heldout/handwritten_realistic.jsonl",
                ROOT / "data/public_labels/hmr100_gold.jsonl", ROOT / "data/reference/hmr_ai_v1/ai_reference.jsonl"]
    report = {"kind": "fresh matched hosted predictions; exploratory development comparison",
              "datasets": {p.stem: compare(p, args.baseline, args.candidate) for p in datasets},
              "active_model_update": "none"}
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
