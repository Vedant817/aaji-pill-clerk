""".ics reminders: one event per slot, alarm at dose time."""

from datetime import date

from pillclerk.ics import to_ics
from pillclerk.schedule import expand
from pillclerk.schema import Dose, MedLine
from icalendar import Calendar


def test_ics_has_two_events_for_bd() -> None:
    med = MedLine(drug="Telma", strength="40 mg", dose=Dose(morning=1, night=1), duration_days=10)
    raw = to_ics(expand([med], date(2026, 10, 2))).decode("utf-8")
    assert raw.count("BEGIN:VEVENT") == 2
    assert "Telma" in raw
    assert "BEGIN:VALARM" in raw
    assert "FREQ=DAILY" in raw


def test_weekly_rrule_interval() -> None:
    med = MedLine(
        drug="Calcirol",
        dose=Dose(morning=1, unit="sachet"),
        every_n_days=7,
        duration_days=30,
    )
    raw = to_ics(expand([med], date(2026, 10, 2))).decode("utf-8")
    assert "INTERVAL=7" in raw


def test_calendar_events_have_required_properties_and_local_wall_clock():
    med = MedLine(drug="Test-only", dose=Dose(morning=1, night=.5), duration_days=7)
    raw = to_ics(expand([med], date(2026, 10, 4)))
    events = Calendar.from_ical(raw).walk("VEVENT")
    assert len(events) == 2
    assert len({str(e["UID"]) for e in events}) == 2
    for event in events:
        assert event["DTSTAMP"].dt.utcoffset().total_seconds() == 0
        assert event["DTSTART"].dt.tzinfo is None  # Phone's local wall clock.
        assert event["RRULE"]["COUNT"] == [7]
        assert len(event.walk("VALARM")) == 1
        assert event.walk("VALARM")[0]["TRIGGER"].dt.total_seconds() == 0
