import json
from pathlib import Path

import pytest

from pillclerk.annotation_form import manual_gold
from pillclerk.feedback import Observation, save_observation, shareable_summary


def fields(**updates):
    return dict(drug="", strength="", form="other", kind="daily", food="any",
                duration=None, interval=1, dose=None, taper=[], prn_limit=None,
                checks=[], **updates)


def test_unreadable_fields_abstain_without_prescription_defaults():
    row = manual_gold(**fields())
    assert row["drug"] is None and row["dose"] is None and row["duration_days"] is None
    assert set(row["needs_check"]) == {"drug", "dose", "duration_days"}


def test_manual_selection_and_all_dose_slots_are_required():
    values = fields()
    values["form"] = None
    with pytest.raises(ValueError, match="Choose"):
        manual_gold(**values)
    values["form"] = "tab"
    values["dose"] = {"morning": 1, "afternoon": None, "night": 0, "unit": "tab"}
    with pytest.raises(ValueError, match="every dose"):
        manual_gold(**values)


def observation(**updates):
    data = dict(observer_id="test-only", source="agent_test", context="synthetic_input",
                actual_observation_attested=True, sharing_allowed=False, workflow="pass",
                ask_understood="not_checked", source_compared="not_checked", ics_import="not_checked",
                recurrence="not_checked", notification="not_checked", sound="not_checked")
    data.update(updates)
    return Observation(**data)


def test_attestation_and_phone_context_are_required():
    with pytest.raises(ValueError, match="actual observation"):
        observation(actual_observation_attested=False)
    with pytest.raises(ValueError, match="Phone observations"):
        observation(notification="pass")


def test_private_feedback_never_enters_shared_summary_and_agents_stay_separate(tmp_path):
    path = tmp_path / "feedback.jsonl"
    save_observation(observation(feedback="Private test-only words", observer_id="secret-test-id"), path)
    assert shareable_summary(path)["consented_observations"] == 0
    save_observation(observation(sharing_allowed=True), path)
    save_observation(observation(source="human_self_report", sharing_allowed=True, workflow="fail"), path)
    result = shareable_summary(path)
    assert result["agent_tests"] == 1 and result["human_observations"] == 1
    assert result["checks"]["human_self_report"]["workflow"]["fail"] == 1
    assert "secret-test-id" not in json.dumps(result) and "Private test-only words" not in json.dumps(result)


def test_feedback_page_starts_unanswered_and_cannot_save_simulated_success(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import pillclerk.feedback as feedback
    path = tmp_path / "observations.jsonl"
    save = feedback.save_observation
    monkeypatch.setattr(feedback, "DEFAULT_PATH", path)
    monkeypatch.setattr(feedback, "save_observation", lambda record: save(record, path))
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app/pages/7_Acceptance_Feedback.py"), default_timeout=10).run()
    assert not at.exception
    assert all(w.value == "not_checked" for w in at.selectbox if w.key and w.key.startswith("feedback_"))
    at.button[0].click().run()
    assert at.error and not path.exists()

    at.text_input[0].set_value("test-only-observer")
    next(w for w in at.selectbox if w.label == "Who observed it?").set_value("agent_test")
    next(w for w in at.selectbox if w.label == "Input used").set_value("synthetic_input")
    next(w for w in at.selectbox if w.label == "Permission to share aggregate results").set_value("Keep private")
    at.selectbox(key="feedback_workflow").set_value("fail")
    at.checkbox[0].check()
    at.button[0].click().run()
    assert not at.exception and not at.error
    row = json.loads(path.read_text())
    assert row["source"] == "agent_test" and row["sharing_allowed"] is False
    assert row["workflow"] == "fail"
    assert all(row[name] == "not_checked" for name in ("ics_import", "notification"))


def test_empty_unchecked_observation_cannot_inflate_acceptance_counts():
    with pytest.raises(ValueError, match="at least one actual"):
        observation(workflow="not_checked", feedback=" ")
