"""Agent-operated role checks; fixtures are synthetic and storage is temporary."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from pillclerk import config, store
from pillclerk.drafts import drafts_from_text
from pillclerk.schema import Dose, MedLine

ROOT = Path(__file__).resolve().parents[1]


def page(name, drafts=None):
    at = AppTest.from_file(str(ROOT / f"app/pages/{name}.py"), default_timeout=10)
    if drafts is not None:
        at.session_state["drafts"] = drafts
    return at.run()


def routing(monkeypatch):
    import streamlit as st
    destinations = []
    monkeypatch.setattr(st, "page_link", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "switch_page", lambda target: destinations.append(target))
    monkeypatch.setattr(config, "tinker_parser_ready", lambda: False)
    monkeypatch.setenv("PARSER_BACKEND", "tinker")
    return destinations


def button(at, label):
    return next(widget for widget in at.button if widget.label == label)


def test_caregiver_corrects_ask_exports_then_edit_locks_chart(monkeypatch):
    destinations = routing(monkeypatch)
    source = "Tab SyntheticA 10mg 1-0-0 x7 days"
    scan = page("1_Scan")
    assert scan.text_area[0].value == "" and "drafts" not in scan.session_state
    button(scan, "Load lines").click().run()
    assert scan.warning and not destinations
    scan.text_area[0].set_value(source)
    button(scan, "Load lines").click().run()
    assert destinations == ["pages/2_Review.py"]
    drafts = scan.session_state["drafts"]
    review = page("2_Review", drafts)
    assert not review.exception and button(review, "Confirm this line").disabled
    # Checking ASK attestations alone cannot create the missing drug or dose.
    for check in review.checkbox:
        check.check()
    review.run()
    assert button(review, "Confirm this line").disabled
    review.text_input(key="pc_r_0_drug").set_value("SyntheticA")
    review.text_input(key="pc_r_0_str").set_value("10mg")
    review.number_input(key="pc_r_0_am").set_value(1.0)
    review.number_input(key="pc_r_0_dur").set_value(7)
    review.run()
    assert not button(review, "Confirm this line").disabled
    button(review, "Confirm this line").click().run()
    assert destinations[-1] == "pages/3_Chart.py"
    confirmed = review.session_state["drafts"]
    chart = page("3_Chart", confirmed)
    assert not chart.exception and len(chart.get("download_button")) == 2
    assert chart.number_input[0].value is None
    chart.number_input[0].set_value(3.0).run()
    assert any("Stock runs out" in widget.value for widget in chart.markdown)
    review.text_input(key="pc_r_0_str").set_value("20mg").run()
    assert not review.session_state["drafts"][0]["confirmed"]
    locked = page("3_Chart", review.session_state["drafts"])
    assert not locked.get("download_button")


def test_parser_failure_stays_ask_and_new_scan_clears_old_signoffs(monkeypatch):
    routing(monkeypatch)
    import pillclerk.infer as infer
    monkeypatch.setattr(config, "tinker_parser_ready", lambda: True)
    def unavailable():
        raise RuntimeError("test-only backend unavailable")
    monkeypatch.setattr(infer, "get_parser", unavailable)
    at = page("2_Review", drafts_from_text("Tab SyntheticA [?]"))
    assert not at.exception and "Parser unavailable" in at.session_state["parse_note"]
    assert button(at, "Confirm this line").disabled
    assert not at.session_state["drafts"][0]["confirmed"]
    scan = page("1_Scan", at.session_state["drafts"])
    scan.session_state["parsed_once"] = True
    scan.session_state["pc_r_0_resolve_drug"] = True
    scan.text_area[0].set_value("Tab SyntheticB 5mg 0-0-1 x3 days")
    button(scan, "Load lines").click().run()
    assert "parsed_once" not in scan.session_state
    assert "pc_r_0_resolve_drug" not in scan.session_state
    assert len(scan.session_state["drafts"]) == 1
    assert not scan.session_state["drafts"][0]["confirmed"]


def test_saved_revisions_visible_and_user_text_is_literal(tmp_path, monkeypatch):
    path = tmp_path / "role-history.db"
    old = MedLine(drug="SyntheticA", strength="10mg", dose=Dose(morning=1))
    new = old.model_copy(update={"drug": "<b>SyntheticA</b>", "dose": Dose(night=.5)})
    store.save_meds([old], note="Earlier synthetic source", path=path)
    store.save_meds([new], note="<b>Changed synthetic source</b>", path=path)
    assert store.load_meds(path) == [new]
    revisions = store.load_history(path)
    assert [r["meds"] for r in revisions] == [[new], [old]]
    assert len(store.load_history(path, limit=1)) == 1
    load, history = store.load_meds, store.load_history
    monkeypatch.setattr(store, "load_meds", lambda: load(path))
    monkeypatch.setattr(store, "load_history", lambda: history(path))
    at = page("4_History")
    assert not at.exception and len(at.expander) == 2
    assert len(at.table) == 2
    assert any("&lt;b&gt;SyntheticA&lt;/b&gt;" in item.value for item in at.markdown)
    assert at.text[0].value == "<b>Changed synthetic source</b>"
    assert at.table[1].value.iloc[0]["Medicine"] == old.drug
    assert at.table[1].value.iloc[0]["Morning"] == old.dose.morning
    assert at.table[0].value.iloc[0]["Night"] == new.dose.night
