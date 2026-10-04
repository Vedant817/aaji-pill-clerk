from eval.ocr_probe import summarize


def test_blank_labels_never_count_as_recognized():
    result = summarize([{"image": "test.jpg", "lines": [], "error": None}],
                       {"test.jpg": ["", " ", "???", "Test Medicine"]}, backend="windows", model=None)
    assert result["published_label_exact_presence"] == {"found": 0, "total": 1}
    assert result["pages_without_text"] == 1
    assert result["cer"] is None
    assert not result["human_verified"]


def test_probe_distinguishes_some_text_from_full_name_recovery():
    result = summarize([{"image": "a.jpg", "lines": ["TEST-MED 5mg"], "error": None},
                        {"image": "b.jpg", "lines": [], "error": "RuntimeError"}],
                       {"a.jpg": ["Test Med 5 MG", "Missing"], "b.jpg": ["Unreadable"]},
                       backend="ollama", model="test-only")
    assert result["published_label_exact_presence"] == {"found": 1, "total": 3}
    assert result["pages_with_text"] == 1
    assert result["pages_failed"] == 1
