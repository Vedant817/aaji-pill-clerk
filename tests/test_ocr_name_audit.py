import pytest

from eval.ocr_name_audit import audit, contains_name


def reference(drug, image="a.jpg"):
    return {"image": image, "gold": {"drug": drug}, "label_origin": "ai_single_agent", "human_verified": False}


def test_page_names_use_token_boundaries_and_never_match_blank():
    assert contains_name(["T. TEST-MED 5mg"], "test med")
    assert not contains_name(["Testmedication"], "Testmed")
    assert not contains_name(["Test", "Med"], "Test Med")
    assert not contains_name(["anything"], "[?]")


def test_unknown_and_duplicate_names_do_not_inflate_denominator():
    result = audit([{"image": "a.jpg", "lines": ["Testmed"], "error": None}],
                   [reference("Testmed"), reference("TESTMED"), reference(None), reference("Missing")])
    assert result["distinct_known_name_presence"] == {"found": 1, "total": 2}
    assert result["unknown_drug_reference_lines"] == 1
    assert result["cer"] is None and not result["human_verified"]


def test_incomplete_or_duplicate_page_evidence_is_rejected():
    with pytest.raises(ValueError, match="each reference page"):
        audit([], [reference("Testmed")])
    row = {"image": "a.jpg", "lines": [], "error": None}
    with pytest.raises(ValueError, match="each reference page"):
        audit([row, row], [reference("Testmed")])


def test_origin_and_failure_consistency_are_required():
    ref = reference("Testmed")
    ref["human_verified"] = True
    with pytest.raises(ValueError, match="unverified AI"):
        audit([], [ref])
    with pytest.raises(ValueError, match="actual lines"):
        audit([{"image": "a.jpg", "lines": ["Testmed"], "error": "RuntimeError"}], [reference("Testmed")])
