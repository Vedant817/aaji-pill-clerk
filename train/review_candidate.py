"""Audit a synthetic candidate and prepare explicit missing-duration ASK corrections.

No medical advice, providers, human-label claims, or edits to frozen source files.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import re

from pillclerk.config import ROOT
from pillclerk.copy_explicit import align_gold
from pillclerk.filters import rule_ok
from pillclerk.render import to_chat_row
from pillclerk.schema import MedLine
from train.prepare_candidate import digest, jsonl, load_rows, prepare, write_frozen

CONTINUE = re.compile(r"\bcont(?:inue|inued|inuously)?\b", re.I)


def missing_duration(line: str, med: MedLine) -> bool:
    return (med.duration_days is None and med.kind != "taper"
            and "duration_days" not in med.needs_check and not CONTINUE.search(line))


def audit(rows: list[dict], sample_size: int, seed: int) -> dict:
    counts = Counter()
    mismatches, missing, invalid = [], [], []
    for index, row in enumerate(rows):
        med = MedLine.model_validate(row["gold"])
        counts.update([f"kind:{med.kind}", f"form:{med.form}", "ASK" if med.needs_check else "clear"])
        if not rule_ok(row["line"], med):
            invalid.append(index)
        if align_gold(med, row["line"]).model_dump() != med.model_dump():
            mismatches.append(index)
        if missing_duration(row["line"], med):
            missing.append(index)
    sample_indexes = sorted(random.Random(seed).sample(range(len(rows)), min(sample_size, len(rows))))
    return {"rows": len(rows), "coverage": dict(sorted(counts.items())),
            "rule_filter_failures": invalid, "copy_rule_disagreements": mismatches,
            "missing_duration_without_ASK_or_continue": missing,
            "sample_seed": seed, "sample_indexes": sample_indexes,
            "sample": [{"index": i, "line": rows[i]["line"], "gold": rows[i]["gold"]} for i in sample_indexes],
            "review_status": "automatic audit; AI inspection is not independent human or clinical review",
            "limits": "Agreement with generator/copy rules is not an independent accuracy measurement"}


def correct(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    out, changes = [], []
    for index, row in enumerate(rows):
        if row.get("synthetic") is not True:
            raise ValueError("Only synthetic candidate rows may be curated")
        med = MedLine.model_validate(row["gold"])
        if missing_duration(row["line"], med):
            revised = med.model_copy(update={"needs_check": sorted(set(med.needs_check + ["duration_days"]))})
            changes.append({"source_index": index, "line": row["line"], "field": "needs_check",
                            "before": med.needs_check, "after": revised.needs_check,
                            "reason": "No written duration or explicit continuation; preserve null and require ASK"})
            row = {**row, "gold": revised.model_dump(), **to_chat_row(row["line"], revised)}
        out.append(row)
    return out, changes


def review(source: Path, output: Path, seed: int = 20261003, sample_size: int = 30) -> dict:
    if source.resolve() == output.resolve():
        raise ValueError("Use a new candidate directory; source remains frozen")
    rows = {name: load_rows(source / f"{name}.jsonl") for name in ("train", "val")}
    report = {"source": str(source), "source_sha256": {name: digest(source / f"{name}.jsonl") for name in rows},
              "splits": {name: audit(value, sample_size, seed) for name, value in rows.items()},
              "human_review": "pending", "independent_acceptance_gold": "pending", "model_accuracy": "not measured"}
    corrected, changes = {}, {}
    for name, value in rows.items():
        corrected[name], changes[name] = correct(value)
    # Build through the same immutable cleaner, retaining source and all clinical values.
    staging = output / "curation_inputs"
    blobs = {"train.jsonl": jsonl(corrected["train"]), "val.jsonl": jsonl(corrected["val"]),
             "review.json": json.dumps(report, indent=2, ensure_ascii=False) + "\n",
             "changes.json": json.dumps(changes, indent=2, ensure_ascii=False) + "\n"}
    for name, blob in blobs.items():
        path = staging / name
        if path.exists() and path.read_text(encoding="utf-8") != blob:
            raise FileExistsError(f"Frozen review differs: {path}; use a new candidate directory")
    for name, blob in blobs.items():
        write_frozen(staging / name, blob)
    heldout = [ROOT / "data/synth/synth_test.jsonl", ROOT / "data/heldout/handwritten_realistic.jsonl",
               ROOT / "data/public_labels/hmr100_gold.jsonl", ROOT / "data/public_labels/bd200_gold.jsonl",
               *sorted((ROOT / "data/acceptance").glob("*/gold.jsonl"))]
    prepare(staging / "train.jsonl", staging / "val.jsonl", heldout, output)
    return {"rows": {name: len(value) for name, value in corrected.items()},
            "ASK_corrections": {name: len(value) for name, value in changes.items()},
            "human_review": "pending; automated corrections do not count as human signoff"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=ROOT / "data/candidates/clean_v4")
    ap.add_argument("--out", type=Path, default=ROOT / "data/candidates/safety_v5")
    ap.add_argument("--sample-size", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20261003)
    args = ap.parse_args()
    if args.sample_size < 1:
        ap.error("sample-size must be positive")
    print(json.dumps(review(args.source, args.out, args.seed, args.sample_size), indent=2))


if __name__ == "__main__":
    main()
