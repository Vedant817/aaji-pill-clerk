import pytest

from eval.compare_candidate import metrics, page_delta_ci
from pillclerk.schema import Dose, MedLine


def test_joint_and_field_ask_metrics_catch_partial_abstention():
    label = MedLine(drug="TestOnly", dose=Dose(morning=1), needs_check=["food", "duration_days"])
    pred = label.model_copy(update={"needs_check": ["food"]})
    gold = [{"line": "test", "gold": label.model_dump(), "image": "page.jpg"}]
    summary, scores = metrics(gold, [{"line": "test", "pred": pred.model_dump()}])
    assert summary["exact"] == 1 and summary["exact_and_ask"] == 0
    assert summary["ASK_field_recall"] == 0.5 and summary["ASK_field_precision"] == 1
    assert summary["selective_coverage"] == 0
    assert scores[0]["image"] == "page.jpg"
    with pytest.raises(ValueError, match="cohorts"):
        metrics(gold, [{"line": "other", "pred": pred.model_dump()}])


def test_page_bootstrap_pairs_all_lines_from_a_page():
    before = [{"image": "A", "exact": 0}, {"image": "A", "exact": 0}, {"image": "B", "exact": 1}]
    after = [{**s, "exact": 1} for s in before]
    assert page_delta_ci(before, after) == [0, 1]


def test_unflagged_food_form_and_prn_errors_are_reported_separately():
    med = MedLine(drug="TestOnly", form="cap", kind="prn", food="after", prn_max_per_day=2)
    pred = med.model_copy(update={"form": "tab", "food": "any", "prn_max_per_day": 3})
    gold = [{"line": "test", "gold": med.model_dump()}]
    summary, _ = metrics(gold, [{"line": "test", "pred": pred.model_dump()}])
    assert summary["unflagged_field_errors"] == {"form": 1, "food": 1, "prn_max_per_day": 1}
