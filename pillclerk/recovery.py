"""Salvage structurally valid fields without converting uncertain clinical values."""
from __future__ import annotations

from pydantic import ValidationError

from pillclerk.schema import MedLine


def recover_fields(obj: object) -> tuple[MedLine, dict] | None:
    """Replace invalid fields with neutral, flagged values; never convert units.

    Whole-object consistency errors and malformed ASK lists are not salvageable.
    The returned replacements must also be applied after source-copy processing,
    which otherwise could reconstruct the field that was deliberately withheld.
    """
    if not isinstance(obj, dict):
        return None
    try:
        MedLine.model_validate(obj)
        return None  # Recovery is only for an actually invalid object.
    except ValidationError as exc:
        errors = exc.errors()
    if any(not e["loc"] for e in errors):
        return None
    fields = {e["loc"][0] for e in errors}
    if "needs_check" in fields:
        return None
    replacements = {}
    checks = set(obj.get("needs_check", []))
    for name in fields:
        if name in {"drug", "strength", "duration_days"}:
            replacements[name] = None
            checks.add(name)
        elif name == "form":
            replacements["form"] = "other"
            checks.add("schedule")
        elif name == "dose":
            replacements["dose"] = None
            checks.add("dose")
        elif name in {"kind", "taper", "every_n_days"}:
            replacements.update(kind="daily", taper=[], every_n_days=1, dose=None)
            checks.update({"dose", "schedule"})
        elif name == "food":
            replacements["food"] = "any"
            checks.add("food")
        elif name == "prn_max_per_day":
            replacements["prn_max_per_day"] = None
            checks.add("dose")
        elif name == "note":
            replacements["note"] = None
        else:
            return None
    # Missing form must not acquire the schema's tablet default during salvage.
    if "form" not in obj:
        replacements["form"] = "other"
        checks.add("schedule")
    replacements["needs_check"] = sorted(checks)
    try:
        med = MedLine.model_validate({**obj, **replacements})
    except ValidationError:
        return None
    return med, replacements
