"""sampler -> template render -> rule filter -> drug-held-out split."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from rapidfuzz import fuzz

from pillclerk.copy_explicit import align_gold
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
from pillclerk.schema import Dose, MedLine
from pillclerk.templates import render_template

ROOT = Path(__file__).resolve().parents[1]
SYNTH = ROOT / "data" / "synth"


def pair_row(line: str, gold, style: str, drug_name: str, **extra) -> dict:
    gold = align_gold(gold, line)
    row = to_chat_row(line, gold)
    row.update(
        {
            "line": line,
            "gold": json.loads(gold.model_dump_json()),
            "style": style,
            "renderer": "template",
            "drug": drug_name,
            "synthetic": True,
            **extra,
        }
    )
    return row


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
            "LLM renderer is off (template only unless LLM_BACKEND=gemini and you accept cost). Use --renderer template."
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
        out.append(pair_row(line, gold, style, drug["name"]))
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
        out.append(pair_row(line, gold, style, drug["name"], targeted=bucket))
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
        out.append(pair_row(line, gold, style, drug["name"], targeted=f"fdf_{bucket}"))
    if len(out) < n:
        raise RuntimeError(f"form/dose/food targeted only produced {len(out)}/{n}")
    return out


def eval_drug_names() -> set[str]:
    names: set[str] = set()
    for path in (
        SYNTH / "synth_test.jsonl",
        ROOT / "data" / "heldout" / "handwritten_realistic.jsonl",
        ROOT / "data" / "public_labels" / "hmr100_gold.jsonl",
        ROOT / "data" / "public_labels" / "bd200_gold.jsonl",
    ):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            drug = (json.loads(raw).get("gold") or {}).get("drug")
            if drug:
                names.add(str(drug).lower())
    return names


def generate_ft3_danger(
    n: int,
    *,
    drugs,
    patterns,
    seed: int = 2026,
    banned_lines: set[str] | None = None,
) -> list[dict]:
    """Insulin N unit, syrup ml / ASK, Hindi-Marathi three-slot, combo suffixes.

    Drugs must not appear in synth_test, handwritten_realistic, or hmr100_gold.
    """
    rng = random.Random(seed)
    banned_lines = banned_lines if banned_lines is not None else eval_line_keys()
    banned_drugs = eval_drug_names()
    eval_lines = eval_raw_lines()
    pool = [d for d in drugs if d["name"].lower() not in banned_drugs]
    insulins = [d for d in pool if d.get("form") == "injection"]
    syrups = [d for d in pool if d.get("form") == "syrup"]
    suffixes = {"AM", "MT", "LS", "CV", "XR", "D3"}
    combos = [
        d
        for d in pool
        if d["name"].strip().split()[-1].upper() in suffixes or d["name"].upper().endswith("D3")
    ]
    tabs = [d for d in pool if d.get("form") in ("tab", "cap")] or pool
    seen: set[str] = set(banned_lines)
    out: list[dict] = []
    attempts = 0

    def _near_eval(line: str) -> bool:
        return any(fuzz.ratio(line, other) > 90 for other in eval_lines)

    def _add(line: str, gold: MedLine, style: str, drug_name: str, tag: str) -> None:
        key = normalised_text(line)
        if key in seen:
            return
        if _near_eval(line):
            return
        if not gold.needs_check and not rule_ok(line, gold):
            return
        seen.add(key)
        out.append(pair_row(line, gold, style, drug_name, targeted=tag))

    while len(out) < n and attempts < n * 80:
        attempts += 1
        bucket = rng.choice(
            ["insulin", "insulin", "syrup", "syrup", "syrup_ask", "hi_slots", "combo", "combo"]
        )
        if bucket == "insulin" and insulins:
            drug = rng.choice(insulins)
            units = float(rng.choice([6, 8, 10, 12, 16]))
            slot = rng.choice(["morning", "afternoon", "night"])
            m = a = nt = 0.0
            if slot == "morning":
                m = units
                word = "subah"
            elif slot == "afternoon":
                a = units
                word = "dopahar"
            else:
                nt = units
                word = "raat"
            gold = MedLine(
                drug=drug["name"],
                strength=None,
                form="injection",
                kind="daily",
                dose=Dose(morning=m, afternoon=a, night=nt, unit="unit"),
                food="any",
                duration_days=None,
            )
            if rng.choice([True, False]):
                line = f"INJ. {drug['name']} {int(units)} unit {word}"
            else:
                line = f"{drug['name']} {int(units)} unit {word} ko"
            _add(line, gold, "hinglish_wa", drug["name"], "ft3_insulin")
        elif bucket in {"syrup", "syrup_ask"} and syrups:
            drug = rng.choice(syrups)
            days = int(rng.choice([3, 5, 7]))
            if bucket == "syrup_ask":
                gold = MedLine(
                    drug=drug["name"],
                    strength=None,
                    form="syrup",
                    kind="daily",
                    dose=None,
                    food="any",
                    duration_days=days,
                    needs_check=["dose", "schedule"],
                    note="frequency not written",
                )
                line = (
                    f"SYR. {drug['name']} x {days}d"
                    if rng.choice([True, False])
                    else f"SYR. {drug['name']} AFTER FOOD x {days} DAYS"
                )
                _add(line, gold, "doctor_short", drug["name"], "ft3_syrup_ask")
            else:
                m, a, nt = rng.choice([(5.0, 0.0, 5.0), (5.0, 0.0, 0.0), (0.0, 0.0, 5.0), (5.0, 5.0, 5.0)])
                gold = MedLine(
                    drug=drug["name"],
                    strength=drug["strengths"][0] if drug["strengths"] else None,
                    form="syrup",
                    kind="daily",
                    dose=Dose(morning=m, afternoon=a, night=nt, unit="ml"),
                    food="after",
                    duration_days=days,
                )
                line = f"SYR. {drug['name']}  {int(m)}-{int(a)}-{int(nt)} ml  AFTER FOOD  x {days} DAYS"
                _add(line, gold, "clinic_print", drug["name"], "ft3_syrup")
        elif bucket == "hi_slots" and tabs:
            drug = rng.choice(tabs)
            unit = FORM_TO_UNIT.get(drug["form"], "tab")
            gold = sample_daily_slots(rng, drug, patterns, unit, (1.0, 1.0, 1.0))
            style = rng.choice(["hindi", "marathi", "hinglish_wa"])
            line = render_template(gold, style, rng)
            _add(line, gold, style, drug["name"], "ft3_hi_slots")
        elif bucket == "combo" and combos:
            drug = rng.choice(combos)
            unit = FORM_TO_UNIT.get(drug["form"], "tab")
            gold = sample_daily_slots(rng, drug, patterns, unit, rng.choice([(1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 1.0)]))
            style = rng.choice(["clinic_print", "doctor_short", "hinglish_wa"])
            line = render_template(gold, style, rng)
            _add(line, gold, style, drug["name"], "ft3_combo")
        if len(out) >= n:
            break
    if len(out) < n:
        raise RuntimeError(f"ft3 danger targeted only produced {len(out)}/{n}")
    return out[:n]


def eval_raw_lines() -> list[str]:
    lines: list[str] = []
    for path in (
        SYNTH / "synth_test.jsonl",
        ROOT / "data" / "heldout" / "handwritten_realistic.jsonl",
        ROOT / "data" / "public_labels" / "hmr100_gold.jsonl",
        ROOT / "data" / "public_labels" / "bd200_gold.jsonl",
    ):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            line = json.loads(raw).get("line")
            if line:
                lines.append(str(line))
    return lines


def eval_line_keys() -> set[str]:
    keys: set[str] = set()
    for path in (
        SYNTH / "synth_test.jsonl",
        SYNTH / "val.jsonl",
        ROOT / "data" / "heldout" / "handwritten_realistic.jsonl",
        ROOT / "data" / "public_labels" / "hmr100_gold.jsonl",
        ROOT / "data" / "public_labels" / "bd200_gold.jsonl",
    ):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                keys.add(normalised_text(json.loads(line)["line"]))
    return keys


def generate_drug_strength(
    n: int,
    *,
    drugs,
    patterns,
    seed: int = 77,
    banned: set[str] | None = None,
) -> list[dict]:
    """FT3 extras: combo brands, odd strengths, Hindi/Marathi drug spelling."""
    rng = random.Random(seed)
    banned = banned if banned is not None else eval_line_keys()
    styles = ["clinic_print", "doctor_short", "hinglish_wa", "hindi", "marathi", "mixed"]
    combos = [d for d in drugs if " " in d["name"] or "/" in d["name"]] or drugs
    out: list[dict] = []
    seen: set[str] = set(banned)
    attempts = 0
    while len(out) < n and attempts < n * 50:
        attempts += 1
        bucket = rng.choice(["drug", "drug", "strength", "strength", "combo"])
        drug = rng.choice(combos if bucket == "combo" else drugs)
        unit = FORM_TO_UNIT.get(drug["form"], "tab")
        gold = sample_daily_slots(
            rng, drug, patterns, unit, rng.choice([(1.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)])
        )
        style = rng.choice(styles)
        line = render_template(gold, style, rng)
        if not rule_ok(line, gold):
            continue
        key = normalised_text(line)
        if key in seen:
            continue
        seen.add(key)
        out.append(pair_row(line, gold, style, drug["name"], targeted=f"ds_{bucket}"))
    if len(out) < n:
        raise RuntimeError(f"drug/strength targeted only produced {len(out)}/{n}")
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
    ap.add_argument(
        "--append-drug-strength",
        action="store_true",
        help="append ~200 drug/strength stress rows; leave eval sets unchanged",
    )
    ap.add_argument("--n-drug-strength", type=int, default=200)
    ap.add_argument(
        "--write-ft3-danger",
        action="store_true",
        help="write targeted_ft3_danger.jsonl (does not append train.jsonl; ask before Tinker SFT)",
    )
    ap.add_argument("--n-ft3-danger", type=int, default=200)
    args = ap.parse_args(argv)

    if args.renderer == "llm":
        print("LLM renderer is off. Use --renderer template (free).", file=sys.stderr)
        return 2

    if args.write_ft3_danger:
        patterns = load_patterns()
        drugs = load_drugs()
        extra = generate_ft3_danger(
            args.n_ft3_danger,
            drugs=drugs,
            patterns=patterns,
            seed=args.seed + 23,
            banned_lines=eval_line_keys(),
        )
        dest = SYNTH / "targeted_ft3_danger.jsonl"
        write_jsonl(dest, extra)
        tags: dict[str, int] = {}
        for row in extra:
            tags[str(row.get("targeted"))] = tags.get(str(row.get("targeted")), 0) + 1
        print(json.dumps({"wrote": dest.name, "n": len(extra), "tags": tags}, indent=2))
        return 0

    if args.append_drug_strength:
        patterns = load_patterns()
        drugs = load_drugs()
        train_drugs, _ = holdout_split(
            drugs, fraction=float(patterns["held_out_drug_fraction"]), seed=args.seed
        )
        extra = generate_drug_strength(
            args.n_drug_strength,
            drugs=train_drugs,
            patterns=patterns,
            seed=args.seed + 17,
            banned=eval_line_keys(),
        )
        train_path = SYNTH / "train.jsonl"
        existing = [json.loads(l) for l in train_path.read_text(encoding="utf-8").splitlines() if l.strip()] if train_path.is_file() else []
        keys = {normalised_text(r["line"]) for r in existing} | eval_line_keys()
        new = [r for r in extra if normalised_text(r["line"]) not in keys]
        write_jsonl(SYNTH / "targeted_drug_strength.jsonl", extra)
        write_jsonl(train_path, existing + new)
        print(json.dumps({"appended": len(new), "train": len(existing) + len(new), "ds": len(extra)}, indent=2))
        return 0

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
