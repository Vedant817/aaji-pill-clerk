"""One recurring .ics event per medicine slot, with an alarm at the dose time."""

from __future__ import annotations

from datetime import datetime, timedelta, time, timezone
from hashlib import sha256

from icalendar import Alarm, Calendar, Event

from pillclerk.schedule import SLOTS, Dosing


def frac(x: float) -> str:
    return {0.5: "½", 1.5: "1½"}.get(x, f"{x:g}")


def to_ics(plan: list[Dosing], slot_times: dict[str, time] | None = None) -> bytes:
    times = slot_times or SLOTS
    cal = Calendar()
    cal.add("prodid", "-//Pill Clerk//EN")
    cal.add("version", "2.0")
    exported_at = datetime.now(timezone.utc)
    for i, d in enumerate(plan):
        unit = d.unit
        summary = f"💊 {d.med.drug} {d.med.strength or ''}: {frac(d.amount)} {unit} ({d.med.food})"
        ev = Event()
        ev.add("dtstamp", exported_at)
        ev.add("summary", summary)
        ev.add("dtstart", datetime.combine(d.start, times[d.slot]))
        ev.add("duration", timedelta(minutes=10))
        rule: dict = {"freq": "daily", "interval": d.every_n_days}
        if d.days:
            rule["count"] = (d.days + d.every_n_days - 1) // d.every_n_days
        ev.add("rrule", rule)
        identity = f"{d.med.model_dump_json()}|{d.slot}|{d.start}|{times[d.slot]}|{d.amount}|{i}"
        ev.add("uid", f"pillclerk-{sha256(identity.encode()).hexdigest()}@local")
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", summary)
        alarm.add("trigger", timedelta(0))
        ev.add_component(alarm)
        cal.add_component(ev)
    return cal.to_ical()
