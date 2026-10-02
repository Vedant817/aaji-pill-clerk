"""Deterministic schedule expansion. The LLM never does this maths."""

from datetime import date, timedelta

from pillclerk.schedule import expand, refill_date
from pillclerk.schema import Dose, MedLine, TaperStep


def test_101_makes_two_slots() -> None:
    med = MedLine(
        drug="Glycomet",
        strength="500 mg",
        dose=Dose(morning=1, night=1, unit="tab"),
        duration_days=30,
    )
    plan = expand([med], date(2026, 10, 2))
    assert [d.slot for d in plan] == ["morning", "night"]
    assert all(d.amount == 1 for d in plan)
    assert all(d.days == 30 for d in plan)


def test_taper_steps_are_sequential() -> None:
    med = MedLine(
        drug="Wysolone",
        kind="taper",
        taper=[
            TaperStep(dose=Dose(morning=1, night=1), days=5),
            TaperStep(dose=Dose(night=1), days=5),
        ],
        duration_days=10,
    )
    start = date(2026, 10, 2)
    plan = expand([med], start)
    assert plan[0].start == start
    later = [d for d in plan if d.start == start + timedelta(days=5)]
    assert later and all(d.slot == "night" for d in later)


def test_prn_has_no_timed_slots() -> None:
    med = MedLine(drug="Dolo", kind="prn", prn_max_per_day=3)
    assert expand([med], date(2026, 10, 2)) == []


def test_weekly_interval() -> None:
    med = MedLine(
        drug="Uprise D3",
        strength="60K IU",
        dose=Dose(morning=1, unit="cap"),
        every_n_days=7,
        duration_days=90,
    )
    plan = expand([med], date(2026, 10, 2))
    assert plan[0].every_n_days == 7


def test_refill_date() -> None:
    med = MedLine(drug="Pan", dose=Dose(morning=1, night=1, unit="tab"))
    start = date(2026, 10, 1)
    assert refill_date(med, start, 14) == start + timedelta(days=7)
