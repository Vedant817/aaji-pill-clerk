"""sampler -> template (or LLM) render -> rule filter.

LLM render and parse-back call DigitalOcean (or Backboard) and cost money.
Default path is --renderer template, which is free and offline.
Do not generate the full train/val/synth_test split until the 10-line smoke
print has been reviewed.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from pillclerk.filters import normalised_text, rule_ok
from pillclerk.render import to_chat_row
from pillclerk.sampler import load_drugs, load_patterns, sample_line
from pillclerk.templates import render_template

ROOT = Path(__file__).resolve().parents[1]


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
            "Refusing to call the LLM renderer: it spends DigitalOcean (or Backboard) tokens. "
            "Re-run with --renderer template, or pass --i-accept-llm-cost after keys are in .env."
        )
    rng = random.Random(seed)
    drugs = drugs if drugs is not None else load_drugs()
    patterns = patterns if patterns is not None else load_patterns()
    seen: set[str] = set()
    out: list[dict] = []
    attempts = 0
    while len(out) < n and attempts < n * 20:
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate synthetic prescription pairs (template path is free).")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--renderer", choices=["template", "llm"], default="template")
    ap.add_argument("--i-accept-llm-cost", action="store_true")
    ap.add_argument("--show", action="store_true", help="print pairs to stdout")
    ap.add_argument("--out", type=Path, default=None, help="optional jsonl path (do not write the full split yet)")
    args = ap.parse_args(argv)

    if args.renderer == "llm" and not args.i_accept_llm_cost:
        print(
            "LLM renderer is gated. It needs DO_MODEL_ACCESS_KEY (or BACKBOARD_API_KEY) and spends tokens.",
            file=sys.stderr,
        )
        return 2

    if args.renderer == "llm":
        raise SystemExit("LLM renderer not wired into this CLI yet; use --renderer template for the smoke print.")

    pairs = generate_pairs(args.n, seed=args.seed, renderer=args.renderer)
    if args.show or args.out is None:
        for i, p in enumerate(pairs, 1):
            print(f"{i:02d} [{p['style']}] {p['line']}")
            print(f"    gold: {json.dumps(p['gold'], ensure_ascii=False)}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as fh:
            for p in pairs:
                fh.write(json.dumps(p, ensure_ascii=False) + "\n")
        print(f"wrote {len(pairs)} rows to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
