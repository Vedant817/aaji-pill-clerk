"""sampler -> template render -> rule filter -> drug-held-out split."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from pillclerk.filters import normalised_text, rule_ok
from pillclerk.render import to_chat_row
from pillclerk.sampler import (
    FORM_TO_UNIT,
    holdout_split,
    load_drugs,
    load_patterns,
    sample_daily_slots,
    sample_hard_negative,
    sample_line,
    sample_prn,
    sample_taper,
)
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


def generate_targeted(
    n: int,
    *,
    drugs,
    patterns,
    seed: int = 99,
) -> list[dict]:
    """FT2 extras for FT1 error buckets: form/unit, food cues, half-tab, taper, ASK."""
    rng = random.Random(seed)
    special = [d for d in drugs if d.get("form") not in ("tab", "other", "")]
    pool = special or drugs
    styles_form = ["clinic_print", "doctor_short", "hinglish_wa", "hindi", "marathi", "mixed"]
    seen: set[str] = set()
    out: list[dict] = []
    attempts = 0
    while len(out) < n and attempts < n * 40:
        attempts += 1
        bucket = rng.choice(["form", "form", "food", "half", "taper", "hard", "prn"])
        drug = rng.choice(pool if bucket == "form" else drugs)
        unit = FORM_TO_UNIT.get(drug["form"], "tab")
        if bucket == "hard":
            gold = sample_hard_negative(rng, drug, patterns)
            style = rng.choice(styles_form)
        elif bucket == "taper":
            gold = sample_taper(rng, drug, patterns, unit)
            style = "clinic_print"
        elif bucket == "prn":
            gold = sample_prn(rng, drug, patterns)
            style = rng.choice(["doctor_short", "clinic_print", "hinglish_wa"])
        elif bucket == "half":
            tabs = [d for d in drugs if d.get("form") in ("tab", "cap")] or drugs
            drug = rng.choice(tabs)
            unit = FORM_TO_UNIT.get(drug["form"], "tab")
            gold = sample_daily_slots(rng, drug, patterns, unit, (0.5, 0.0, 0.5))
            style = rng.choice(["clinic_print", "hinglish_wa", "marathi"])
        elif bucket == "food":
            gold = sample_daily_slots(rng, drug, patterns, unit, (1.0, 0.0, 1.0))
            food = rng.choice(["before", "after", "with", "empty_stomach"])
            gold = gold.model_copy(update={"food": food})
            style = rng.choice(["clinic_print", "doctor_short", "hindi"])
        else:
            gold = sample_daily_slots(
                rng, drug, patterns, unit, rng.choice([(1.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)])
            )
            style = rng.choice(styles_form)
        line = render_template(gold, style, rng)
        if not rule_ok(line, gold) and not gold.needs_check:
            continue
        key = normalised_text(line)
        if key in seen:
            continue
        seen.add(key)
        row = to_chat_row(line, gold)
        row.update(
            {
                "line": line,
                "gold": json.loads(gold.model_dump_json()),
                "style": style,
                "renderer": "template",
                "drug": drug["name"],
                "synthetic": True,
                "targeted": bucket,
            }
        )
        out.append(row)
    if len(out) < n:
        raise RuntimeError(f"targeted only produced {len(out)}/{n}")
    return out


def generate_form_dose_food(
    n: int,
    *,
    drugs,
    patterns,
    seed: int = 123,
) -> list[dict]:
    """Extra FT1-weak-field rows: form/unit, food tokens, half-tab and slot patterns."""
    rng = random.Random(seed)
    special = [d for d in drugs if d.get("form") not in ("tab", "other", "")]
    tabs = [d for d in drugs if d.get("form") in ("tab", "cap")] or drugs
    pool = special or drugs
    styles = ["clinic_print", "doctor_short", "hinglish_wa", "hindi", "marathi", "mixed"]
    seen: set[str] = set()
    out: list[dict] = []
    attempts = 0
    while len(out) < n and attempts < n * 40:
        attempts += 1
        bucket = rng.choice(["form", "form", "food", "food", "half", "slots"])
        if bucket == "form":
            drug = rng.choice(pool)
            unit = FORM_TO_UNIT.get(drug["form"], "tab")
            gold = sample_daily_slots(
                rng, drug, patterns, unit, rng.choice([(1.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)])
            )
            style = rng.choice(styles)
        elif bucket == "food":
            drug = rng.choice(drugs)
            unit = FORM_TO_UNIT.get(drug["form"], "tab")
            gold = sample_daily_slots(rng, drug, patterns, unit, (1.0, 0.0, 1.0))
            gold = gold.model_copy(update={"food": rng.choice(["before", "after", "with", "empty_stomach"])})
            style = rng.choice(["clinic_print", "doctor_short", "hindi", "marathi", "hinglish_wa"])
        elif bucket == "half":
            drug = rng.choice(tabs)
            unit = FORM_TO_UNIT.get(drug["form"], "tab")
            gold = sample_daily_slots(rng, drug, patterns, unit, rng.choice([(0.5, 0.0, 0.5), (0.5, 0.0, 0.0), (0.0, 0.0, 0.5)]))
            style = rng.choice(["clinic_print", "hinglish_wa", "marathi", "doctor_short"])
        else:
            drug = rng.choice(tabs)
            unit = FORM_TO_UNIT.get(drug["form"], "tab")
            gold = sample_daily_slots(
                rng, drug, patterns, unit, rng.choice([(1.0, 1.0, 1.0), (1.0, 0.0, 1.0), (0.0, 0.0, 1.0)])
            )
            style = rng.choice(["doctor_short", "clinic_print", "mixed"])
        line = render_template(gold, style, rng)
        if not rule_ok(line, gold):
            continue
        key = normalised_text(line)
        if key in seen:
            continue
        seen.add(key)
        row = to_chat_row(line, gold)
        row.update(
            {
                "line": line,
                "gold": json.loads(gold.model_dump_json()),
                "style": style,
                "renderer": "template",
                "drug": drug["name"],
                "synthetic": True,
                "targeted": f"fdf_{bucket}",
            }
        )
        out.append(row)
    if len(out) < n:
        raise RuntimeError(f"form/dose/food targeted only produced {len(out)}/{n}")
    return out


def write_splits(
    *,
    n_train: int = 2000,
    n_val: int = 250,
    n_test: int = 400,
    n_targeted: int = 500,
    n_form_dose_food: int = 400,
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
    extra = generate_targeted(n_targeted, drugs=train_drugs, patterns=patterns, seed=seed + 7) if n_targeted else []
    fdf = (
        generate_form_dose_food(n_form_dose_food, drugs=train_drugs, patterns=patterns, seed=seed + 11)
        if n_form_dose_food
        else []
    )
    write_jsonl(SYNTH / "train.jsonl", train + extra + fdf)
    write_jsonl(SYNTH / "val.jsonl", val)
    write_jsonl(SYNTH / "synth_test.jsonl", test)
    write_jsonl(SYNTH / "targeted_v2.jsonl", extra)
    write_jsonl(SYNTH / "targeted_form_dose_food.jsonl", fdf)
    return {
        "train": len(train) + len(extra) + len(fdf),
        "val": len(val),
        "synth_test": len(test),
        "targeted": len(extra),
        "form_dose_food": len(fdf),
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
    ap.add_argument(
        "--append-form-dose-food",
        action="store_true",
        help="append extra form/dose/food rows to train.jsonl; leave synth_test unchanged",
    )
    ap.add_argument("--n-train", type=int, default=2000)
    ap.add_argument("--n-val", type=int, default=250)
    ap.add_argument("--n-test", type=int, default=400)
    ap.add_argument("--n-targeted", type=int, default=500, help="FT2 extras mixed into train.jsonl")
    ap.add_argument("--n-form-dose-food", type=int, default=400, help="extra form/dose/food stress rows")
    args = ap.parse_args(argv)

    if args.renderer == "llm":
        print("LLM renderer is off (no DigitalOcean). Use --renderer template.", file=sys.stderr)
        return 2

    if args.append_form_dose_food:
        patterns = load_patterns()
        drugs = load_drugs()
        train_drugs, _ = holdout_split(
            drugs, fraction=float(patterns["held_out_drug_fraction"]), seed=args.seed
        )
        extra = generate_form_dose_food(
            args.n_form_dose_food, drugs=train_drugs, patterns=patterns, seed=args.seed + 11
        )
        train_path = SYNTH / "train.jsonl"
        existing = [json.loads(l) for l in train_path.read_text(encoding="utf-8").splitlines() if l.strip()] if train_path.is_file() else []
        keys = {normalised_text(r["line"]) for r in existing}
        new = [r for r in extra if normalised_text(r["line"]) not in keys]
        write_jsonl(SYNTH / "targeted_form_dose_food.jsonl", extra)
        write_jsonl(train_path, existing + new)
        print(json.dumps({"appended": len(new), "train": len(existing) + len(new), "fdf": len(extra)}, indent=2))
        return 0

    if args.split:
        stats = write_splits(
            n_train=args.n_train,
            n_val=args.n_val,
            n_test=args.n_test,
            n_targeted=args.n_targeted,
            n_form_dose_food=args.n_form_dose_food,
            seed=args.seed,
        )
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
