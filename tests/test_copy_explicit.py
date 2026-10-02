from pillclerk.config import ROOT
from pillclerk.copy_explicit import copy_explicit
from pillclerk.infer import _extract_json
from pillclerk.drafts import drafts_from_text
from pillclerk.schema import Dose, MedLine
from pillclerk.templates import STYLES, render_template
from pillclerk.validate import extra_rules, schedule_conflicts


def test_copies_cap_and_food_from_the_line() -> None:
    med = MedLine(
        drug="Pan",
        strength="40 mg",
        form="tab",
        dose=Dose(morning=1, night=1, unit="tab"),
        food="any",
        duration_days=14,
    )
    line = "Cap Pan 40mg BD AC x14d"
    out = extra_rules(copy_explicit(med, line))
    assert out.form == "cap"
    assert out.dose is not None and out.dose.unit == "cap"
    assert out.food == "before"
    assert out.dose.morning == 1 and out.dose.night == 1


def test_no_food_token_is_any() -> None:
    med = MedLine(drug="Dolo", kind="prn", form="tab", food="after", prn_max_per_day=3)
    out = copy_explicit(med, "Tab Dolo 650mg SOS max 3/d x 3 DAYS")
    assert out.food == "any"


def test_one_over_twelve_is_thirty_days() -> None:
    med = MedLine(drug="Telma", dose=Dose(morning=1, unit="tab"), duration_days=1)
    out = copy_explicit(med, "Tab Telma 40mg OD ES 1/12")
    assert out.duration_days == 30
    assert out.food == "empty_stomach"


def test_does_not_invent_dose_slots() -> None:
    med = MedLine(drug="Pan", kind="daily", dose=None, needs_check=["dose"])
    out = copy_explicit(med, "Tab Pan 40mg as directed")
    assert out.dose is None
    assert "dose" in out.needs_check


def test_every_style_writes_a_form_token() -> None:
    gold = MedLine(
        drug="Asthalin",
        strength="100 mcg",
        form="inhaler",
        dose=Dose(morning=1, unit="puff"),
        food="any",
        duration_days=30,
    )
    for style in STYLES:
        line = render_template(gold, style)
        assert "Inh" in line or "INH" in line, (style, line)


def test_schedule_conflicts_same_drug_different_dose() -> None:
    a = MedLine(drug="Glycomet", dose=Dose(morning=1, night=1, unit="tab"), duration_days=30)
    b = MedLine(drug="Glycomet", dose=Dose(morning=1, unit="tab"), duration_days=30)
    found = schedule_conflicts([a, b])
    assert len(found) == 1
    assert found[0][0] == "glycomet"


def test_extract_json_strips_think_blocks() -> None:
    raw = '<think>plan</think>\n{"drug":"Pan","kind":"prn","needs_check":[]}'
    assert _extract_json(raw).startswith("{")


def test_demo_slip_loads_ten_ask_drafts() -> None:
    raw = (ROOT / "data" / "demo" / "prescriptions" / "aaji_sample.txt").read_text(encoding="utf-8")
    drafts = drafts_from_text(raw)
    assert len(drafts) == 10
    assert drafts[0]["line"].startswith("TAB. Glycomet")
    assert drafts[0]["gold"]["needs_check"]
    assert drafts[0]["confirmed"] is False


def test_schedule_conflicts_ignores_identical_copies() -> None:
    a = MedLine(drug="Telma", dose=Dose(morning=1, unit="tab"), duration_days=30)
    b = MedLine(drug="Telma", dose=Dose(morning=1, unit="tab"), duration_days=30)
    assert schedule_conflicts([a, b]) == []
