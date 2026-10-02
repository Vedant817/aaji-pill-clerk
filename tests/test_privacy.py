from pathlib import Path

import pytest

from pillclerk.privacy import (
    PrivacyError,
    assert_gemini_eval_set,
    is_real_path,
    redact_secret,
    strip_pii,
    write_payload_summary,
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
    assert_gemini_eval_set(Path("data/public_labels/hmr100_gold.jsonl"))
    with pytest.raises(PrivacyError):
        assert_gemini_eval_set(Path("data/public/hmr100/hmr_000.jpg"))


def test_gemini_key_not_in_url_and_exceptions() -> None:
    src = Path("pillclerk/render.py").read_text(encoding="utf-8")
    assert "x-goog-api-key" in src
    assert 'params={"key"' not in src
    assert "params={'key'" not in src
    assert "params={\"key\": self.api_key}" not in src
    secret = "super-secret-gemini-key"
    leaked = redact_secret(
        RuntimeError(f"GET https://generativelanguage.googleapis.com/v1/models/x:generateContent?key={secret} 403"),
        secret,
    )
    assert secret not in leaked
    assert "key=[REDACTED]" in leaked or "[REDACTED]" in leaked


def test_payload_summary_has_count_sets_model_sha(tmp_path: Path) -> None:
    log = tmp_path / "sent.jsonl"
    log.write_text(
        '{"system":"render","set":"synthetic_render","model":"gemma-4-31b-it","payload":[{"role":"user","content":"hi"}]}\n',
        encoding="utf-8",
    )
    dest = tmp_path / "summary.json"
    out = write_payload_summary(log, dest)
    assert out["count"] == 1
    assert out["sets"]["synthetic_render"] == 1
    assert out["models"]["gemma-4-31b-it"] == 1
    assert len(out["sha256"]) == 64


def test_real_path_detects_raw_and_gt() -> None:
    assert is_real_path(Path("data/real/raw/rx01.jpg"))
    assert is_real_path(Path("data/real/gt.jsonl"))
    assert not is_real_path(Path("data/heldout/handwritten_realistic.jsonl"))
    assert not is_real_path(Path("data/public_labels/hmr100_gold.jsonl"))
