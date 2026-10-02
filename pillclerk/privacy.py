"""What may leave the laptop.

Prescription photos (family or public HMR/BD images) never go to Gemini or
any other remote teacher. Gemma 4 31B (AI Studio) may only see de-identified
*text* from allowlisted jsonl sets. Every remote teacher payload is logged
to eval/out/sent_payload_log.jsonl.
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
    (ROOT / "data" / "public_labels" / "hmr100_gold.jsonl").resolve(),
    (ROOT / "data" / "public_labels" / "bd200_gold.jsonl").resolve(),
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


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def is_photo_path(path: Path) -> bool:
    """Image files and gitignored photo folders never leave the laptop."""
    rel = path.resolve()
    if _under(rel, ROOT / "data" / "real"):
        return True
    if _under(rel, ROOT / "data" / "public"):
        return True
    suffix = rel.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff", ".bmp"}:
        return _under(rel, ROOT / "data")
    return False


def is_real_path(path: Path) -> bool:
    rel = path.resolve()
    if is_photo_path(rel):
        return True
    if _under(rel, ROOT / "data" / "real"):
        return True
    name = path.name.lower()
    return name in {"gt.jsonl", "real_test.jsonl"} or "photographed" in name


def assert_gemini_eval_set(path: Path) -> Path:
    resolved = path.resolve()
    if is_photo_path(resolved):
        raise PrivacyError(
            "Prescription images never leave the laptop. Gemini 31B is text-only "
            "on synth_test, handwritten_realistic, and de-identified public gold jsonl."
        )
    if _under(resolved, ROOT / "data" / "real"):
        raise PrivacyError(
            "data/real/* never leaves the laptop. Gemini 31B is text-only on "
            "allowlisted jsonl (synth, handwritten realistic, public gold text)."
        )
    if resolved not in ALLOWED_GEMINI_SETS:
        raise PrivacyError(
            "Gemini 31B may only score synth_test, handwritten_realistic, or "
            f"de-identified public gold jsonl, got {path}"
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
