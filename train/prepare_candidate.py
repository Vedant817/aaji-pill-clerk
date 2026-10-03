"""Prepare a separate, synthetic-only candidate. No providers, no published-data edits."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from pillclerk.config import ROOT
from pillclerk.filters import normalised_text
from pillclerk.render import to_chat_row
from pillclerk.schema import MedLine
from train.sft import validate_split


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gold_key(gold: MedLine) -> str:
    value = gold.model_dump(exclude={"note"})
    value["needs_check"] = sorted(set(value["needs_check"]))
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def clean_rows(rows: list[dict], banned: set[str]) -> tuple[list[dict], list[dict]]:
    groups: dict[str, list[tuple[int, dict, MedLine]]] = defaultdict(list)
    rejected = []
    for i, row in enumerate(rows):
        if row.get("synthetic") is not True:
            raise ValueError("Candidate training/validation accepts explicitly synthetic rows only")
        try:
            line = row["line"]
            if not isinstance(line, str) or not line.strip():
                raise ValueError("Empty source line")
            gold = MedLine.model_validate(row["gold"])
            target = MedLine.model_validate_json(row["messages"][-1]["content"])
            if gold.model_dump() != target.model_dump():
                raise ValueError("Assistant target disagrees with gold")
            if row["messages"][-1]["role"] != "assistant" or row["messages"][-2] != {"role": "user", "content": line}:
                raise ValueError("Chat user turn disagrees with source line")
        except (KeyError, IndexError, TypeError, ValueError):
            rejected.append({"source_index": i, "reason": "invalid_or_misaligned_target"})
            continue
        key = normalised_text(line)
        if key in banned:
            rejected.append({"source_index": i, "reason": "held_out_overlap"})
        else:
            groups[key].append((i, row, gold))
    kept = []
    for group in groups.values():
        if len({gold_key(g) for _, _, g in group}) > 1:
            rejected.extend({"source_index": i, "reason": "conflicting_duplicate_labels"} for i, _, _ in group)
            continue
        i, row, gold = group[0]
        # Current prompt and complete canonical gold; no automatic relabelling.
        kept.append((i, {**row, **to_chat_row(row["line"], gold)}))
        rejected.extend({"source_index": i, "reason": "internal_duplicate"} for i, _, _ in group[1:])
    kept.sort(key=lambda entry: entry[0])
    return [row for _, row in kept], sorted(rejected, key=lambda r: r["source_index"])


def write_frozen(path: Path, data: str) -> None:
    """Idempotent repeat; refuse to mutate an already prepared candidate."""
    if path.exists() and path.read_text(encoding="utf-8") != data:
        raise FileExistsError(f"Frozen artifact differs: {path}. Use a new candidate directory.")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8", newline="")


def jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)


def prepare(train: Path, validation: Path, heldout: list[Path], output: Path) -> dict:
    # Check all destinations before any mutation, including unusual CLI overrides.
    source_paths = {p.resolve() for p in [train, validation, *heldout]}
    destinations = [output / n for n in ("train.jsonl", "val.jsonl", "rejections.json", "manifest.json")]
    if any(p.resolve() in source_paths for p in destinations):
        raise ValueError("Candidate output must not overwrite source or evaluation files")
    missing = [str(p) for p in heldout if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing held-out datasets: {missing}")
    eval_lines = {normalised_text(r["line"]) for p in heldout for r in load_rows(p)}
    val_rows, val_rejected = clean_rows(load_rows(validation), eval_lines)
    banned = eval_lines | {normalised_text(r["line"]) for r in val_rows}
    train_rows, train_rejected = clean_rows(load_rows(train), banned)
    if not train_rows or not val_rows:
        raise ValueError("Preparation produced an empty training or validation split")
    overlap = validate_split(train_rows, val_rows, heldout)
    blobs = {"train.jsonl": jsonl(train_rows), "val.jsonl": jsonl(val_rows),
             "rejections.json": json.dumps({"train": train_rejected, "validation": val_rejected}, indent=2) + "\n"}
    report = {
        "kind": "synthetic candidate only; not trained or deployed", "algorithm": "normalized-text deduplication; conflicting labels quarantined",
        "inputs": {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): {"sha256": digest(p), "rows": len(load_rows(p))}
                   for p in [train, validation, *heldout]},
        "outputs": {name: {"sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest()} for name, blob in blobs.items()},
        "train_rows": len(train_rows), "validation_rows": len(val_rows),
        "rejected_train": dict(Counter(r["reason"] for r in train_rejected)),
        "rejected_validation": dict(Counter(r["reason"] for r in val_rejected)),
        "overlap": overlap, "human_sample_review": "pending", "independent_test_labels": "pending",
        "limitation": "Exact normalized overlap is checked; template similarity and prior model exposure are not eliminated",
        "code_sha256": {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), ROOT / "pillclerk/filters.py", ROOT / "pillclerk/schema.py"]},
    }
    blobs["manifest.json"] = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    # Validate every existing target before writing any new target.
    for name, blob in blobs.items():
        p = output / name
        if p.exists() and p.read_text(encoding="utf-8") != blob:
            raise FileExistsError(f"Frozen artifact differs: {p}. Choose a new output directory.")
    for name, blob in blobs.items():
        write_frozen(output / name, blob)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", type=Path, default=ROOT / "data/synth/train.jsonl")
    ap.add_argument("--val", type=Path, default=ROOT / "data/synth/val.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "data/candidates/clean_v4")
    args = ap.parse_args()
    heldout = [ROOT / "data/synth/synth_test.jsonl", ROOT / "data/heldout/handwritten_realistic.jsonl",
               ROOT / "data/public_labels/hmr100_gold.jsonl", ROOT / "data/public_labels/bd200_gold.jsonl"]
    heldout.extend(sorted((ROOT / "data/acceptance").glob("*/gold.jsonl")))
    report = prepare(args.train, args.val, heldout, args.out)
    print(json.dumps({k: report[k] for k in ["train_rows", "validation_rows", "rejected_train", "rejected_validation", "overlap"]}, indent=2))


if __name__ == "__main__":
    main()
