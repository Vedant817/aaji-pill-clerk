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


def test_copies_combo_brand_and_devanagari_surface() -> None:
    telma = MedLine(drug="Telma", strength="40 mg/5 mg", form="tab", dose=Dose(morning=1, unit="tab"))
    out = copy_explicit(telma, "Tab Telma AM 40mg/5mg OD ES 1/12")
    assert out.drug == "Telma AM"
    assert out.strength == "40mg/5mg"
    hindi = MedLine(drug="Telma", strength="40 mg", form="tab", dose=Dose(morning=1, unit="tab"))
    out_h = copy_explicit(hindi, "टेल्मा 40 सुबह एक खाली पेट 30 दिन")
    assert out_h.drug == "टेल्मा"
    assert out_h.strength == "40"


def test_asks_when_frequency_is_missing() -> None:
    med = MedLine(
        drug="Ascoril LS",
        form="syrup",
        dose=Dose(morning=1, unit="ml"),
        food="after",
        duration_days=5,
        needs_check=[],
    )
    out = extra_rules(copy_explicit(med, "SYR. Ascoril LS AFTER FOOD x 5 DAYS"))
    assert out.dose is None
    assert "dose" in out.needs_check


def test_copies_insulin_units_and_three_time_words() -> None:
    lantus = MedLine(
        drug="Lantus",
        strength="12 unit",
        form="tab",
        dose=Dose(morning=0, night=1, unit="unit"),
    )
    out = extra_rules(copy_explicit(lantus, "Lantus 12 unit raat ko"))
    assert out.form == "injection"
    assert out.strength is None
    assert out.dose is not None and out.dose.night == 12 and out.dose.morning == 0
    tears = MedLine(
        drug="Refresh Tears",
        form="drops",
        dose=Dose(morning=1, unit="drop"),
        duration_days=15,
    )
    out_t = extra_rules(copy_explicit(tears, "Refresh Tears drops subah dopahar raat 15 din"))
    assert out_t.dose is not None
    assert (out_t.dose.morning, out_t.dose.afternoon, out_t.dose.night) == (1, 1, 1)
    assert out_t.dose.unit == "drop"


def test_english_frequency_and_ml_dose_from_the_line() -> None:
    niveoli = MedLine(
        drug="Niveoli",
        strength="100mg",
        form="inhaler",
        dose=None,
        needs_check=["dose", "schedule"],
    )
    out = extra_rules(copy_explicit(niveoli, "Inh Niveoli (100mg) 2 puff x twice a day (Rinse throat)"))
    assert out.dose is not None
    assert (out.dose.morning, out.dose.afternoon, out.dose.night) == (2.0, 0.0, 2.0)
    assert out.dose.unit == "puff"
    assert "dose" not in (out.needs_check or [])

    night = MedLine(drug="Montair", strength="10mg", form="tab", dose=None, needs_check=["dose"])
    out_n = extra_rules(copy_explicit(night, "Tab Montair (10mg) 1 tab x at night"))
    assert out_n.dose is not None and out_n.dose.morning == 0 and out_n.dose.night == 1

    daily = MedLine(drug="Rejunex CD3", form="tab", dose=None, needs_check=["dose"])
    out_d = extra_rules(copy_explicit(daily, "Rejunex CD3 1 daily"))
    assert out_d.dose is not None and out_d.dose.morning == 1 and out_d.dose.night == 0

    syr = MedLine(
        drug="Allegra",
        strength="5 ml",
        form="syrup",
        dose=None,
        needs_check=["dose"],
    )
    out_s = extra_rules(copy_explicit(syr, "Syrup Allegra 5 ml Twice a day X 4 Days"))
    assert out_s.strength is None
    assert out_s.dose is not None
    assert (out_s.dose.morning, out_s.dose.night) == (5.0, 5.0)
    assert out_s.dose.unit == "ml"
    assert out_s.duration_days == 4


def test_combo_suffix_mdi_stat_bbf_and_month() -> None:
    levo = MedLine(drug="Levolin MDI", form="inhaler", kind="prn", dose=None)
    out_l = extra_rules(copy_explicit(levo, "Inh Levolin MDI 2 puff x SOS"))
    assert out_l.drug == "Levolin"
    assert out_l.kind == "prn"
    assert out_l.dose is None

    amb = MedLine(drug="Ambrolite", strength="5 ml", form="syrup", dose=None, needs_check=["dose"])
    out_a = extra_rules(copy_explicit(amb, "Syrup Ambrolite S 5 ml Twice a day X 3 Days"))
    assert out_a.drug == "Ambrolite S"

    pan = MedLine(drug="Pan", strength="40", form="injection", kind="daily", dose=None, needs_check=["dose"])
    out_p = extra_rules(copy_explicit(pan, "Inj Pan 40 IV stat"))
    assert out_p.kind == "prn"

    fam = MedLine(drug="Famocid", strength="40", form="tab", dose=None, needs_check=["dose"])
    out_f = extra_rules(copy_explicit(fam, "Tab Famocid (40) 1 BBF x 1 month"))
    assert out_f.food == "empty_stomach"
    assert out_f.dose is not None and out_f.dose.morning == 1
    assert out_f.duration_days == 30

    nex = MedLine(drug="Nexito", strength="10", form="tab", dose=Dose(morning=1, unit="tab"), food="any")
    out_x = extra_rules(copy_explicit(nex, "Tab Nexito (10) 1 OD after BF x 2 months"))
    assert out_x.food == "after"
    assert out_x.duration_days == 60


def test_ml_triple_and_insulin_strength_cleared() -> None:
    aug = MedLine(
        drug="Augmentin",
        strength="5ml",
        form="syrup",
        dose=Dose(morning=0, night=5, unit="ml"),
    )
    out = extra_rules(copy_explicit(aug, "Syp Augmentin DDS 5ml-0-5ml x 5 days"))
    assert out.drug == "Augmentin DDS"
    assert out.dose is not None
    assert (out.dose.morning, out.dose.afternoon, out.dose.night) == (5.0, 0.0, 5.0)
    assert out.strength is None

    lantus = MedLine(
        drug="Lantus Solostar",
        strength="10",
        form="injection",
        dose=Dose(morning=0, night=10, unit="unit"),
    )
    out_i = extra_rules(copy_explicit(lantus, "Inj Lantus Solostar 10 units SC at 10PM"))
    assert out_i.strength is None
    assert out_i.dose is not None and out_i.dose.night == 10
    assert "schedule" in out_i.needs_check  # 10PM cannot be silently replaced by the night default


def test_stub_from_line_copies_suspension() -> None:
    from pillclerk.copy_explicit import stub_from_line

    stub = extra_rules(copy_explicit(stub_from_line("Suspension Looz 10 ml Once a day X 1 Month"), "Suspension Looz 10 ml Once a day X 1 Month"))
    assert stub.drug == "Looz"
    assert stub.form == "syrup"
    assert stub.dose is not None and stub.dose.morning == 10
    assert stub.duration_days == 30


def test_mixed_in_ml_is_not_the_dose() -> None:
    med = MedLine(
        drug="Laxopeg",
        strength="17 GM",
        form="sachet",
        dose=None,
        needs_check=["dose"],
    )
    line = "Laxopeg Sachet (17 GM) 1 Twice a day X 1 Month Mixed in 200 ml water or juice"
    out = extra_rules(copy_explicit(med, line))
    assert out.dose is not None
    assert (out.dose.morning, out.dose.night) == (1.0, 1.0)
    assert out.dose.unit == "sachet"


def test_half_tab_triple_not_wiped() -> None:
    med = MedLine(
        drug="Galvus Met",
        form="tab",
        dose=Dose(morning=0.5, afternoon=0.0, night=0.5, unit="tab"),
    )
    out = extra_rules(copy_explicit(med, "Tab Galvus Met 50/500 ½-0-½ after food x 30d"))
    assert out.drug == "Galvus Met"
    assert out.dose is not None
    assert (out.dose.morning, out.dose.night) == (0.5, 0.5)


def test_raat_ko_ek_is_night_only() -> None:
    med = MedLine(
        drug="Telma AM",
        form="tab",
        dose=Dose(morning=1, night=1, unit="tab"),
        duration_days=30,
    )
    out = copy_explicit(med, "Tab Telma AM 40 mg/5 mg raat ko ek 30 din")
    assert out.dose is not None and out.dose.morning == 0 and out.dose.night == 1


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


def test_pasted_lines_become_ask_drafts() -> None:
    raw = "Tab Atorva 10mg 0-0-1 after food x 30 days\nTab Telma 40mg 1-0-0 empty stomach x 30 days"
    drafts = drafts_from_text(raw)
    assert len(drafts) == 2
    assert drafts[0]["gold"]["drug"] is None
    assert drafts[0]["gold"]["needs_check"]
    assert drafts[0]["confirmed"] is False
    scan = (ROOT / "app" / "pages" / "1_Scan.py").read_text(encoding="utf-8")
    assert "Load demo slip" not in scan
    assert "aaji_sample" not in scan
    assert "Glycomet" not in scan


def test_schedule_conflicts_ignores_identical_copies() -> None:
    a = MedLine(drug="Telma", dose=Dose(morning=1, unit="tab"), duration_days=30)
    b = MedLine(drug="Telma", dose=Dose(morning=1, unit="tab"), duration_days=30)
    assert schedule_conflicts([a, b]) == []
