import json

import pytest

from pillclerk.infer import process_completion
from pillclerk.schema import Dose, MedLine


def test_invalid_form_keeps_valid_fields_but_requires_review():
    raw = MedLine(drug="TestOnly", strength="10 mg", dose=Dose(morning=1), duration_days=5).model_dump()
    raw["form"] = "unsupported"
    pred, meta = process_completion(json.dumps(raw), "TestOnly 10 mg 1-0-0 x5d")
    assert pred.drug == "TestOnly" and pred.strength == "10 mg"
    assert pred.dose == Dose(morning=1) and pred.duration_days == 5
    assert pred.form == "other" and "schedule" in pred.needs_check
    assert not meta["raw_schema_valid"] and meta["recovery_kind"] == "fields"


@pytest.mark.parametrize("bad_unit", ["tsp", "mg", "unknown"])
def test_invalid_unit_never_becomes_an_inferred_volume(bad_unit):
    raw = MedLine(drug="TestOnly", form="syrup", dose=Dose(morning=2, unit="ml"), duration_days=5).model_dump()
    raw["dose"]["unit"] = bad_unit
    pred, meta = process_completion(json.dumps(raw), f"Syr TestOnly 2 {bad_unit} OD x5d")
    assert pred.drug == "TestOnly" and pred.duration_days == 5
    assert pred.dose is None and "dose" in pred.needs_check
    assert meta["withheld_fields"] == ["dose"]


def test_invalid_taper_withholds_entire_schedule_without_losing_name():
    raw = MedLine(drug="TestOnly", dose=Dose(morning=1)).model_dump()
    raw.update(kind="taper", taper=[{"dose": {"morning": 1, "unit": "unknown"}, "days": 3}])
    pred, _ = process_completion(json.dumps(raw), "Tab TestOnly 1-0-0 x3d then as directed")
    assert pred.drug == "TestOnly" and not pred.taper and pred.dose is None
    assert {"dose", "schedule"} <= set(pred.needs_check)


def test_root_consistency_and_invalid_ASK_list_use_source_stub():
    raw = MedLine(drug="TestOnly", dose=Dose(morning=1)).model_dump()
    for update in ({"needs_check": ["invalid"]}, {"kind": "taper"}):
        _, meta = process_completion(json.dumps({**raw, **update}), "Tab TestOnly 1-0-0")
        assert meta["recovery_kind"] == "source_stub"


def test_valid_completion_behavior_and_raw_validity_unchanged():
    med = MedLine(drug="TestOnly", dose=Dose(morning=1), duration_days=5)
    pred, meta = process_completion(med.model_dump_json(), "Tab TestOnly 1-0-0 x5d")
    assert pred == med and meta["raw_schema_valid"] and not meta["recovery_used"]


def test_valid_model_uncertainty_survives_source_copy_and_keeps_dose_null():
    med = MedLine(drug="TestOnly", form="other", dose=None, needs_check=["dose", "schedule"])
    pred, meta = process_completion(med.model_dump_json(), "TestOnly 1-0-1 x5d")
    assert pred.dose is None and {"dose", "schedule"} <= set(pred.needs_check)
    assert meta["raw_schema_valid"] and not meta["recovery_used"]
