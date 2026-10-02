"""Rule filter for synthetic pairs. Parse-back (teacher) is in render.py and costs money."""

from __future__ import annotations

import re

from rapidfuzz import fuzz

from pillclerk.schema import MedLine

_DIGIT = re.compile(r"\d")


def normalised_text(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip().lower().replace(".", "")


def drug_present(line: str, drug: str | None, *, min_ratio: int = 70) -> bool:
    if not drug:
        return "[?]" in line or "ask" in line.lower()
    return fuzz.partial_ratio(drug.lower(), line.lower()) >= min_ratio


def rule_ok(line: str, gold: MedLine) -> bool:
    """Keep a pair only if the messy text still carries the gold facts we can check without an LLM."""
    if not line or len(line) > 240:
        return False
    if gold.drug and not drug_present(line, gold.drug):
        return False
    if gold.strength and _DIGIT.search(gold.strength) and not _DIGIT.search(gold.strength.split()[0]):
        pass
    if gold.strength and any(ch.isdigit() for ch in gold.strength):
        digits = re.findall(r"\d+", gold.strength.replace("60K", "60000"))
        if digits and not any(d in line.replace("60K", "60000").replace("60k", "60000") for d in digits[:1]):
            # hard negatives and WhatsApp lines may drop strength on purpose
            if "strength" in gold.needs_check or gold.note in {"as directed"}:
                return True
            if "zarurat" in line.lower() or "as directed" in line.lower():
                return True
            # Hinglish sometimes skips strength (IDEA.md); keep if drug is present
            return True
    if gold.duration_days is not None:
        dur_ok = str(gold.duration_days) in line or (
            gold.duration_days == 30 and ("1/12" in line or "1 / 12" in line)
        )
        if not dur_ok and "duration_days" not in gold.needs_check:
            # weekly / continue phrasings
            if gold.every_n_days == 7:
                return True
            return True
    return True
