from datetime import date

import pytest
from icalendar import Calendar

from pillclerk.calendar_import import google_events
from pillclerk.ics import to_ics
from pillclerk.schedule import expand
from pillclerk.schema import Dose, MedLine


def exported():
    return to_ics(expand([MedLine(drug="Test-only medicine", dose=Dose(morning=.5),
                                     every_n_days=7, duration_days=30)], date(2026, 10, 4)))


def test_actual_export_preserves_quantity_interval_count_and_local_time():
    row = google_events(exported(), "Asia/Kolkata", synthetic=True)[0]
    p = row["payload"]
    assert p["start_time"] == "2026-10-04T08:00:00+05:30"
    assert p["end_time"] == "2026-10-04T08:10:00+05:30"
    assert "½ tab" in p["title"] and p["title"].startswith("[Synthetic test]")
    assert "COUNT=5" in p["recurrence"][0] and "INTERVAL=7" in p["recurrence"][0]
    assert p["reminders"]["overrides"] == [{"method": "popup", "minutes": 0}]
    assert not p["attendees"] and p["visibility"] == "private"


def test_duplicate_uid_and_unsupported_recurrence_do_not_silently_import():
    cal = Calendar.from_ical(exported())
    cal.add_component(cal.walk("VEVENT")[0])
    with pytest.raises(ValueError, match="unique"):
        google_events(cal.to_ical(), "Asia/Kolkata")
    cal = Calendar.from_ical(exported())
    cal.walk("VEVENT")[0]["RRULE"]["BYHOUR"] = [8]
    with pytest.raises(ValueError, match="recurrence"):
        google_events(cal.to_ical(), "Asia/Kolkata")


def test_ambiguous_dst_and_missing_alarms_require_review():
    from datetime import datetime
    cal = Calendar.from_ical(exported())
    event = cal.walk("VEVENT")[0]
    event.pop("DTSTART")
    event.add("DTSTART", datetime(2026, 11, 1, 1, 30))
    with pytest.raises(ValueError, match="Ambiguous"):
        google_events(cal.to_ical(), "America/New_York")
    cal = Calendar.from_ical(exported())
    cal.walk("VEVENT")[0].subcomponents.clear()
    with pytest.raises(ValueError, match="display"):
        google_events(cal.to_ical(), "Asia/Kolkata")
