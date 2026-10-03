"""Declared eval normalisation. Strict scores stay untouched.

Rules (applied to every system when reporting exact_norm):
- strength: compare the ordered list of (number, unit); spaces/case ignored.
  Missing unit on one side still matches if the numbers match.
- drug: Devanagari brand spellings map onto the Latin names in this table,
  then compare case-insensitively with spaces/dots stripped.
"""

from __future__ import annotations

import re
import json
from pathlib import Path
import unicodedata

# Declared transliteration reference data; never supplies a dose or patient record.
BRAND_ALIASES: dict[str, str] = json.loads(
    (Path(__file__).parent / "resources" / "brand_aliases.json").read_text(encoding="utf-8")
)

_STRENGTH = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mcg|mg|iu|ml|g|k|μg|ug)?",
    re.I,
)
_UNIT_MAP = {"μg": "mcg", "ug": "mcg", "mcg": "mcg", "mg": "mg", "g": "g", "iu": "iu", "ml": "ml", "k": "k"}


def _fold(text: str | None) -> str:
    if not text:
        return ""
    out = unicodedata.normalize("NFKC", text).strip().lower()
    return out.replace(".", " ").replace("  ", " ").strip()


def alias_drug(name: str | None) -> str:
    folded = _fold(name)
    if not folded:
        return ""
    mapped = BRAND_ALIASES.get(folded, folded)
    return re.sub(r"[\s.]+", "", mapped)


def drug_eq(a: str | None, b: str | None) -> bool:
    return alias_drug(a) == alias_drug(b)


def strength_parts(text: str | None) -> tuple[tuple[float, str], ...]:
    if not text:
        return ()
    parts: list[tuple[float, str]] = []
    for num, unit in _STRENGTH.findall(text.replace(",", "")):
        u = _UNIT_MAP.get((unit or "").lower(), (unit or "").lower())
        parts.append((float(num), u))
    return tuple(parts)


def strength_eq(a: str | None, b: str | None) -> bool:
    pa, pb = strength_parts(a), strength_parts(b)
    if not pa and not pb:
        return (a or None) == (b or None) or (not (a or "").strip() and not (b or "").strip())
    if len(pa) != len(pb):
        return False
    for (na, ua), (nb, ub) in zip(pa, pb, strict=True):
        if na != nb:
            return False
        if ua and ub and ua != ub:
            return False
    return True
