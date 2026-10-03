"""Review helpers: turn widget fields into a MedLine; track confirm progress."""

from __future__ import annotations

from typing import Any

from pillclerk.schema import CheckField, Dose, Food, Form, Kind, MedLine, Unit
from pillclerk.validate import extra_rules

WIDGET_PREFIX = "pc_r_"


def med_from_fields(
    *,
    line: str,
    drug: str,
    strength: str,
    form: Form,
    kind: Kind,
    food: Food,
    duration: int,
    every: int,
    morning: float,
    afternoon: float,
    night: float,
    unit: Unit,
    prn_max: int,
    taper: list | None = None,
) -> MedLine:
    checks: list[CheckField] = []
    if not (drug or "").strip():
        checks.append("drug")
    dose = None if kind == "prn" else Dose(
        morning=morning, afternoon=afternoon, night=night, unit=unit
    )
    if kind == "daily" and dose and (dose.morning + dose.afternoon + dose.night) == 0:
        checks.append("dose")
    taper_list = list(taper or [])
    next_kind: Kind = kind
    if kind == "taper" and not taper_list:
        next_kind = "daily"
        checks.append("schedule")
    return extra_rules(
        MedLine(
            drug=(drug or "").strip() or None,
            strength=(strength or "").strip() or None,
            form=form,
            kind=next_kind,
            dose=dose,
            every_n_days=int(every),
            taper=taper_list,
            food=food,
            duration_days=int(duration) or None,
            prn_max_per_day=int(prn_max) or None,
            needs_check=checks,
            note=line,
        )
    )


def n_confirmed(drafts: list[dict[str, Any]]) -> int:
    return sum(1 for d in drafts if d.get("confirmed"))


def next_unconfirmed(drafts: list[dict[str, Any]], after: int = -1) -> int | None:
    n = len(drafts)
    for j in range(after + 1, n):
        if not drafts[j].get("confirmed"):
            return j
    for j in range(0, after + 1):
        if j < n and not drafts[j].get("confirmed"):
            return j
    return None


def drafts_need_parse(drafts: list[dict[str, Any]]) -> bool:
    if not drafts:
        return False
    return all(not (d.get("gold") or {}).get("drug") for d in drafts)


def clear_widget_keys(state: dict[str, Any]) -> None:
    for key in list(state):
        if key.startswith(WIDGET_PREFIX):
            state.pop(key, None)


def clear_review_keys(state: dict[str, Any]) -> None:
    clear_widget_keys(state)
    for key in ("review_i", "parsed_once", "parse_note"):
        state.pop(key, None)
