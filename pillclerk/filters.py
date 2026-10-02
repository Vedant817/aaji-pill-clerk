"""Rule filter for synthetic pairs (IDEA.md §7).

Keep a pair only if the messy text still carries the gold facts we can check
without an LLM: drug name (fuzzy), strength digits, duration digits.
Parse-back agreement is a separate, paid teacher call in render.py.
"""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from pillclerk.schema import MedLine

_DIGITS = re.compile(r"\d+")


def normalised_text(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip().lower().replace(".", "")


def drug_present(line: str, drug: str | None, *, min_ratio: int = 70) -> bool:
    if not drug:
        return "[?]" in line
    return fuzz.partial_ratio(drug.lower(), line.lower()) >= min_ratio


def _strength_digits_present(line: str, strength: str) -> bool:
    blob = strength.upper().replace("60K", "60")
    digits = _DIGITS.findall(blob)
    if not digits:
        return True
    line_u = line.upper().replace("60K", "60")
    return digits[0] in line_u


def _duration_present(line: str, days: int) -> bool:
    if str(days) in line:
        return True
    compact = line.replace(" ", "")
    if days == 30 and "1/12" in compact:
        return True
    return False


def rule_ok(line: str, gold: MedLine) -> bool:
    if not line or len(line) < 3 or len(line) > 240:
        return False
    if gold.drug:
        if not drug_present(line, gold.drug):
            return False
    elif "[?]" not in line:
        return False
    if gold.strength and any(ch.isdigit() for ch in gold.strength):
        if not _strength_digits_present(line, gold.strength):
            return False
    if gold.kind == "taper" and gold.taper:
        if not all(str(step.days) in line for step in gold.taper):
            return False
    elif gold.duration_days is not None and "duration_days" not in gold.needs_check:
        if not _duration_present(line, gold.duration_days):
            return False
    return True
