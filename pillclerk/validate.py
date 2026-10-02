"""Pydantic + consistency rules. Failures become ASK after one retry."""

from __future__ import annotations

from pillclerk.schema import CheckField, MedLine


def extra_rules(med: MedLine) -> MedLine:
    checks: list[CheckField] = list(med.needs_check)
    if not med.drug and "drug" not in checks:
        checks.append("drug")
    if med.kind == "daily" and med.dose is None and "dose" not in checks:
        checks.append("dose")
    if med.kind == "taper" and not med.taper and "schedule" not in checks:
        checks.append("schedule")
    if med.kind == "prn" and med.dose and (med.dose.morning + med.dose.afternoon + med.dose.night):
        if "schedule" not in checks:
            checks.append("schedule")
    if checks == med.needs_check:
        return med
    return med.model_copy(update={"needs_check": checks})


def all_confirmed(meds: list[MedLine]) -> bool:
    return all(not m.needs_check for m in meds)
