"""Gold MedLine sampler: the answer first, then the question is rendered.

Schedule mix matches IDEA.md §7 (of all non-hard-negative lines):
1-0-1 25%, 1-0-0 20%, 0-0-1 15%, 1-1-1 10%, half-tab 7%, PRN 8%,
taper 7%, every-N-days 5%, other 3%. Hard negatives are an extra 5%.
"""

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

WEEKLY_MARKERS = ("60k", "calcirol", "uprise d3", "vitamin d3", "vitamin d")


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


def is_weekly_typical(drug: dict[str, Any]) -> bool:
    blob = f"{drug['name']} {' '.join(drug.get('strengths') or [])}".lower()
    return any(tok in blob for tok in WEEKLY_MARKERS)


def _choices(rng: random.Random, mapping: dict[Any, float]) -> Any:
    keys = list(mapping.keys())
    weights = [float(mapping[k]) for k in keys]
    return rng.choices(keys, weights=weights, k=1)[0]


def _unit_for(form: str) -> Unit:
    return FORM_TO_UNIT.get(form, "tab")


def _scale(unit: Unit, patterns: dict[str, Any]) -> float:
    return float(patterns.get("unit_scale", {}).get(unit, 1))


def _dose(unit: Unit, m: float, a: float, n: float, patterns: dict[str, Any]) -> Dose:
    k = _scale(unit, patterns)
    return Dose(morning=m * k, afternoon=a * k, night=n * k, unit=unit)


def _pick_pattern(rng: random.Random, rows: list[dict[str, Any]]) -> tuple[float, float, float]:
    pick = rng.choices(rows, weights=[s["weight"] for s in rows], k=1)[0]
    m, a, n = pick["pattern"]
    return float(m), float(a), float(n)


def _base(rng: random.Random, drug: dict[str, Any], patterns: dict[str, Any]) -> dict[str, Any]:
    form: Form = drug["form"]  # type: ignore[assignment]
    strengths: list[str] = drug["strengths"]
    strength = rng.choice(strengths) if strengths else None
    food = _choices(rng, patterns["food_weights"])
    return {"drug": drug["name"], "strength": strength, "form": form, "food": food}


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


def sample_weekly(rng: random.Random, drug: dict[str, Any], patterns: dict[str, Any], unit: Unit) -> MedLine:
    """Vitamin D3 60K-style: one slot, every 7 days, long / continue duration."""
    slot = rng.choice(["morning", "night"])
    m, a, n = (1.0, 0.0, 0.0) if slot == "morning" else (0.0, 0.0, 1.0)
    return MedLine(
        **_base(rng, drug, patterns),
        kind="daily",
        dose=_dose(unit, m, a, n, patterns),
        every_n_days=7,
        duration_days=rng.choice(patterns.get("weekly_durations", [30, 60, 90, None])),
    )


def sample_daily_slots(
    rng: random.Random,
    drug: dict[str, Any],
    patterns: dict[str, Any],
    unit: Unit,
    slots: tuple[float, float, float],
) -> MedLine:
    m, a, n = slots
    return MedLine(
        **_base(rng, drug, patterns),
        kind="daily",
        dose=_dose(unit, m, a, n, patterns),
        every_n_days=1,
        duration_days=rng.choice(patterns["durations"]),
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
        line = sample_daily_slots(rng, drug, patterns, unit, (1.0, 0.0, 1.0))
        return line.model_copy(update={"duration_days": None, "needs_check": ["duration_days"]})
    return MedLine(
        **base,
        kind="daily",
        dose=None,
        duration_days=rng.choice([5, 7, 10, None]),
        needs_check=["dose", "schedule"],
        note="frequency not written",
    )


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
    # 60K IU / Vitamin D3 is weekly OD in real life (IDEA.md example).
    if is_weekly_typical(drug):
        return sample_weekly(rng, drug, patterns, unit)

    mix: dict[str, float] = {str(k): float(v) for k, v in patterns["line_mix"].items()}
    bucket = _choices(rng, mix)
    if bucket == "prn":
        return sample_prn(rng, drug, patterns)
    if bucket == "taper":
        return sample_taper(rng, drug, patterns, unit)
    if bucket == "every_n_days":
        return sample_weekly(rng, drug, patterns, unit)
    if bucket == "half_tab":
        slots = _pick_pattern(rng, patterns["half_tab"])
        return sample_daily_slots(rng, drug, patterns, unit, slots)
    if bucket == "other":
        slots = _pick_pattern(rng, patterns["other"])
        return sample_daily_slots(rng, drug, patterns, unit, slots)
    slots_map: dict[str, tuple[float, float, float]] = {
        "1-0-1": (1.0, 0.0, 1.0),
        "1-0-0": (1.0, 0.0, 0.0),
        "0-0-1": (0.0, 0.0, 1.0),
        "1-1-1": (1.0, 1.0, 1.0),
    }
    if bucket not in slots_map:
        raise ValueError(f"unknown line_mix bucket {bucket!r}")
    return sample_daily_slots(rng, drug, patterns, unit, slots_map[bucket])


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
