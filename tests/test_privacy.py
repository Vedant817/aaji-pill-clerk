from pathlib import Path

import pytest

from pillclerk.privacy import (
    PrivacyError,
    assert_gemini_eval_set,
    is_real_path,
    strip_pii,
)


def test_strip_pii_redacts_phone_age_doctor() -> None:
    text = "Dr. Sharma, patient: Aaji, age 74, phone 9876543210, a@b.com. Tab Glycomet 500 1-0-1"
    clean, tags = strip_pii(text)
    assert "9876543210" not in clean
    assert "a@b.com" not in clean
    assert "phone" in tags and "doctor" in tags and "age" in tags
    assert "Glycomet" in clean


def test_gemini_allowlist_blocks_real_paths() -> None:
    with pytest.raises(PrivacyError):
        assert_gemini_eval_set(Path("data/real/gt.jsonl"))
    with pytest.raises(PrivacyError):
        assert_gemini_eval_set(Path("data/synth/train.jsonl"))
    allowed = assert_gemini_eval_set(Path("data/synth/synth_test.jsonl"))
    assert allowed.name == "synth_test.jsonl"
    assert_gemini_eval_set(Path("data/heldout/handwritten_realistic.jsonl"))


def test_real_path_detects_raw_and_gt() -> None:
    assert is_real_path(Path("data/real/raw/rx01.jpg"))
    assert is_real_path(Path("data/real/gt.jsonl"))
    assert not is_real_path(Path("data/heldout/handwritten_realistic.jsonl"))
