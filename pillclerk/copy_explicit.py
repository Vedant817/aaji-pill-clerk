"""Copy tokens that are literally on the line. Never guess a dose that is not written."""

from __future__ import annotations

import re

from pillclerk.normalize import drug_eq, strength_eq
from pillclerk.schema import Dose, Form, MedLine

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
_MAX_N = re.compile(r"\bmax\s*(\d+)\s*(?:/\s*d)?\b", re.I)
_MAX_DIN = re.compile(r"दिवसाला\s*(\d+)|din\s*mein\s*(\d+)", re.I)
_DUR_X = re.compile(r"\bx\s*(\d+)\s*d(?:ays?)?\b", re.I)
_DUR_DIN = re.compile(r"\b(\d+)\s*(?:din|दिन|दिवस)\b", re.I)
_CONTINUE = re.compile(r"\b(?:continue|cont)\b", re.I)
_COMBO = re.compile(r"\s+(AM|AV|LS|GP\d*|XR|SR|CR|PLUS)\b", re.I)
_DOSE_TRIPLE = re.compile(
    r"[0-9½¼¾]+(?:\.\d+)?\s*-\s*[0-9½¼¾]+(?:\.\d+)?\s*-\s*[0-9½¼¾]+(?:\.\d+)?"
)
_OD_BD = re.compile(r"\b(OD|BD|TDS|QID|HS)\b", re.I)
_MORNING = re.compile(r"subah|सुबह|सकाळी", re.I)
_NOON = re.compile(r"dopahar|दोपहर|दुपारी", re.I)
_NIGHT = re.compile(r"raat(?:\s*ko)?|रात(?:\s*को)?|रात्री", re.I)
_UNIT_AMT = re.compile(r"\b(\d+(?:\.\d+)?)\s*units?\b", re.I)
_WEEKLY = re.compile(r"hafte|weekly|आठवड", re.I)
_ML_AMT = re.compile(r"\b(\d+(?:\.\d+)?)\s*ml\b", re.I)
_UNIT = r"(?:mg|mcg|iu|ml|g|k|%)"
_STRENGTH_SPAN = re.compile(
    rf"\d+(?:\.\d+)?(?:\s*{_UNIT})?(?:\s*/\s*\d+(?:\.\d+)?(?:\s*{_UNIT})?)?",
    re.I,
)
_WORD = re.compile(r"[\u0900-\u097FA-Za-z][\u0900-\u097FA-Za-z]*")


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
    if m:
        return int(m.group(1))
    m = _MAX_DIN.search(line)
    if m:
        return int(m.group(1) or m.group(2))
    return None


def line_has_dose_cue(line: str) -> bool:
    return bool(
        _DOSE_TRIPLE.search(line)
        or _OD_BD.search(line)
        or _MORNING.search(line)
        or _NOON.search(line)
        or _NIGHT.search(line)
        or _UNIT_AMT.search(line)
        or _WEEKLY.search(line)
        or len(_ML_AMT.findall(line)) >= 2
    )


def _guessed_od(dose: Dose | None) -> bool:
    return bool(dose and dose.morning == 1 and dose.afternoon == 0 and dose.night == 0)


def _surface_drug(line: str, pred_drug: str) -> str | None:
    parts = pred_drug.split()
    first = parts[0]
    if len(parts) == 1:
        combo = re.search(rf"{re.escape(first)}{_COMBO.pattern}", line, re.I)
        if combo:
            return combo.group(0).strip()
    words = _WORD.findall(line)
    hits = [w for w in words if drug_eq(w, pred_drug)]
    if not hits:
        return None
    return max(hits, key=len)


def _surface_strength(line: str, pred_strength: str) -> str | None:
    hits = [m.group(0).strip() for m in _STRENGTH_SPAN.finditer(line) if strength_eq(m.group(0), pred_strength)]
    if not hits:
        return None
    best = max(hits, key=len)
    compact = lambda s: re.sub(r"\s+", "", s).lower()
    if compact(best) == compact(pred_strength):
        return best
    if not re.search(r"[A-Za-z\u0900-\u097F]", best) and len(best) < len(pred_strength):
        return best
    return None


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

    written_max = prn_max_from_line(line)
    if written_max is not None:
        updates["prn_max_per_day"] = written_max

    if med.drug:
        surface = _surface_drug(line, med.drug)
        if surface:
            updates["drug"] = surface

    if med.strength:
        surface_s = _surface_strength(line, med.strength)
        if surface_s:
            updates["strength"] = surface_s

    unit_amt = _UNIT_AMT.search(line)
    if unit_amt and not re.search(r"IU\s*/\s*ml", line, re.I):
        amt = float(unit_amt.group(1))
        morning = amt if _MORNING.search(line) else 0.0
        afternoon = amt if _NOON.search(line) else 0.0
        night = amt if _NIGHT.search(line) else 0.0
        if morning + afternoon + night > 0:
            updates["dose"] = Dose(morning=morning, afternoon=afternoon, night=night, unit="unit")
            updates["form"] = "injection"
            if med.strength and re.search(r"unit", med.strength, re.I):
                updates["strength"] = None

    dose_now = updates.get("dose", med.dose)
    night_only = bool(_NIGHT.search(line) and not _MORNING.search(line) and not _NOON.search(line))
    times = sum(bool(p.search(line)) for p in (_MORNING, _NOON, _NIGHT))
    if "dose" not in updates and dose_now and not _DOSE_TRIPLE.search(line) and not _OD_BD.search(line):
        unit = dose_now.unit
        if med.form == "drops" or re.search(r"\bdrops?\b", line, re.I):
            unit = "drop"
        if times >= 2 and _guessed_od(dose_now):
            updates["dose"] = Dose(
                morning=1.0 if _MORNING.search(line) else 0.0,
                afternoon=1.0 if _NOON.search(line) else 0.0,
                night=1.0 if _NIGHT.search(line) else 0.0,
                unit=unit,
            )
        elif night_only and dose_now.morning > 0:
            night = dose_now.night if dose_now.night else 1.0
            updates["dose"] = Dose(morning=0.0, afternoon=0.0, night=night, unit=unit)

    if "dose" not in updates and med.dose is not None and med.kind == "daily" and not line_has_dose_cue(line):
        checks = list(med.needs_check or [])
        if "dose" not in checks:
            checks.append("dose")
        if "schedule" not in checks:
            checks.append("schedule")
        updates["dose"] = None
        updates["needs_check"] = checks

    if not updates:
        return med
    return med.model_copy(update=updates)
