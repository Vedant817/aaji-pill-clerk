"""Source/check record is explicit, private and retained in actual exports."""
from datetime import date, time
import sqlite3
from pathlib import Path

import pytest
from icalendar import Calendar
from streamlit.testing.v1 import AppTest

from pillclerk import store
from pillclerk.chart import chart_html
from pillclerk.ics import to_ics
from pillclerk.provenance import CopyContext
from pillclerk.review import clear_review_keys
from pillclerk.schedule import expand
from pillclerk.schema import Dose, MedLine


def context():
    return CopyContext(source_reference="Synthetic source <literal>", prescription_date=None,
                       checker="agent-test", checked_on=date(2026, 10, 4), start_date=date(2026, 10, 5),
                       slot_times={"morning": time(9, 15), "afternoon": time(14), "night": time(22)},
                       ongoing_confirmed=[False]).model_dump(mode="json")


def test_context_survives_html_ics_and_sqlite_revision(tmp_path):
    med = MedLine(drug="SyntheticA", dose=Dose(morning=1), duration_days=7, note="left site")
    record = context()
    plan = expand([med], date(2026, 10, 5))
    html = chart_html(plan, lang="en", context=record)
    assert "Synthetic source &lt;literal&gt;" in html and "agent-test" in html
    assert "prescription date: not recorded" in html and "morning 09:15" in html
    event = Calendar.from_ical(to_ics(plan, context=record)).walk("VEVENT")[0]
    assert "left site" in str(event["DESCRIPTION"]) and "Checked by: agent-test" in str(event["DESCRIPTION"])
    assert event.decoded("DTSTART").time() == time(9, 15)
    assert "09:15" in html
    path = tmp_path / "history.db"
    store.save_meds([med], path=path, context=record)
    assert store.load_history(path)[0]["context"] == record


def test_legacy_database_migrates_without_inventing_source_or_changing_records(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE meds (id INTEGER PRIMARY KEY, saved_at TEXT, payload TEXT)")
        connection.execute("CREATE TABLE history (id INTEGER PRIMARY KEY, saved_at TEXT, note TEXT, payload TEXT)")
        connection.execute("INSERT INTO history VALUES (1, 'old timestamp', 'old note', '[]')")
    assert store.load_history(path) == [{"id": 1, "saved_at": "old timestamp", "note": "old note", "meds": [], "context": {}}]


def test_missing_source_and_checker_disable_download_and_save(monkeypatch, tmp_path):
    import streamlit as st
    monkeypatch.setattr(st, "page_link", lambda *args, **kwargs: None)
    save = store.save_meds
    path = tmp_path / "copy.db"
    monkeypatch.setattr(store, "save_meds", lambda meds, note="", context=None: save(meds, note, path, context=context))
    source = "Tab SyntheticA 1-0-0 x7 days"
    med = MedLine(drug="SyntheticA", dose=Dose(morning=1), duration_days=7, note=source)
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app/pages/3_Chart.py"), default_timeout=10)
    at.session_state["drafts"] = [{"line": source, "gold": med.model_dump(), "confirmed": True}]
    at.run()
    assert not at.exception
    assert all(w.proto.disabled for w in at.get("download_button"))
    assert next(b for b in at.button if b.label == "Save to local history").disabled
    assert at.date_input(key="pc_chart_source_date").value is None
    at.text_input(key="pc_chart_source").set_value("synthetic-role-case")
    at.text_input(key="pc_chart_checker").set_value("agent-test").run()
    assert not at.exception and all(not w.proto.disabled for w in at.get("download_button"))
    next(b for b in at.button if b.label == "Save to local history").click().run()
    record = store.load_history(path)[0]["context"]
    assert record["source_reference"] == "synthetic-role-case" and record["checker"] == "agent-test"
    assert record["prescription_date"] is None and record["start_date"] == at.date_input[0].value.isoformat()


def test_new_source_resets_old_chart_signoff_and_context_validation():
    state = {"pc_chart_source": "old-source", "pc_chart_checker": "old-checker", "drafts": []}
    clear_review_keys(state)
    assert "pc_chart_source" not in state and "pc_chart_checker" not in state
    values = context()
    values["checker"] = " "
    with pytest.raises(ValueError):
        CopyContext.model_validate(values)


def test_conflicting_export_times_cannot_misstate_saved_check_context():
    record = context()
    med = MedLine(drug="SyntheticA", dose=Dose(morning=1), duration_days=7)
    plan = expand([med], date(2026, 10, 5))
    wrong = {"morning": time(8), "afternoon": time(14), "night": time(22)}
    with pytest.raises(ValueError, match="times differ"):
        to_ics(plan, slot_times=wrong, context=record)
    with pytest.raises(ValueError, match="times differ"):
        chart_html(plan, slot_times=wrong, context=record)
