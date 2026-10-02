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


def schedule_conflicts(meds: list[MedLine]) -> list[tuple[str, MedLine, MedLine]]:
    """Same drug name, different dose/kind/food. Clerk surfaces both; never picks."""
    found: list[tuple[str, MedLine, MedLine]] = []
    by_name: dict[str, list[MedLine]] = {}
    for med in meds:
        if not med.drug:
            continue
        by_name.setdefault(med.drug.lower(), []).append(med)
    for name, group in by_name.items():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                same = (
                    a.kind == b.kind
                    and a.every_n_days == b.every_n_days
                    and (a.dose.model_dump() if a.dose else None) == (b.dose.model_dump() if b.dose else None)
                )
                if not same:
                    found.append((name, a, b))
    return found
