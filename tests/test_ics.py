""".ics reminders: one event per slot, alarm at dose time."""

from datetime import date

from pillclerk.ics import to_ics
from pillclerk.schedule import expand
from pillclerk.schema import Dose, MedLine


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
