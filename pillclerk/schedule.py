"""Deterministic day-by-slot expansion. The LLM never does this maths."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta

from pillclerk.schema import MedLine

SLOTS = {"morning": time(8, 0), "afternoon": time(14, 0), "night": time(21, 0)}


@dataclass
class Dosing:
    med: MedLine
    slot: str
    amount: float
    start: date
    days: int | None
    every_n_days: int = 1


def expand(meds: list[MedLine], start: date) -> list[Dosing]:
    out: list[Dosing] = []
    for m in meds:
        if m.kind == "daily" and m.dose:
            for s in SLOTS:
                amt = getattr(m.dose, s)
                if amt > 0:
                    out.append(Dosing(m, s, amt, start, m.duration_days, m.every_n_days))
        elif m.kind == "taper":
            d0 = start
            for step in m.taper:
                for s in SLOTS:
                    amt = getattr(step.dose, s)
                    if amt > 0:
                        out.append(Dosing(m, s, amt, d0, step.days, 1))
                d0 += timedelta(days=step.days)
        # prn: on the chart as "only if needed"; no timed reminders
    return out


def refill_date(m: MedLine, start: date, units_in_stock: float) -> date | None:
    if not m.dose:
        return None
    per_day = (m.dose.morning + m.dose.afternoon + m.dose.night) / m.every_n_days
    if per_day <= 0:
        return None
    return start + timedelta(days=int(units_in_stock // per_day))


def prn_meds(meds: list[MedLine]) -> list[MedLine]:
    return [m for m in meds if m.kind == "prn"]
