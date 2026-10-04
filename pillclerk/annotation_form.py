"""Explicit manual annotation fields. No OCR, parser, or clinical defaults."""
from pillclerk.acceptance import validate_gold


def manual_gold(*, drug, strength, form, kind, food, duration, interval,
                dose, taper, prn_limit, checks, note=None):
    if form is None or kind is None or food is None:
        raise ValueError("Choose form, schedule kind and food explicitly")
    if interval is None:
        raise ValueError("Enter the dosing interval explicitly")
    if dose is not None and any(value is None for value in dose.values()):
        raise ValueError("Enter every dose slot and unit explicitly, including zero slots")
    checks = set(checks)
    if not drug or not drug.strip():
        drug = None
        checks.add("drug")
    if kind == "daily" and dose is None:
        checks.add("dose")
    if kind != "prn" and duration is None:
        checks.add("duration_days")
    blob = {"drug": drug, "strength": strength.strip() or None, "form": form,
            "kind": kind, "dose": dose, "taper": taper, "food": food,
            "duration_days": duration, "every_n_days": interval,
            "prn_max_per_day": prn_limit, "needs_check": sorted(checks), "note": note}
    return validate_gold(blob).model_dump()
