"""Deterministic day-by-slot expansion. The LLM never does this maths."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta

from pillclerk.schema import MedLine, Unit

SLOTS = {"morning": time(8, 0), "afternoon": time(14, 0), "night": time(21, 0)}


@dataclass
class Dosing:
    med: MedLine
    slot: str
    amount: float
    start: date
    days: int | None
    every_n_days: int = 1
    unit: Unit = "tab"


def expand(meds: list[MedLine], start: date) -> list[Dosing]:
    out: list[Dosing] = []
    for m in meds:
        if m.kind == "daily" and m.dose:
            for s in SLOTS:
                amt = getattr(m.dose, s)
                if amt > 0:
                    out.append(Dosing(m, s, amt, start, m.duration_days, m.every_n_days, m.dose.unit))
        elif m.kind == "taper":
            d0 = start
            for step in m.taper:
                for s in SLOTS:
                    amt = getattr(step.dose, s)
                    if amt > 0:
                        out.append(Dosing(m, s, amt, d0, step.days, 1, step.dose.unit))
                d0 += timedelta(days=step.days)
        # prn: on the chart as "only if needed"; no timed reminders
    return out


def refill_date(m: MedLine, start: date, units_in_stock: float) -> date | None:
    if units_in_stock < 0:
        raise ValueError("Stock must be nonnegative")
    if m.kind != "daily" or not m.dose:
        return None
    per_dosing_day = m.dose.morning + m.dose.afternoon + m.dose.night
    if per_dosing_day <= 0:
        return None
    # First dosing day on which the entered stock cannot cover all slots.
    days = int(units_in_stock // per_dosing_day) * m.every_n_days
    if m.duration_days is not None and days >= m.duration_days:
        return None
    return start + timedelta(days=days)


def prn_meds(meds: list[MedLine]) -> list[MedLine]:
    return [m for m in meds if m.kind == "prn"]
