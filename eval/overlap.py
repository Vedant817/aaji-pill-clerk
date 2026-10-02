"""Exact and near-duplicate overlap of train vs every eval set.

Usage: uv run python -m eval.overlap
Writes eval/out/overlap.json. rapidfuzz ratio > 90 is a near-dup.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rapidfuzz import fuzz

from pillclerk.filters import normalised_text

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "out" / "overlap.json"
NEAR = 90

SETS = {
    "train": ROOT / "data" / "synth" / "train.jsonl",
    "val": ROOT / "data" / "synth" / "val.jsonl",
    "synth_test": ROOT / "data" / "synth" / "synth_test.jsonl",
    "handwritten_realistic": ROOT / "data" / "heldout" / "handwritten_realistic.jsonl",
    "hmr100_gold": ROOT / "data" / "public_labels" / "hmr100_gold.jsonl",
    "bd200_gold": ROOT / "data" / "public_labels" / "bd200_gold.jsonl",
}


def load_lines(path: Path) -> list[str]:
    if not path.is_file():
        return []
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        line = row.get("line")
        if line:
            out.append(str(line))
    return out


def compare(a_name: str, a_lines: list[str], b_name: str, b_lines: list[str]) -> dict:
    b_raw = set(b_lines)
    exact = [left for left in a_lines if left in b_raw]
    near: list[dict] = []
    # Skip exact matches already counted; scan remaining for ratio > 90.
    b_exact = set(exact)
    for i, left in enumerate(a_lines):
        if left in b_exact:
            continue
        best_j = -1
        best = 0.0
        for j, right in enumerate(b_lines):
            ratio = float(fuzz.ratio(left, right))
            if ratio > best:
                best, best_j = ratio, j
        if best > NEAR and best_j >= 0:
            near.append(
                {
                    "a": left,
                    "b": b_lines[best_j],
                    "ratio": best,
                }
            )
    a_n = {normalised_text(x) for x in a_lines}
    b_n = {normalised_text(x) for x in b_lines}
    exact_unique = sorted(set(exact))
    return {
        "a": a_name,
        "b": b_name,
        "n_a": len(a_lines),
        "n_b": len(b_lines),
        "exact": len(exact_unique),
        "exact_occurrences": len(exact),
        "exact_normalized": len(a_n & b_n),
        "exact_lines": exact_unique,
        "near_ratio_gt_90": len(near),
        "near_pairs": near[:50],
    }


EVAL_SET_NAMES = ("synth_test", "handwritten_realistic", "hmr100_gold", "bd200_gold")


def vs_eval(lines: list[str], extra_name: str = "extra") -> dict:
    """Exact + near overlap of a candidate file against every eval set (not train)."""
    vs: dict[str, dict] = {}
    for name in EVAL_SET_NAMES:
        c = compare(extra_name, lines, name, load_lines(SETS[name]))
        vs[name] = {
            "exact": c["exact"],
            "exact_normalized": c["exact_normalized"],
            "near_ratio_gt_90": c["near_ratio_gt_90"],
            "n_eval": c["n_b"],
        }
    return {
        "extra": extra_name,
        "n": len(lines),
        "vs_eval": vs,
        "any_exact_eval": any(v["exact"] for v in vs.values()),
        "any_near_eval": any(v["near_ratio_gt_90"] for v in vs.values()),
    }


def run() -> dict:
    loaded = {name: load_lines(path) for name, path in SETS.items()}
    pairs: list[dict] = []
    names = list(SETS)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            pairs.append(compare(a, loaded[a], b, loaded[b]))
    train_vs_synth = next(p for p in pairs if {p["a"], p["b"]} == {"train", "synth_test"})
    out = {
        "near_threshold": NEAR,
        "exact_train_synth_test": train_vs_synth["exact"],
        "pairs": pairs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra", type=Path, default=None, help="candidate jsonl to check against eval sets")
    args = ap.parse_args()
    out = run()
    print(json.dumps({k: out[k] for k in ("near_threshold", "exact_train_synth_test")}, indent=2))
    print(f"wrote {OUT}")
    if args.extra:
        extra = vs_eval(load_lines(args.extra), extra_name=args.extra.name)
        extra_path = OUT.parent / "overlap_extra.json"
        extra_path.write_text(json.dumps(extra, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(extra, indent=2))
        print(f"wrote {extra_path}")


if __name__ == "__main__":
    main()
