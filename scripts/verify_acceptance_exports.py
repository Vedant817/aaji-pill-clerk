"""Verify actual browser export files against an external synthetic scenario.

Does not start the app, seed runtime data, or make hosted calls.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
import json
from pathlib import Path

from icalendar import Calendar


def verify(directory: Path) -> dict:
    case = json.loads((directory / "scenario.json").read_text(encoding="utf-8"))
    if case.get("synthetic") is not True or case.get("human_acceptance") is not False:
        raise ValueError("Only explicitly synthetic agent verification is supported")
    raw = (directory / "pillclerk.ics").read_bytes()
    events = Calendar.from_ical(raw).walk("VEVENT")
    expected = []
    for row in case["rows"]:
        med = row["gold"]
        if med["kind"] != "daily":
            raise ValueError("This verification fixture supports daily courses")
        for slot, hour in (("morning", 8), ("afternoon", 14), ("night", 21)):
            amount = med["dose"][slot]
            if amount:
                expected.append((med, hour, amount))
    assert len(events) == len(expected)
    assert len({str(e["UID"]) for e in events}) == len(events)
    checked = []
    for event, (med, hour, amount) in zip(events, expected, strict=True):
        start = event["DTSTART"].dt
        assert start.tzinfo is None  # Floating time in the importing calendar.
        assert start.hour == hour and start.minute == 0
        assert event["DTSTAMP"].dt.utcoffset() == timedelta(0)
        summary = str(event["SUMMARY"])
        quantity = "½" if amount == .5 else f"{amount:g}"
        assert f'{med["drug"]} {med["strength"]}: {quantity} {med["dose"]["unit"]}' in summary
        assert event["RRULE"]["COUNT"] == [med["duration_days"]]
        assert event["RRULE"]["INTERVAL"] == [med["every_n_days"]]
        alarms = event.walk("VALARM")
        assert len(alarms) == 1 and alarms[0]["TRIGGER"].dt == timedelta(0)
        assert str(alarms[0]["ACTION"]) == "DISPLAY"
        checked.append({"summary": summary, "start": start.isoformat(),
                        "occurrences": med["duration_days"], "alarm_seconds": 0})
    html = (directory / "fridge-chart.html").read_text(encoding="utf-8")
    assert "½" in html and "Not medical advice" in html
    for row in case["rows"]:
        assert row["gold"]["drug"] in html and row["gold"]["strength"] in html
    return {"synthetic": True, "human_acceptance": False,
            "phone_import_verified": False, "timezone": "floating local wall clock",
            "event_count": len(events), "events": checked, "chart_checks_passed": True}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--directory", type=Path, default=Path("artifacts/acceptance"))
    args = ap.parse_args()
    result = verify(args.directory)
    (args.directory / "export-verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
