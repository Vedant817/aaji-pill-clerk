from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from streamlit.testing.v1 import AppTest

from pillclerk.schema import Dose, MedLine


def test_review_edit_revokes_confirmation_and_preserves_parser_ask(monkeypatch):
    import streamlit as st
    from pillclerk import config
    monkeypatch.setattr(config, "tinker_parser_ready", lambda: False)
    monkeypatch.setenv("PARSER_BACKEND", "tinker")
    # Test page widgets independently of Streamlit's multipage routing.
    monkeypatch.setattr(st, "page_link", lambda *args, **kwargs: None)
    line = "Tab Example 1-0-0"
    med = MedLine(drug="Example", dose=Dose(morning=1), note=line)
    at = AppTest.from_file(str(ROOT / "app/pages/2_Review.py"))
    at.session_state["drafts"] = [{"line": line, "gold": med.model_dump(), "confirmed": True}]
    at.run()
    assert not at.exception
    assert at.session_state["drafts"][0]["confirmed"]
    at.text_input(key="pc_r_0_drug").set_value("Edited").run()
    assert not at.exception
    assert not at.session_state["drafts"][0]["confirmed"]

    med = med.model_copy(update={"needs_check": ["strength"]})
    at = AppTest.from_file(str(ROOT / "app/pages/2_Review.py"))
    at.session_state["drafts"] = [{"line": line, "gold": med.model_dump(), "confirmed": False}]
    at.run()
    assert not at.exception
    assert "strength" in at.session_state["drafts"][0]["gold"]["needs_check"]
    confirm = next(b for b in at.button if b.label == "Confirm this line")
    assert confirm.disabled
    at.checkbox(key="pc_r_0_resolve_strength").check().run()
    assert not at.session_state["drafts"][0]["gold"]["needs_check"]


def test_chart_stock_is_blank_per_medicine_and_conflicts_stop_exports():
    med = MedLine(drug="Example", dose=Dose(morning=1))
    line = "Tab Example 1-0-0"
    draft = {"line": line, "gold": med.model_dump(), "confirmed": True}
    at = AppTest.from_file(str(ROOT / "app/pages/3_Chart.py"))
    at.session_state["drafts"] = [draft]
    at.run()
    assert not at.exception
    assert len(at.number_input) == 1 and at.number_input[0].value is None
    at = AppTest.from_file(str(ROOT / "app/pages/3_Chart.py"))
    changed = med.model_copy(update={"strength": "10 mg"})
    at.session_state["drafts"] = [draft, {**draft, "gold": changed.model_dump()}]
    at.run()
    assert not at.exception
    assert not at.get("download_button")
    assert not at.number_input


def test_review_restores_draft_and_resolved_ask_after_page_widget_cleanup(monkeypatch):
    import streamlit as st
    from pillclerk import config
    monkeypatch.setattr(config, "tinker_parser_ready", lambda: False)
    monkeypatch.setenv("PARSER_BACKEND", "tinker")
    monkeypatch.setattr(st, "page_link", lambda *args, **kwargs: None)
    line = "Tab Example 10 mg 1-0-0 x7d"
    med = MedLine(drug="Example", strength="10 mg", duration_days=7,
                  dose=Dose(morning=1), note=line)
    # Streamlit removes page-specific widgets on navigation but keeps non-widget
    # state. Model the exact state observed after visiting Chart in the browser.
    at = AppTest.from_file(str(ROOT / "app/pages/2_Review.py"))
    at.session_state["pc_r_0_seeded"] = True
    at.session_state["drafts"] = [{"line": line, "gold": med.model_dump(),
        "confirmed": True, "parser_checks": ["strength"], "resolved_checks": ["strength"]}]
    at.run()
    assert not at.exception
    assert at.text_input(key="pc_r_0_drug").value == "Example"
    assert at.number_input(key="pc_r_0_am").value == 1
    assert at.checkbox(key="pc_r_0_resolve_strength").value
    assert at.session_state["drafts"][0]["confirmed"]
    assert not at.session_state["drafts"][0]["gold"]["needs_check"]
