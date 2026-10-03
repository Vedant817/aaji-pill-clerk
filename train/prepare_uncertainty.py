"""Prepare synthetic omission pairs offline, preserving all published labels."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from pillclerk.config import ROOT
from pillclerk.copy_explicit import _DOSE_TRIPLE, _FORM_CUES, _qty
from pillclerk.filters import normalised_text
from pillclerk.render import to_chat_row
from pillclerk.schema import MedLine
from train.prepare_candidate import digest, jsonl, load_rows, prepare, write_frozen

LEAD_FORM = re.compile(r"^\s*(?:tab(?:let)?s?|cap(?:sule)?s?|syr(?:up)?|syp|drops?|inh(?:aler)?|inj(?:ection)?|sachet)\.?\s+", re.I)
DOSE_UNIT = re.compile(r"\b(\d+(?:\.\d+)?|½|¼|¾)\s*(ml|puffs?|drops?|units?|sachets?)\b", re.I)


def has_written_unit(line: str, strength: str | None) -> bool:
    if strength:
        pattern = r"\s*".join(re.escape(c) for c in re.sub(r"\s+", "", strength))
        line = re.sub(pattern, " ", line, count=1, flags=re.I)
    return bool(DOSE_UNIT.search(line))


def curate_units(source: list[dict], positive_limit: int) -> tuple[list[dict], list[dict], list[dict]]:
    """Version ambiguous synthetic unit labels and balance with explicit-unit copies."""
    curated, changes, positives = [], [], []
    for index, row in enumerate(source):
        if row.get("synthetic") is not True:
            raise ValueError("Only explicitly synthetic source rows are allowed")
        med = MedLine.model_validate(row["gold"])
        if (med.kind == "daily" and med.dose is not None
                and med.dose.unit in {"ml", "puff", "drop", "unit", "sachet"}
                and not has_written_unit(row["line"], med.strength)):
            gold = MedLine.model_validate({**med.model_dump(), "dose": None,
                "needs_check": sorted(set(med.needs_check + ["dose"]))})
            changes.append({"source_index": index, "reason": "No written administration unit; never infer volume/device quantity from form",
                            "before": med.model_dump(), "after": gold.model_dump()})
            curated.append({**row, "gold": gold.model_dump(), **to_chat_row(row["line"], gold)})
            triple = _DOSE_TRIPLE.search(row["line"])
            amounts = (med.dose.morning, med.dose.afternoon, med.dose.night)
            if (triple and tuple(_qty(triple.group(i)) for i in (1, 2, 3)) == amounts
                    and len(positives) < positive_limit):
                # Values come from synthetic gold. Write the unit explicitly;
                # no value is inferred from a real prescription or a drug name.
                explicit = "-".join(f"{n:g} {med.dose.unit}" for n in amounts)
                line = (row["line"][:triple.start()].rstrip() + " " + explicit
                        + " " + row["line"][triple.end():].lstrip()).strip()
                positives.append({**row, "line": line, **to_chat_row(line, med),
                    "renderer": "synthetic_explicit_unit", "source_index": index,
                    "paired_source_line": row["line"], "human_verified": False})
        else:
            curated.append(row)
    return curated, changes, positives


def omissions(source: list[dict], per_kind: int) -> list[dict]:
    additions, counts, seen = [], Counter(), set()
    for index, row in enumerate(source):
        if row.get("synthetic") is not True:
            raise ValueError("Only explicitly synthetic source rows are allowed")
        med = MedLine.model_validate(row["gold"])
        if med.kind != "daily" or med.dose is None or {"dose", "schedule"} & set(med.needs_check):
            continue
        line = row["line"]
        if not LEAD_FORM.match(line):
            continue
        variants = []
        no_form = LEAD_FORM.sub("", line, count=1)
        if med.form in {"tab", "cap"} and not any(p.search(no_form) for p, _, _ in _FORM_CUES):
            variants.append(("missing_form", no_form, {"form": "other"}, ["dose", "schedule"]))
        # Remove only a written administration unit. Never alter a strength span.
        if med.dose.unit in {"ml", "puff", "drop", "unit", "sachet"} and DOSE_UNIT.search(line):
            if med.strength is None or not re.search(r"ml|puff|drop|unit|sachet", med.strength, re.I):
                no_unit = DOSE_UNIT.sub(r"\1", line)
                if not DOSE_UNIT.search(no_unit):
                    variants.append(("missing_dose_unit", no_unit, {}, ["dose"]))
        for kind, changed, updates, flags in variants:
            key = normalised_text(changed)
            if key in seen or counts[kind] >= per_kind:
                continue
            seen.add(key)
            counts[kind] += 1
            gold = MedLine.model_validate({**med.model_dump(), **updates, "dose": None,
                "needs_check": sorted(set(med.needs_check + flags))})
            additions.append({"line": changed, "gold": gold.model_dump(), **to_chat_row(changed, gold),
                "synthetic": True, "renderer": "synthetic_omission", "omission": kind,
                "source_index": index, "paired_source_line": line,
                "label_origin": "deterministic_source_omission", "human_verified": False})
    return additions


def build(source: Path, output: Path, train_per_kind: int = 100, val_per_kind: int = 20) -> dict:
    if source.resolve() == output.resolve():
        raise ValueError("Use a separate output directory")
    split_rows = {s: load_rows(source / f"{s}.jsonl") for s in ("train", "val")}
    additions = {s: omissions(r, train_per_kind if s == "train" else val_per_kind) for s, r in split_rows.items()}
    unit_review = {s: curate_units(r, train_per_kind if s == "train" else val_per_kind) for s, r in split_rows.items()}
    review = {"kind": "synthetic omission candidate; not trained or deployed",
        "policy": {"missing_form": "form=other, dose=null, ASK dose+schedule; no brand inference",
                   "missing_dose_unit": "retain written form, dose=null, ASK dose; never assume a liquid/device quantity unit"},
        "source_sha256": {s: digest(source / f"{s}.jsonl") for s in split_rows},
        "requested_per_kind": {"train": train_per_kind, "val": val_per_kind},
        "additions": {s: dict(Counter(r["omission"] for r in rr)) for s, rr in additions.items()},
        "unit_label_corrections": {s: len(v[1]) for s, v in unit_review.items()},
        "explicit_unit_positives": {s: len(v[2]) for s, v in unit_review.items()},
        "sample": {s: [r for k in ("missing_form", "missing_dose_unit") for r in [x for x in rr if x["omission"] == k][:5]]
                   for s, rr in additions.items()},
        "limitations": "Derived templates, not independent human gold; historical evaluation labels unchanged; source positives retained"}
    staging = output / "curation_inputs"
    blobs = {f"{s}.jsonl": jsonl(unit_review[s][0] + additions[s] + unit_review[s][2]) for s in split_rows}
    blobs.update({f"{s}_omissions.jsonl": jsonl(additions[s]) for s in split_rows})
    blobs["review.json"] = json.dumps(review, indent=2, ensure_ascii=False) + "\n"
    blobs["unit_changes.json"] = json.dumps({s: v[1] for s, v in unit_review.items()}, indent=2, ensure_ascii=False) + "\n"
    for name, blob in blobs.items():
        path = staging / name
        if path.exists() and path.read_text(encoding="utf-8") != blob:
            raise FileExistsError(f"Frozen preparation differs: {path}")
    for name, blob in blobs.items():
        write_frozen(staging / name, blob)
    heldout = [ROOT / "data/synth/synth_test.jsonl", ROOT / "data/heldout/handwritten_realistic.jsonl",
               ROOT / "data/public_labels/hmr100_gold.jsonl", ROOT / "data/public_labels/bd200_gold.jsonl",
               *sorted((ROOT / "data/acceptance").glob("*/gold.jsonl")),
               *sorted((ROOT / "data/reference").glob("*/ai_reference.jsonl"))]
    manifest = prepare(staging / "train.jsonl", staging / "val.jsonl", heldout, output)
    return {"train_rows": manifest["train_rows"], "validation_rows": manifest["validation_rows"],
            "additions": review["additions"], "overlap": manifest["overlap"],
            "unit_label_corrections": review["unit_label_corrections"],
            "explicit_unit_positives": review["explicit_unit_positives"],
            "review": str(staging / "review.json"), "training": "not run"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=ROOT / "data/candidates/safety_v5")
    ap.add_argument("--out", type=Path, default=ROOT / "data/candidates/uncertainty_v6_final")
    args = ap.parse_args()
    print(json.dumps(build(args.source, args.out), indent=2))


if __name__ == "__main__":
    main()
