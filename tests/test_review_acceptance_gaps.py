"""Reproduced QA/PM role findings, tested with synthetic isolated inputs."""
from datetime import date
from pathlib import Path

import pytest
from icalendar import Calendar
from streamlit.testing.v1 import AppTest

from pillclerk import config
from pillclerk.calendar_import import google_events
from pillclerk.chart import chart_html
from pillclerk.ics import to_ics
from pillclerk.review import export_blockers
from pillclerk.schedule import expand
from pillclerk.schema import Dose, MedLine

ROOT = Path(__file__).resolve().parents[1]


def review(monkeypatch, med, source):
    import streamlit as st
    monkeypatch.setattr(st, "page_link", lambda *args, **kwargs: None)
    monkeypatch.setattr(config, "tinker_parser_ready", lambda: False)
    monkeypatch.setenv("PARSER_BACKEND", "tinker")
    at = AppTest.from_file(str(ROOT / "app/pages/2_Review.py"), default_timeout=10)
    at.session_state["drafts"] = [{"line": source, "gold": med.model_dump(), "confirmed": True}]
    return at.run()


def test_unknown_duration_stays_ask_and_chart_blocks_unbounded_exports(monkeypatch):
    source = "Tab SyntheticUnknown 1-0-0"
    med = MedLine(drug="SyntheticUnknown", dose=Dose(morning=1), note=source)
    at = review(monkeypatch, med, source)
    assert not at.exception and not at.session_state["drafts"][0]["confirmed"]
    assert "duration_days" in at.session_state["drafts"][0]["gold"]["needs_check"]
    assert next(b for b in at.button if b.label == "Confirm this line").disabled
    direct = {"line": source, "gold": med.model_dump(), "confirmed": True}
    assert any("end date" in b for b in export_blockers([direct]))
    chart = AppTest.from_file(str(ROOT / "app/pages/3_Chart.py"), default_timeout=10)
    chart.session_state["drafts"] = [direct]
    chart.run()
    assert not chart.get("download_button")


def test_written_continuation_requires_explicit_attestation_and_unchecking_revokes(monkeypatch):
    source = "Tab SyntheticOngoing 1-0-0 continue"
    med = MedLine(drug="SyntheticOngoing", dose=Dose(morning=1), note=source)
    at = review(monkeypatch, med, source)
    at.checkbox(key="pc_r_0_ongoing").check().run()
    draft = at.session_state["drafts"][0]
    assert not draft["gold"]["needs_check"] and draft["ongoing_confirmed"]
    assert not export_blockers([{**draft, "confirmed": True}])
    at.session_state["drafts"] = [{**draft, "confirmed": True}]
    at.checkbox(key="pc_r_0_ongoing").uncheck().run()
    assert not at.session_state["drafts"][0]["confirmed"]


@pytest.mark.parametrize("lang", ["en", "mr", "hi"])
def test_copied_instructions_survive_review_chart_ics_and_google_payload(monkeypatch, lang):
    source = "Drops SyntheticEye 1-0-0 left eye x3 days"
    med = MedLine(drug="SyntheticEye", form="drops", dose=Dose(morning=1, unit="drop"), duration_days=3, note="left eye <literal>")
    at = review(monkeypatch, med, source)
    assert at.text_area(key="pc_r_0_note").value == med.note
    copied = MedLine.model_validate(at.session_state["drafts"][0]["gold"])
    assert copied.note == med.note
    plan = expand([copied], date(2026, 10, 4))
    output = chart_html(plan, lang=lang)
    assert "left eye &lt;literal&gt;" in output
    raw = to_ics(plan)
    event = Calendar.from_ical(raw).walk("VEVENT")[0]
    assert str(event["DESCRIPTION"]) == med.note
    assert google_events(raw, "Asia/Kolkata")[0]["payload"]["description"] == med.note


def test_conflicting_drug_names_display_literal_markup(monkeypatch):
    source = "Tab <b>Synthetic</b> 1-0-0 x7 days"
    med = MedLine(drug="<b>Synthetic</b>", dose=Dose(morning=1), duration_days=7, note=source)
    at = review(monkeypatch, med, source)
    at.session_state["drafts"] = [at.session_state["drafts"][0],
        {"line": source, "gold": med.model_copy(update={"dose": Dose(night=1)}).model_dump(), "confirmed": False}]
    at.run()
    banner = next(m.value for m in at.markdown if "Same drug, different copy" in m.value)
    assert "&lt;b&gt;synthetic&lt;/b&gt;" in banner
    assert "<b>synthetic</b>" not in banner
