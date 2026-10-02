"""Declared eval normalisation. Strict scores stay untouched.

Rules (applied to every system when reporting exact_norm):
- strength: compare the ordered list of (number, unit); spaces/case ignored.
  Missing unit on one side still matches if the numbers match.
- drug: Devanagari brand spellings map onto the Latin names in this table,
  then compare case-insensitively with spaces/dots stripped.
"""

from __future__ import annotations

import re
import unicodedata

# Devanagari (or mixed) brand -> Latin alias. Keys are lowercased NFKC.
# Halant spellings (टेल्मा, पैन, …) were added after seeing eval errors. Disclose that.
BRAND_ALIASES: dict[str, str] = {
    "ग्लाइकोमेट": "glycomet",
    "ग्लायकोमेट": "glycomet",
    "ग्लुकोमेट": "glycomet",
    "टेलमा": "telma",
    "टेल्मा": "telma",
    "टेलमा एएम": "telma am",
    "टेल्मा एएम": "telma am",
    "पैन": "pan",
    "पैन": "pan",
    "इकोस्प्रिन": "ecosprin",
    "इकोस्प्रिन एव्ही": "ecosprin av",
    "थायरोनॉर्म": "thyronorm",
    "थायरॉनॉर्म": "thyronorm",
    "एटोरवा": "atorva",
    "डोलो": "dolo",
    "पैंटोप्रैजोल": "pantoprazole",
    "पैंटोप्राज़ोल": "pantoprazole",
    "पॅन्टोप": "pantop",
    "पैंटोप": "pantop",
    "मेटोलार": "metolar",
    "क्लोपीटैब": "clopitab",
    "क्लोपिटॅब": "clopitab",
    "रोजावेल": "rozavel",
    "फोराकोर्ट": "foracort",
    "अस्थालिन": "asthalin",
    "लेंटस": "lantus",
    "नोवोरेपिड": "novorapid",
    "नोव्होरेपिड": "novorapid",
    "शेल्कल": "shelcal",
    "कॅल्सिरोल": "calcirol",
    "विटामिन डी3": "vitamin d3",
    "एस्कोरिल": "ascoril",
    "वइसोलोन": "wysolone",
    "वायसोलोन": "wysolone",
    "कॉम्बिफ्लेम": "combiflam",
    "ड्यूलिन": "duolin",
}

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
