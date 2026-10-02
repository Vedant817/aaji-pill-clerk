"""Copy form/food/duration tokens that are literally on the line. Never guess a dose."""

from __future__ import annotations

import re

from pillclerk.schema import Form, MedLine

_FORM_CUES: list[tuple[re.Pattern[str], Form, str]] = [
    (re.compile(r"\b(capsules?|cap\.?)\b", re.I), "cap", "cap"),
    (re.compile(r"\b(tablets?|tab\.?)\b", re.I), "tab", "tab"),
    (re.compile(r"\b(syrup|syr\.?)\b", re.I), "syrup", "ml"),
    (re.compile(r"\b(drops?)\b", re.I), "drops", "drop"),
    (re.compile(r"\b(inhaler|inh\.?|puff)\b", re.I), "inhaler", "puff"),
    (re.compile(r"\b(injection|inj\.?|insulin)\b", re.I), "injection", "unit"),
    (re.compile(r"\b(cream|ointment)\b", re.I), "cream", "apply"),
    (re.compile(r"\b(sachet)\b", re.I), "sachet", "sachet"),
]

_FOOD_CUES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"before food|\bac\b|खाने से पहले|जेवणाआधी|khane se pehle", re.I), "before"),
    (re.compile(r"after food|\bpc\b|खाने के बाद|जेवणानंतर|khane ke baad", re.I), "after"),
    (re.compile(r"with food|\bwf\b|खाने के साथ|जेवणासोबत|khane ke saath", re.I), "with"),
    (
        re.compile(r"empty stomach|\bes\b|खाली पेट|उपाशीपोटी|khali pet", re.I),
        "empty_stomach",
    ),
]

_MONTH = re.compile(r"\b1/12\b")
_PRN = re.compile(r"\b(sos|prn|zarurat|जरूरत|गरजेनुसार)\b", re.I)
_MAX_N = re.compile(r"\bmax\s*(\d+)\b", re.I)
_DUR_X = re.compile(r"\bx\s*(\d+)\s*d(?:ays?)?\b", re.I)
_DUR_DIN = re.compile(r"\b(\d+)\s*(?:din|दिन|दिवस)\b", re.I)
_CONTINUE = re.compile(r"\b(?:continue|cont)\b", re.I)


def line_has_food_word(line: str) -> bool:
    return any(pat.search(line) for pat, _ in _FOOD_CUES)


def duration_from_line(line: str) -> int | None | str:
    """Return written duration, None if continue/absent, or 'ambiguous'."""
    if _MONTH.search(line):
        return 30
    found = [int(m.group(1)) for m in _DUR_X.finditer(line)]
    found += [int(m.group(1)) for m in _DUR_DIN.finditer(line)]
    if len(set(found)) == 1:
        return found[0]
    if len(set(found)) > 1:
        return "ambiguous"
    if _CONTINUE.search(line):
        return None
    return None


def prn_max_from_line(line: str) -> int | None:
    m = _MAX_N.search(line)
    return int(m.group(1)) if m else None


def align_gold(med: MedLine, line: str) -> MedLine:
    """Make gold match tokens that are actually written on the line.

    - food is any when the line has no food word
    - duration_days matches x Nd / N din / 1/12; None if none is written
      (taper lines keep the sum of steps)
    - prn_max_per_day only when "max N" is written
    """
    updates: dict = {}
    if not line_has_food_word(line):
        updates["food"] = "any"
    if med.kind != "taper":
        written = duration_from_line(line)
        if written != "ambiguous":
            updates["duration_days"] = written
    updates["prn_max_per_day"] = prn_max_from_line(line)
    if not updates:
        return med
    return med.model_copy(update=updates)


def copy_explicit(med: MedLine, line: str) -> MedLine:
    updates: dict = {}
    forms = [(form, unit) for pat, form, unit in _FORM_CUES if pat.search(line)]
    unique_forms = {f for f, _ in forms}
    if len(unique_forms) == 1:
        form, unit = forms[0]
        updates["form"] = form
        if med.dose is not None and med.dose.unit != unit:
            updates["dose"] = med.dose.model_copy(update={"unit": unit})
        if med.kind == "taper" and med.taper:
            updates["taper"] = [
                step.model_copy(update={"dose": step.dose.model_copy(update={"unit": unit})})
                for step in med.taper
            ]

    foods = [food for pat, food in _FOOD_CUES if pat.search(line)]
    unique_foods = set(foods)
    if len(unique_foods) == 1:
        updates["food"] = foods[0]
    elif not unique_foods:
        updates["food"] = "any"

    if _MONTH.search(line) and med.duration_days in (None, 1, 12):
        updates["duration_days"] = 30

    if not updates:
        return med
    return med.model_copy(update=updates)
