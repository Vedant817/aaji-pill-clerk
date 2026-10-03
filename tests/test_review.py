from pillclerk.drafts import drafts_from_text
from pillclerk.review import (
    WIDGET_PREFIX,
    clear_review_keys,
    clear_widget_keys,
    drafts_need_parse,
    med_from_fields,
    n_confirmed,
    next_unconfirmed,
)
from pathlib import Path


def test_pasted_drafts_need_parse_until_drug_filled() -> None:
    drafts = drafts_from_text("Tab Atorva 10mg 0-0-1 after food x 30 days")
    assert drafts_need_parse(drafts)
    drafts[0]["gold"]["drug"] = "Atorva"
    assert not drafts_need_parse(drafts)


def test_confirm_progress_and_next_unconfirmed() -> None:
    drafts = drafts_from_text("line a\nline b\nline c")
    assert n_confirmed(drafts) == 0
    assert next_unconfirmed(drafts) == 0
    drafts[0]["confirmed"] = True
    assert next_unconfirmed(drafts, after=0) == 1
    drafts[1]["confirmed"] = True
    drafts[2]["confirmed"] = True
    assert n_confirmed(drafts) == 3
    assert next_unconfirmed(drafts) is None


def test_med_from_fields_asks_when_dose_empty() -> None:
    med = med_from_fields(
        line="Tab Atorva 10mg",
        drug="Atorva",
        strength="10mg",
        form="tab",
        kind="daily",
        food="after",
        duration=30,
        every=1,
        morning=0,
        afternoon=0,
        night=0,
        unit="tab",
        prn_max=0,
    )
    assert "dose" in med.needs_check
    ok = med_from_fields(
        line="Tab Atorva 10mg 0-0-1 after food x 30 days",
        drug="Atorva",
        strength="10mg",
        form="tab",
        kind="daily",
        food="after",
        duration=30,
        every=1,
        morning=0,
        afternoon=0,
        night=1,
        unit="tab",
        prn_max=0,
    )
    assert not ok.needs_check
    assert ok.drug == "Atorva"


def test_scan_switches_to_review_and_review_confirms_one_line() -> None:
    scan = Path("app/pages/1_Scan.py").read_text(encoding="utf-8")
    review = Path("app/pages/2_Review.py").read_text(encoding="utf-8")
    assert "switch_page" in scan
    assert "Load demo slip" not in scan
    assert "Confirm this line" in review
    assert "st.checkbox" not in review
    assert "WIDGET_PREFIX" in review


def test_clear_review_keys() -> None:
    state = {f"{WIDGET_PREFIX}0_drug": "Atorva", "review_i": 2, "drafts": [1], "other": 1}
    clear_review_keys(state)
    assert "review_i" not in state
    assert f"{WIDGET_PREFIX}0_drug" not in state
    assert state["drafts"] == [1]
    assert state["other"] == 1
    state = {f"{WIDGET_PREFIX}1_drug": "Telma", "parsed_once": True}
    clear_widget_keys(state)
    assert f"{WIDGET_PREFIX}1_drug" not in state
    assert state["parsed_once"] is True
