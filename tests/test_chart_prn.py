"""Printed PRN instructions must preserve copied food and course length."""
from datetime import date

import pytest
from icalendar import Calendar

from pillclerk.chart import chart_html
from pillclerk.ics import to_ics
from pillclerk.schedule import expand
from pillclerk.schema import MedLine


@pytest.mark.parametrize("language,food,days,maximum", [
    ("en", "after food", "3 days", "max 2/day"),
    ("mr", "जेवणानंतर", "3 दिवस", "कमाल 2/दिवस"),
    ("hi", "खाने के बाद", "3 दिन", "अधिकतम 2/दिन"),
])
def test_prn_food_and_duration_print_without_creating_timed_reminders(language, food, days, maximum):
    med = MedLine(drug="SyntheticPRN", kind="prn", food="after", duration_days=3, prn_max_per_day=2)
    plan = expand([med], date(2026, 10, 4))
    output = chart_html(plan, lang=language, prn=[med])
    assert food in output and days in output and maximum in output
    assert not Calendar.from_ical(to_ics(plan)).walk("VEVENT")


def test_prn_missing_food_and_duration_do_not_gain_instructions():
    med = MedLine(drug="SyntheticPRN", kind="prn", food="any", duration_days=None)
    output = chart_html([], lang="en", prn=[med])
    assert "after food" not in output and "before food" not in output
    assert "3 days" not in output and "until changed" not in output
