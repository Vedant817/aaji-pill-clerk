from datetime import date, time, timedelta

import pytest
from icalendar import Calendar

from eval.audit import align_predictions
from eval.report import mcnemar_exact
from pillclerk.chart import chart_html
from pillclerk.copy_explicit import copy_explicit
from pillclerk.review import export_blockers, updated_draft
from pillclerk.schedule import expand, refill_date
from pillclerk.schema import Dose, MedLine, TaperStep


def test_edit_revokes_signoff_and_conflicts_block_export():
    med = MedLine(drug="Example", dose=Dose(morning=1), duration_days=7)
    draft = {"line": "Tab Example 1-0-0 x7 days", "gold": med.model_dump(), "confirmed": True}
    assert updated_draft(draft, med)["confirmed"]
    changed = med.model_copy(update={"food": "after"})
    assert not updated_draft(draft, changed)["confirmed"]
    assert export_blockers([draft]) == []
    other = {**draft, "gold": changed.model_dump()}
    assert any("Conflicting" in b for b in export_blockers([draft, other]))


@pytest.mark.parametrize("line", ["Tab Example QID", "Tab Example twice per week",
                                    "Tab Example daily except Monday", "Tab Example 1 at 5pm",
                                    "Syp Example 5 ml every 6 hrly", "Tab Example [?] OD",
                                    "Nebulise with Example plus Other twice daily"])
def test_unrepresentable_or_uncertain_lines_never_export(line):
    med = MedLine(drug="Example", dose=Dose(morning=1))
    copied = copy_explicit(med, line)
    assert "schedule" in copied.needs_check
    # Even a manual checkbox sign-off cannot turn an unsupported schedule into three slots.
    assert export_blockers([{"line": line, "gold": med.model_dump(), "confirmed": True}])


def test_generic_notation_copy_without_drug_lookup():
    med = MedLine(drug="T UnseenName", dose=None, needs_check=["dose"])
    out = copy_explicit(med, "T UnseenName 2 times a day after dinner")
    assert out.drug == "UnseenName"
    assert out.food == "after"
    assert out.dose.morning == out.dose.night == 1


def test_taper_units_dates_and_configured_times_survive_exports():
    med = MedLine(drug="Example", kind="taper", form="syrup", taper=[
        TaperStep(dose=Dose(morning=5, unit="ml"), days=3),
        TaperStep(dose=Dose(morning=2, unit="ml"), days=2)])
    plan = expand([med], date(2026, 10, 3))
    times = {"morning": time(9, 15), "afternoon": time(14), "night": time(21)}
    html = chart_html(plan, lang="en", slot_times=times)
    assert "5 ml" in html and "2 ml" in html
    assert "2026-10-05" in html and "2026-10-06" in html and "09:15" in html
    events = Calendar.from_ical(to_ics(plan, slot_times=times)).walk("VEVENT")
    assert all("ml" in str(e["summary"]) for e in events)
    assert events[0].decoded("dtstart").time() == time(9, 15)


from pillclerk.ics import to_ics


def test_weekly_calendar_includes_last_dose_and_refill_uses_dosing_days():
    med = MedLine(drug="Example", dose=Dose(morning=1), every_n_days=7, duration_days=30)
    start = date(2026, 10, 3)
    event = Calendar.from_ical(to_ics(expand([med], start))).walk("VEVENT")[0]
    assert event["rrule"]["COUNT"] == [5]  # days 0, 7, 14, 21, 28
    assert refill_date(med, start, 4.5) == start + timedelta(days=28)
    assert refill_date(med, start, 5) is None


def test_pairing_rejects_duplicate_or_misaligned_evidence():
    with pytest.raises(ValueError, match="Duplicate"):
        align_predictions([{"line": "A"}], [{"line": "A"}, {"line": "A"}])
    with pytest.raises(ValueError, match="aligned"):
        mcnemar_exact([{"line": "A", "exact": 1}], [{"line": "B", "exact": 0}])


def test_app_parser_never_silently_uses_base_model(monkeypatch):
    from pillclerk.infer import get_parser
    monkeypatch.setenv("PARSER_BACKEND", "tinker")
    monkeypatch.setenv("PILLCLERK_TINKER_PATH", "")
    with pytest.raises(RuntimeError, match="Fine-tuned"):
        get_parser()


def test_training_leakage_fails_before_a_provider_call(tmp_path):
    from train.sft import validate_split
    with pytest.raises(ValueError, match="leakage"):
        validate_split([{"line": "Tab Example 1-0-0"}], [{"line": "Tab Example 1-0-0"}], [])
    assert validate_split([{"line": "Train"}], [{"line": "Validate"}], []) == {"validation": 0}
