"""Gold MedLine sampler: the answer first, then the question is rendered."""

from __future__ import annotations

import csv
import random
from pathlib import Path
from typing import Any

import yaml

from pillclerk.schema import Dose, Form, MedLine, TaperStep, Unit

ROOT = Path(__file__).resolve().parents[1]
DRUGS_CSV = ROOT / "data" / "drugs.csv"
PATTERNS_YAML = ROOT / "data" / "patterns.yaml"

FORM_TO_UNIT: dict[str, Unit] = {
    "syrup": "ml",
    "drops": "drop",
    "inhaler": "puff",
    "injection": "unit",
    "cream": "apply",
    "sachet": "sachet",
    "cap": "cap",
    "tab": "tab",
    "other": "tab",
}


def load_patterns(path: Path = PATTERNS_YAML) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"patterns file is not a mapping: {path}")
    return data


def load_drugs(path: Path = DRUGS_CSV) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for raw in csv.DictReader(fh):
            strengths = [s.strip() for s in (raw.get("strengths") or "").split("|") if s.strip()]
            form = (raw.get("form") or "tab").strip()
            name = (raw.get("name") or "").strip()
            if not name:
                continue
            rows.append(
                {
                    "name": name,
                    "form": form,
                    "strengths": strengths,
                    "generic": (raw.get("generic") or "").strip(),
                }
            )
    if len(rows) < 50:
        raise ValueError(f"expected ~150 drugs, found {len(rows)} in {path}")
    return rows


def _choices(rng: random.Random, mapping: dict[Any, float]) -> Any:
    keys = list(mapping.keys())
    weights = [float(mapping[k]) for k in keys]
    return rng.choices(keys, weights=weights, k=1)[0]


def _unit_for(form: str) -> Unit:
    return FORM_TO_UNIT.get(form, "tab")


def _scale(unit: Unit, patterns: dict[str, Any]) -> float:
    return float(patterns.get("unit_scale", {}).get(unit, 1))


def sample_daily(rng: random.Random, drug: dict[str, Any], patterns: dict[str, Any], unit: Unit) -> MedLine:
    sched = patterns["schedules"]
    pick = rng.choices(sched, weights=[s["weight"] for s in sched], k=1)[0]
    m, a, n = pick["pattern"]
    k = _scale(unit, patterns)
    # Weekly / every-N-days only for a single daily slot (e.g. Vitamin D3 60K).
    slots_on = sum(1 for x in (m, a, n) if x)
    every_weights = patterns["every_n_days_weights"]
    every = 1
    if slots_on == 1:
        every = int(_choices(rng, {int(x): w for x, w in every_weights.items()}))
    return MedLine(
        **_base(rng, drug, patterns),
        kind="daily",
        dose=Dose(morning=m * k, afternoon=a * k, night=n * k, unit=unit),
        every_n_days=every,
        duration_days=rng.choice(patterns["durations"]),
    )


def sample_prn(rng: random.Random, drug: dict[str, Any], patterns: dict[str, Any]) -> MedLine:
    return MedLine(
        **_base(rng, drug, patterns),
        kind="prn",
        prn_max_per_day=rng.choice([2, 3, None]),
        duration_days=rng.choice([3, 5, 7, None]),
    )


def sample_taper(rng: random.Random, drug: dict[str, Any], patterns: dict[str, Any], unit: Unit) -> MedLine:
    k = _scale(unit, patterns)
    high = Dose(morning=1 * k, night=1 * k, unit=unit)
    low = Dose(night=1 * k, unit=unit)
    d1, d2 = 5, 5
    return MedLine(
        **_base(rng, drug, patterns),
        kind="taper",
        taper=[TaperStep(dose=high, days=d1), TaperStep(dose=low, days=d2)],
        duration_days=d1 + d2,
    )


def sample_hard_negative(rng: random.Random, drug: dict[str, Any], patterns: dict[str, Any]) -> MedLine:
    """Lines the model must refuse to guess: missing frequency, as directed, illegible."""
    flavour = rng.choice(["missing_freq", "as_directed", "illegible", "missing_duration"])
    base = _base(rng, drug, patterns)
    if flavour == "illegible":
        base = {**base, "drug": None}
        return MedLine(
            **base,
            kind="daily",
            dose=None,
            needs_check=["drug", "dose", "schedule"],
            note="partially illegible",
        )
    if flavour == "as_directed":
        return MedLine(
            **base,
            kind="daily",
            dose=None,
            duration_days=None,
            needs_check=["dose", "schedule", "duration_days"],
            note="as directed",
        )
    if flavour == "missing_duration":
        unit = _unit_for(drug["form"])
        line = sample_daily(rng, drug, patterns, unit)
        return line.model_copy(update={"duration_days": None, "needs_check": ["duration_days"]})
    return MedLine(
        **base,
        kind="daily",
        dose=None,
        duration_days=rng.choice([5, 7, 10, None]),
        needs_check=["dose", "schedule"],
        note="frequency not written",
    )


def _base(rng: random.Random, drug: dict[str, Any], patterns: dict[str, Any]) -> dict[str, Any]:
    form: Form = drug["form"]  # type: ignore[assignment]
    strengths: list[str] = drug["strengths"]
    strength = rng.choice(strengths) if strengths else None
    food = _choices(rng, patterns["food_weights"])
    return {"drug": drug["name"], "strength": strength, "form": form, "food": food}


def sample_line(
    rng: random.Random,
    drug: dict[str, Any],
    patterns: dict[str, Any] | None = None,
    *,
    hard_negative: bool | None = None,
) -> MedLine:
    patterns = patterns or load_patterns()
    if hard_negative is None:
        hard_negative = rng.random() < float(patterns["hard_negative_rate"])
    if hard_negative:
        return sample_hard_negative(rng, drug, patterns)
    unit = _unit_for(drug["form"])
    kind = _choices(rng, patterns["kind_weights"])
    if kind == "prn":
        return sample_prn(rng, drug, patterns)
    if kind == "taper":
        return sample_taper(rng, drug, patterns, unit)
    return sample_daily(rng, drug, patterns, unit)


def holdout_split(
    drugs: list[dict[str, Any]],
    *,
    fraction: float = 0.2,
    seed: int = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    names = sorted({d["name"] for d in drugs})
    rng = random.Random(seed)
    rng.shuffle(names)
    n_hold = max(1, int(len(names) * fraction))
    held = set(names[:n_hold])
    train = [d for d in drugs if d["name"] not in held]
    test = [d for d in drugs if d["name"] in held]
    return train, test
