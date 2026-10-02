"""MedLine copies what is written. Unclear fields must be flagged, never guessed."""

import pytest
from pydantic import ValidationError

from pillclerk.schema import SYSTEM_PROMPT, Dose, MedLine, TaperStep


def test_daily_101_is_valid() -> None:
    line = MedLine(
        drug="Glycomet",
        strength="500 mg",
        form="tab",
        kind="daily",
        dose=Dose(morning=1, afternoon=0, night=1, unit="tab"),
        food="after",
        duration_days=30,
    )
    assert line.dose is not None
    assert line.dose.morning == 1
    assert line.needs_check == []


def test_more_than_four_tablets_in_a_slot_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Dose(morning=5, unit="tab")


def test_insulin_units_may_exceed_four() -> None:
    dose = Dose(morning=10, unit="unit")
    assert dose.morning == 10


def test_taper_without_steps_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MedLine(drug="Wysolone", kind="taper", taper=[])


def test_daily_without_dose_must_be_flagged() -> None:
    with pytest.raises(ValidationError):
        MedLine(drug="Pan", kind="daily", dose=None, needs_check=[])
    flagged = MedLine(drug="Pan", kind="daily", dose=None, needs_check=["dose"])
    assert "dose" in flagged.needs_check


def test_prn_cannot_have_fixed_slots() -> None:
    with pytest.raises(ValidationError):
        MedLine(
            drug="Dolo",
            kind="prn",
            dose=Dose(morning=1, unit="tab"),
        )
    ok = MedLine(drug="Dolo", kind="prn", prn_max_per_day=3)
    assert ok.dose is None


def test_taper_with_steps_is_valid() -> None:
    line = MedLine(
        drug="Wysolone",
        kind="taper",
        taper=[
            TaperStep(dose=Dose(morning=1, night=1), days=5),
            TaperStep(dose=Dose(night=1), days=5),
        ],
        duration_days=10,
    )
    assert len(line.taper) == 2


def test_json_schema_is_object() -> None:
    schema = MedLine.model_json_schema()
    assert schema["type"] == "object"
    assert "drug" in schema["properties"]
    assert "needs_check" in schema["properties"]


def test_system_prompt_forbids_guessing() -> None:
    assert "Never guess" in SYSTEM_PROMPT
    assert "needs_check" in SYSTEM_PROMPT


def test_dump_roundtrip() -> None:
    line = MedLine(
        drug="Telma",
        strength="40 mg",
        dose=Dose(morning=1, unit="tab"),
        food="empty_stomach",
        duration_days=90,
    )
    again = MedLine.model_validate_json(line.model_dump_json())
    assert again.drug == "Telma"
    assert again.food == "empty_stomach"
