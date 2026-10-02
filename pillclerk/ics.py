"""One recurring .ics event per medicine slot, with an alarm at the dose time."""

from __future__ import annotations

from datetime import datetime, timedelta

from icalendar import Alarm, Calendar, Event

from pillclerk.schedule import SLOTS, Dosing


def frac(x: float) -> str:
    return {0.5: "½", 1.5: "1½"}.get(x, f"{x:g}")


def to_ics(plan: list[Dosing]) -> bytes:
    cal = Calendar()
    cal.add("prodid", "-//Pill Clerk//EN")
    cal.add("version", "2.0")
    for i, d in enumerate(plan):
        unit = d.med.dose.unit if d.med.dose else "tab"
        summary = f"💊 {d.med.drug} {d.med.strength or ''}: {frac(d.amount)} {unit} ({d.med.food})"
        ev = Event()
        ev.add("summary", summary)
        ev.add("dtstart", datetime.combine(d.start, SLOTS[d.slot]))
        ev.add("duration", timedelta(minutes=10))
        rule: dict = {"freq": "daily", "interval": d.every_n_days}
        if d.days:
            rule["count"] = max(1, d.days // d.every_n_days)
        ev.add("rrule", rule)
        ev.add("uid", f"pillclerk-{i}-{d.start.isoformat()}@local")
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", summary)
        alarm.add("trigger", timedelta(0))
        ev.add_component(alarm)
        cal.add_component(ev)
    return cal.to_ical()
