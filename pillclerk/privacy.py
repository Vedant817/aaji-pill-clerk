"""What may leave the laptop.

Real prescription photos and photographed lines never go to Gemini or any
other remote teacher. Gemma 4 31B (AI Studio) may only see de-identified
synthetic and hand-written realistic *text*. Every remote teacher payload
is logged to eval/out/sent_payload_log.jsonl.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from pillclerk.config import ROOT

LOG = ROOT / "eval" / "out" / "sent_payload_log.jsonl"
_LOG_LOCK = threading.Lock()

ALLOWED_GEMINI_SETS = {
    (ROOT / "data" / "synth" / "synth_test.jsonl").resolve(),
    (ROOT / "data" / "heldout" / "handwritten_realistic.jsonl").resolve(),
}

PHONE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
AGE = re.compile(r"\b(?:aged?|age)\s*[:\-]?\s*\d{1,3}\b|\b\d{1,3}\s*(?:y/o|yrs?|years?\s*old)\b", re.I)
DOCTOR = re.compile(
    r"\b(?:Dr\.?|Doctor|डॉ\.?)\s+[A-Za-z\u0900-\u097F.]+(?:\s+[A-Za-z\u0900-\u097F.]{2,})?",
    re.I,
)
PATIENT = re.compile(
    r"\b(?:patient|pt\.?|name)\s*[:\-]\s*[A-Za-z\u0900-\u097F ]{2,40}",
    re.I,
)


class PrivacyError(RuntimeError):
    pass


def is_real_path(path: Path) -> bool:
    rel = path.resolve()
    real_root = (ROOT / "data" / "real").resolve()
    try:
        rel.relative_to(real_root)
        return True
    except ValueError:
        pass
    name = path.name.lower()
    return name in {"gt.jsonl", "real_test.jsonl"} or "photographed" in name


def assert_gemini_eval_set(path: Path) -> Path:
    resolved = path.resolve()
    if is_real_path(resolved):
        raise PrivacyError(
            "Photographed prescriptions and data/real/* never leave the laptop. "
            "Gemini 31B is text-only on synth_test and handwritten_realistic."
        )
    if resolved not in ALLOWED_GEMINI_SETS:
        raise PrivacyError(
            f"Gemini 31B may only score synth_test or handwritten_realistic, got {path}"
        )
    return resolved


def strip_pii(text: str) -> tuple[str, list[str]]:
    """Replace names, ages, phones, doctor names. Returns (clean, tags_removed)."""
    removed: list[str] = []
    out = text
    for tag, pat in (
        ("phone", PHONE),
        ("email", EMAIL),
        ("age", AGE),
        ("doctor", DOCTOR),
        ("name", PATIENT),
    ):
        if pat.search(out):
            removed.append(tag)
            out = pat.sub(f"[{tag.upper()}]", out)
    return out, removed


def log_sent_payload(
    *,
    system: str,
    set_path: str,
    model: str,
    line: str,
    stripped: list[str],
    messages: list[dict[str, str]],
) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "system": system,
        "set": set_path,
        "model": model,
        "stripped": stripped,
        "n_chars": sum(len(m.get("content") or "") for m in messages),
        "payload": messages,
    }
    with _LOG_LOCK:
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
