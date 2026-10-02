from eval.ocr_cer import cer, e4b_available, levenshtein


def test_levenshtein_and_cer() -> None:
    assert levenshtein("", "") == 0
    assert levenshtein("abc", "abc") == 0
    assert levenshtein("kitten", "sitting") == 3
    assert cer("abc", "abc") == 0.0
    assert cer("abc", "ab") == 1 / 3
    assert cer("", "x") == 1.0
    assert cer("", "") == 0.0


def test_e4b_not_claimed_when_missing() -> None:
    # This laptop has no ollama/gemma4:e4b; local OCR is not a Gemma claim.
    assert e4b_available() is False
