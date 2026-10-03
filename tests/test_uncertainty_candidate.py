import pytest

from pillclerk.render import to_chat_row
from pillclerk.schema import Dose, MedLine
from train.prepare_uncertainty import curate_units, omissions


def source(line, med):
    return {"line": line, "gold": med.model_dump(), **to_chat_row(line, med), "synthetic": True}


def test_missing_form_does_not_presume_a_brand_or_tablet():
    row = source("Tab TestOnly 10mg 1-0-1 x5d", MedLine(drug="TestOnly", strength="10mg", dose=Dose(morning=1, night=1), duration_days=5))
    result = omissions([row], 1)[0]
    med = MedLine.model_validate(result["gold"])
    assert result["line"] == "TestOnly 10mg 1-0-1 x5d"
    assert med.form == "other" and med.dose is None
    assert med.strength == "10mg" and med.duration_days == 5
    assert set(med.needs_check) == {"dose", "schedule"}
    assert row["gold"]["form"] == "tab"  # Original positive stays fixed.


def test_missing_liquid_unit_is_not_inferred_from_syrup_and_strength_is_preserved():
    med = MedLine(drug="TestOnly", strength="10mg", form="syrup", dose=Dose(morning=5, unit="ml"))
    row = source("Syr TestOnly 10mg 5ml OD", med)
    result = omissions([row], 1)[0]
    assert result["line"] == "Syr TestOnly 10mg 5 OD"
    assert result["gold"]["form"] == "syrup" and result["gold"]["dose"] is None
    assert result["gold"]["needs_check"] == ["dose"]
    concentration = source("Syr TestOnly 10mg/5ml 5ml OD", med.model_copy(update={"strength": "10mg/5ml"}))
    assert not omissions([concentration], 1)


def test_real_sources_rejected_and_existing_unit_cue_keeps_form_known():
    row = source("Tab TestOnly 1 tablet OD", MedLine(drug="TestOnly", dose=Dose(morning=1)))
    assert not omissions([row], 1)
    with pytest.raises(ValueError, match="synthetic"):
        omissions([{**row, "synthetic": False}], 1)


def test_unit_policy_versions_implicit_units_and_adds_written_positive():
    med = MedLine(drug="TestOnly", form="syrup", strength="10 mg/5 ml", dose=Dose(morning=5, night=5, unit="ml"), duration_days=5)
    row = source("Syr TestOnly 10mg/5ml 5-0-5 x5d", med)
    curated, changes, positives = curate_units([row], 1)
    assert curated[0]["gold"]["dose"] is None and curated[0]["gold"]["needs_check"] == ["dose"]
    assert len(changes) == len(positives) == 1
    assert positives[0]["line"] == "Syr TestOnly 10mg/5ml 5 ml-0 ml-5 ml x5d"
    assert positives[0]["gold"] == row["gold"]
    assert row["gold"]["dose"]["unit"] == "ml"
    clear = source(positives[0]["line"], med)
    assert curate_units([clear], 1) == ([clear], [], [])
