"""What may leave the laptop.

Prescription photos (family or public HMR/BD images) never go to Gemini or
any other remote teacher. Gemma 4 31B (AI Studio) may only see de-identified
*text* from allowlisted jsonl sets. Every remote teacher payload is logged
to eval/out/sent_payload_log.jsonl.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pillclerk.config import ROOT

LOG = ROOT / "eval" / "out" / "sent_payload_log.jsonl"
SUMMARY = ROOT / "eval" / "out" / "payload_summary.json"
_LOG_LOCK = threading.Lock()
_KEY_IN_URL = re.compile(r"([?&]key=)[^&\s\"']+", re.I)

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


def redact_secret(exc: object, secret: str | None) -> str:
    """Stringify an error without ever echoing an API key (URL, header, or body)."""
    text = "" if exc is None else f"{type(exc).__name__}: {exc}" if isinstance(exc, BaseException) else str(exc)
    text = _KEY_IN_URL.sub(r"\1[REDACTED]", text)
    if secret:
        text = text.replace(secret, "[REDACTED]")
    return text


def write_payload_summary(log_path: Path | None = None, dest: Path | None = None) -> dict:
    """Per-run summary: count, sets, model, sha256 of payloads. No secrets."""
    path = log_path or LOG
    dest = dest or SUMMARY
    rows: list[dict] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    hasher = hashlib.sha256()
    sets: Counter[str] = Counter()
    models: Counter[str] = Counter()
    systems: Counter[str] = Counter()
    for row in rows:
        payload = row.get("payload") or row.get("messages") or []
        hasher.update(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        set_name = Path(str(row.get("set") or "")).name or str(row.get("set") or "")
        sets[set_name] += 1
        models[str(row.get("model") or "")] += 1
        systems[str(row.get("system") or "")] += 1
    out = {
        "count": len(rows),
        "sets": dict(sets),
        "models": dict(models),
        "systems": dict(systems),
        "sha256": hasher.hexdigest() if rows else None,
        "log": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


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
