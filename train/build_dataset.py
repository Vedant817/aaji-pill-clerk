"""sampler -> template render -> rule filter -> drug-held-out split."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from pillclerk.filters import normalised_text, rule_ok
from pillclerk.render import to_chat_row
from pillclerk.sampler import holdout_split, load_drugs, load_patterns, sample_line
from pillclerk.templates import render_template

ROOT = Path(__file__).resolve().parents[1]
SYNTH = ROOT / "data" / "synth"


def pick_style(rng: random.Random, patterns: dict) -> str:
    mapping = patterns["styles"]
    names = list(mapping)
    weights = [mapping[n] for n in names]
    return rng.choices(names, weights=weights, k=1)[0]


def generate_pairs(
    n: int,
    *,
    seed: int = 42,
    renderer: str = "template",
    drugs=None,
    patterns=None,
) -> list[dict]:
    if renderer == "llm":
        raise SystemExit(
            "LLM renderer is off (no DigitalOcean). Use --renderer template."
        )
    rng = random.Random(seed)
    drugs = drugs if drugs is not None else load_drugs()
    patterns = patterns if patterns is not None else load_patterns()
    seen: set[str] = set()
    out: list[dict] = []
    attempts = 0
    while len(out) < n and attempts < n * 30:
        attempts += 1
        drug = rng.choice(drugs)
        gold = sample_line(rng, drug, patterns)
        style = pick_style(rng, patterns)
        line = render_template(gold, style, rng)
        if not rule_ok(line, gold):
            continue
        key = normalised_text(line)
        if key in seen:
            continue
        seen.add(key)
        row = to_chat_row(line, gold)
        row["line"] = line
        row["gold"] = json.loads(gold.model_dump_json())
        row["style"] = style
        row["renderer"] = "template"
        row["drug"] = drug["name"]
        row["synthetic"] = True
        out.append(row)
    if len(out) < n:
        raise RuntimeError(f"only produced {len(out)}/{n} pairs after {attempts} attempts")
    return out


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_splits(
    *,
    n_train: int = 2000,
    n_val: int = 250,
    n_test: int = 400,
    seed: int = 42,
) -> dict[str, int]:
    patterns = load_patterns()
    drugs = load_drugs()
    train_drugs, test_drugs = holdout_split(
        drugs, fraction=float(patterns["held_out_drug_fraction"]), seed=seed
    )
    train = generate_pairs(n_train, seed=seed, drugs=train_drugs, patterns=patterns)
    val = generate_pairs(n_val, seed=seed + 1, drugs=train_drugs, patterns=patterns)
    test = generate_pairs(n_test, seed=seed + 2, drugs=test_drugs, patterns=patterns)
    write_jsonl(SYNTH / "train.jsonl", train)
    write_jsonl(SYNTH / "val.jsonl", val)
    write_jsonl(SYNTH / "synth_test.jsonl", test)
    return {
        "train": len(train),
        "val": len(val),
        "synth_test": len(test),
        "train_drugs": len({d["name"] for d in train_drugs}),
        "held_out_drugs": len({d["name"] for d in test_drugs}),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate synthetic prescription pairs (template path is free).")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--renderer", choices=["template", "llm"], default="template")
    ap.add_argument("--i-accept-llm-cost", action="store_true")
    ap.add_argument("--show", action="store_true", help="print pairs to stdout")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--split", action="store_true", help="write train/val/synth_test.jsonl")
    ap.add_argument("--n-train", type=int, default=2000)
    ap.add_argument("--n-val", type=int, default=250)
    ap.add_argument("--n-test", type=int, default=400)
    args = ap.parse_args(argv)

    if args.renderer == "llm":
        print("LLM renderer is off (no DigitalOcean). Use --renderer template.", file=sys.stderr)
        return 2

    if args.split:
        stats = write_splits(n_train=args.n_train, n_val=args.n_val, n_test=args.n_test, seed=args.seed)
        print(json.dumps(stats, indent=2))
        return 0

    pairs = generate_pairs(args.n, seed=args.seed, renderer=args.renderer)
    if args.show or args.out is None:
        for i, p in enumerate(pairs, 1):
            print(f"{i:02d} [{p['style']}] {p['line']}")
            print(f"    gold: {json.dumps(p['gold'], ensure_ascii=False)}")
    if args.out:
        write_jsonl(args.out, pairs)
        print(f"wrote {len(pairs)} rows to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
