"""Copy tokens that are literally on the line. Never guess a dose that is not written."""

from __future__ import annotations

import re

from pillclerk.normalize import drug_eq, strength_eq
from pillclerk.schema import Dose, Form, MedLine

_FORM_CUES: list[tuple[re.Pattern[str], Form, str]] = [
    (re.compile(r"\b(capsules?|cap\.?)\b", re.I), "cap", "cap"),
    (re.compile(r"\b(tablets?|tab\.?)\b", re.I), "tab", "tab"),
    (re.compile(r"\b(syrup|syp\.?|syr\.?|suspension)\b", re.I), "syrup", "ml"),
    (re.compile(r"\b(drops?)\b", re.I), "drops", "drop"),
    (re.compile(r"\b(inhaler|inh\.?|puff|nebuli[sz]e)\b", re.I), "inhaler", "puff"),
    (re.compile(r"\b(injection|inj\.?|insulin)\b", re.I), "injection", "unit"),
    (re.compile(r"\b(cream|ointment)\b", re.I), "cream", "apply"),
    (re.compile(r"\b(sachet)\b", re.I), "sachet", "sachet"),
    (re.compile(r"\bgargle\b", re.I), "other", "apply"),
]

_FOOD_CUES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"before food|\bac\b|खाने से पहले|जेवणाआधी|khane se pehle", re.I), "before"),
    (re.compile(r"after food|\bpc\b|after\s+bf\b|after breakfast|खाने के बाद|जेवणानंतर|khane ke baad", re.I), "after"),
    (re.compile(r"with food|\bwf\b|खाने के साथ|जेवणासोबत|khane ke saath", re.I), "with"),
    (
        re.compile(r"empty stomach|\bes\b|\bbbf\b|before breakfast|खाली पेट|उपाशीपोटी|khali pet", re.I),
        "empty_stomach",
    ),
]

_MONTH = re.compile(r"\b1/12\b")
_PRN = re.compile(r"\b(sos|prn|zarurat|जरूरत|गरजेनुसार)\b", re.I)
_STAT = re.compile(r"\bstat\b", re.I)
_MAX_N = re.compile(r"\bmax\s*(\d+)\s*(?:/\s*d)?\b", re.I)
_MAX_DIN = re.compile(r"दिवसाला\s*(\d+)|din\s*mein\s*(\d+)", re.I)
_DUR_X = re.compile(r"\bx\s*(\d+)\s*d(?:ays?)?\b", re.I)
_DUR_DIN = re.compile(r"\b(\d+)\s*(?:din|दिन|दिवस)\b", re.I)
_DUR_DAY_EN = re.compile(r"\b(?:x\s*)?(\d+)\s*days?\b", re.I)
_DUR_MONTH = re.compile(r"\b(?:x\s*)?(\d+)\s*months?\b", re.I)
_CONTINUE = re.compile(r"\b(?:continue|cont)\b", re.I)
_COMBO = re.compile(r"\s+(AM|AV|LS|GP\d*|XR|SR|CR|PLUS|XP|XT|FX|LC|DS|DDS|CS|CD\d+)\b", re.I)
_DEVICE = re.compile(r"\s+(MDI|HFA|DPI|IV|IM|SC|PO)\b", re.I)
_DOSE_TRIPLE = re.compile(
    r"([0-9½¼¾]+(?:\.\d+)?)\s*(?:ml|mg|u|units?)?\s*-\s*"
    r"([0-9½¼¾]+(?:\.\d+)?)\s*(?:ml|mg|u|units?)?\s*-\s*"
    r"([0-9½¼¾]+(?:\.\d+)?)\s*(?:ml|mg|u|units?)?",
    re.I,
)
_OD_BD = re.compile(r"\b(OD|BD|TDS|QID|HS)\b", re.I)
_ONCE = re.compile(r"\b(?:once\s+(?:a|per)\s+day|once\s+daily|1\s+daily)\b", re.I)
_TWICE = re.compile(r"\b(?:twice(?:\s+a\s+day|\s+daily)?|two\s+times(?:\s+a\s+day)?)\b", re.I)
_THRICE = re.compile(r"\b(?:thrice(?:\s+a\s+day|\s+daily)?|three\s+times(?:\s+a\s+day)?)\b", re.I)
_AT_NIGHT = re.compile(r"\b(?:at\s+night|at\s+bedtime|bedtime)\b", re.I)
_DAILY_WORD = re.compile(r"\b(?:daily|every\s+day)\b", re.I)
_BBF = re.compile(r"\bbbf\b|before\s+breakfast", re.I)
_PM = re.compile(r"\b(?:at\s+)?(?:[01]?\d|2[0-3])\s*pm\b", re.I)
_MORNING = re.compile(r"subah|सुबह|सकाळी", re.I)
_NOON = re.compile(r"dopahar|दोपहर|दुपारी", re.I)
_NIGHT = re.compile(r"raat(?:\s*ko)?|रात(?:\s*को)?|रात्री", re.I)
_UNIT_AMT = re.compile(r"\b(\d+(?:\.\d+)?)\s*units?\b", re.I)
_WEEKLY = re.compile(r"hafte|weekly|once\s+(?:a|per)\s+week|आठवड", re.I)
_ML_AMT = re.compile(r"\b(\d+(?:\.\d+)?)\s*ml\b", re.I)
_AMT_UNIT = re.compile(
    r"\b(\d+(?:\.\d+)?|½|¼|¾)\s*(puffs?|tabs?|tablets?|ml|sachets?|caps?|capsules?|units?|drops?)\b",
    re.I,
)
_AMT_X = re.compile(r"\b(\d+(?:\.\d+)?|½|¼|¾)\s*(?:tab|tablet|puff|sachet|cap)?s?\s*x\b", re.I)
_FORM_LEAD = re.compile(
    r"^(?:\d+\.\s*)?(?:tab(?:let)?s?|cap(?:sule)?s?|syp|syr(?:up)?|inh|inj|"
    r"drops?|sachet|suspension|injection|cream|ointment|nebuli[sz]e(?:\s+with)?)\.?\s+",
    re.I,
)
_UNIT_FROM_WORD = {
    "puff": "puff",
    "puffs": "puff",
    "tab": "tab",
    "tabs": "tab",
    "tablet": "tab",
    "tablets": "tab",
    "ml": "ml",
    "sachet": "sachet",
    "sachets": "sachet",
    "cap": "cap",
    "caps": "cap",
    "capsule": "cap",
    "capsules": "cap",
    "unit": "unit",
    "units": "unit",
    "drop": "drop",
    "drops": "drop",
}
_UNIT = r"(?:mg|mcg|iu|ml|g|k|%)"
_STRENGTH_SPAN = re.compile(
    rf"\d+(?:\.\d+)?(?:\s*{_UNIT})?(?:\s*/\s*\d+(?:\.\d+)?(?:\s*{_UNIT})?)?",
    re.I,
)
_WORD = re.compile(r"[\u0900-\u097FA-Za-z][\u0900-\u097FA-Za-z]*")


def line_has_food_word(line: str) -> bool:
    return any(pat.search(line) for pat, _ in _FOOD_CUES)


def _qty(tok: str) -> float:
    tok = tok.strip()
    if tok in {"½", "1/2"}:
        return 0.5
    if tok in {"¼", "1/4"}:
        return 0.25
    if tok in {"¾", "3/4"}:
        return 0.75
    return float(tok)


def duration_from_line(line: str) -> int | None | str:
    """Return written duration, None if continue/absent, or 'ambiguous'."""
    if _MONTH.search(line):
        return 30
    found = [int(m.group(1)) for m in _DUR_X.finditer(line)]
    found += [int(m.group(1)) for m in _DUR_DIN.finditer(line)]
    found += [int(m.group(1)) for m in _DUR_DAY_EN.finditer(line)]
    found += [int(m.group(1)) * 30 for m in _DUR_MONTH.finditer(line)]
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
        or _AT_NIGHT.search(line)
        or _ONCE.search(line)
        or _TWICE.search(line)
        or _THRICE.search(line)
        or _DAILY_WORD.search(line)
        or _BBF.search(line)
        or _PM.search(line)
        or _UNIT_AMT.search(line)
        or _WEEKLY.search(line)
        or _AMT_X.search(line)
        or len(_ML_AMT.findall(line)) >= 2
    )


def _guessed_od(dose: Dose | None) -> bool:
    return bool(dose and dose.morning == 1 and dose.afternoon == 0 and dose.night == 0)


def _strip_device(name: str) -> str:
    return _DEVICE.sub("", name).strip()


def _surface_drug(line: str, pred_drug: str) -> str | None:
    pred_drug = _strip_device(pred_drug)
    parts = pred_drug.split()
    first = parts[0]
    if len(parts) == 1:
        combo = re.search(rf"{re.escape(first)}{_COMBO.pattern}", line, re.I)
        if combo:
            return _strip_device(combo.group(0).strip())
        solo_s = re.search(rf"{re.escape(first)}\s+S\b", line)
        if solo_s:
            return solo_s.group(0).strip()
    words = _WORD.findall(line)
    hits = [w for w in words if drug_eq(w, pred_drug)]
    if not hits:
        return pred_drug if pred_drug else None
    return max(hits, key=len)


def _leading_drug(line: str) -> str | None:
    s = _FORM_LEAD.sub("", line.strip())
    m = re.match(
        r"([A-Za-z\u0900-\u097F][A-Za-z\u0900-\u097F0-9./-]*"
        r"(?:\s+(?:AM|AV|LS|GP\d*|XR|SR|CR|PLUS|XP|XT|FX|LC|DS|DDS|CS|CD\d+|S))?"
        r"(?:\s+[A-Za-z][A-Za-z0-9./-]*)?)",
        s,
    )
    if not m:
        return None
    drug = m.group(1).strip()
    drug = re.split(r"\s+\d", drug, maxsplit=1)[0].strip(" -")
    strength_tail = re.search(r"[- ](\d+(?:\.\d+)?(?:mg|g|ml|mcg|k))$", drug, re.I)
    if strength_tail:
        drug = drug[: strength_tail.start()].strip(" -")
    if not drug or drug.lower() in {"tab", "cap", "syrup", "inh", "inj", "sachet"}:
        return None
    return _strip_device(drug)


def _default_unit(line: str, med: MedLine) -> str:
    forms = [(form, unit) for pat, form, unit in _FORM_CUES if pat.search(line)]
    unique = {f for f, _ in forms}
    if len(unique) == 1:
        return forms[0][1]
    if med.dose is not None:
        return med.dose.unit
    form_unit = {
        "tab": "tab",
        "cap": "cap",
        "syrup": "ml",
        "drops": "drop",
        "inhaler": "puff",
        "injection": "unit",
        "cream": "apply",
        "sachet": "sachet",
        "other": "apply",
    }
    return form_unit.get(med.form, "tab")


def _amount_and_unit(line: str, default_unit: str) -> tuple[float, str]:
    ranked: list[tuple[int, float, str]] = []
    rank = {"puff": 0, "sachet": 1, "unit": 2, "tab": 3, "cap": 4, "drop": 5, "ml": 6}
    for m in _AMT_UNIT.finditer(line):
        unit = _UNIT_FROM_WORD[m.group(2).lower()]
        prefix = line[max(0, m.start() - 16) : m.start()]
        if unit == "ml" and re.search(r"(?:mg|mcg|g)\s*/\s*$", prefix, re.I):
            continue
        if unit == "ml" and re.search(r"(?:mixed\s+in|in)\s+$", prefix, re.I):
            continue
        amt = _qty(m.group(1))
        if amt > 20:
            continue
        ranked.append((rank.get(unit, 9), amt, unit))
    if ranked:
        ranked.sort()
        return ranked[0][1], ranked[0][2]
    m = _AMT_X.search(line)
    if m:
        return _qty(m.group(1)), default_unit
    return 1.0, default_unit


def _freq_slots(line: str) -> tuple[float, float, float] | None:
    """Return 1/0 multipliers for morning, afternoon, night from written frequency."""
    if re.search(r"\bQID\b", line, re.I):
        return None
    hs = bool(re.search(r"\bHS\b", line, re.I))
    night = bool(_NIGHT.search(line) or _AT_NIGHT.search(line) or _PM.search(line) or hs)
    morning = bool(_MORNING.search(line) or _BBF.search(line))
    noon = bool(_NOON.search(line))
    if re.search(r"\bTDS\b", line, re.I) or _THRICE.search(line):
        return (1.0, 1.0, 1.0)
    if re.search(r"\bBD\b", line, re.I) or _TWICE.search(line):
        return (1.0, 0.0, 1.0)
    if _AT_NIGHT.search(line) or hs or (_PM.search(line) and not morning and not noon):
        return (0.0, 0.0, 1.0)
    if night and not morning and not noon and not _ONCE.search(line) and not re.search(r"\bOD\b", line, re.I):
        return (0.0, 0.0, 1.0)
    if (
        _ONCE.search(line)
        or re.search(r"\bOD\b", line, re.I)
        or _BBF.search(line)
        or _DAILY_WORD.search(line)
        or _WEEKLY.search(line)
    ):
        if night and not morning:
            return (0.0, 0.0, 1.0)
        return (1.0, 0.0, 0.0)
    times = sum(bool(p.search(line)) for p in (_MORNING, _NOON, _NIGHT))
    if times:
        return (
            1.0 if morning else 0.0,
            1.0 if noon else 0.0,
            1.0 if night else 0.0,
        )
    return None


def _dose_from_line(line: str, unit: str) -> Dose | None:
    from pydantic import ValidationError

    try:
        triple = _DOSE_TRIPLE.search(line)
        if triple:
            ml_unit = "ml" if re.search(r"ml", triple.group(0), re.I) else unit
            return Dose(
                morning=_qty(triple.group(1)),
                afternoon=_qty(triple.group(2)),
                night=_qty(triple.group(3)),
                unit=ml_unit,
            )
        slots = _freq_slots(line)
        if slots is None:
            return None
        amt, amt_unit = _amount_and_unit(line, unit)
        return Dose(
            morning=slots[0] * amt,
            afternoon=slots[1] * amt,
            night=slots[2] * amt,
            unit=amt_unit,
        )
    except (ValidationError, ValueError):
        return None


def _ml_is_dose_not_strength(line: str, strength: str | None) -> bool:
    if not strength or not re.search(r"ml", strength, re.I):
        return False
    if re.search(r"(?:mg|mcg|g)\s*/\s*\d", line, re.I):
        return False
    triple = _DOSE_TRIPLE.search(line)
    if triple and re.search(r"ml", triple.group(0), re.I):
        return True
    return bool(
        _ONCE.search(line)
        or _TWICE.search(line)
        or _THRICE.search(line)
        or _DAILY_WORD.search(line)
        or _AT_NIGHT.search(line)
        or _OD_BD.search(line)
    )


def stub_from_line(line: str) -> MedLine:
    """Schema-valid copy of tokens on the line when the model JSON failed."""
    kind: str = "prn" if (_PRN.search(line) or _STAT.search(line)) else "daily"
    forms = [form for pat, form, _ in _FORM_CUES if pat.search(line)]
    form: Form = forms[0] if len(set(forms)) == 1 else "other"
    drug = _leading_drug(line)
    checks: list[str] = []
    if not drug:
        checks.append("drug")
    if kind == "daily":
        checks.append("dose")
    if "drug" not in checks:
        checks.append("drug")
    return MedLine(drug=drug, form=form, kind=kind, food="any", needs_check=checks)


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

    written_dur = duration_from_line(line)
    if written_dur != "ambiguous" and med.kind != "taper":
        if _MONTH.search(line) and med.duration_days in (None, 1, 12):
            updates["duration_days"] = 30
        elif isinstance(written_dur, int) and med.duration_days != written_dur:
            if med.duration_days in (None, 1, 12) or _DUR_MONTH.search(line) or _DUR_DAY_EN.search(line):
                updates["duration_days"] = written_dur

    written_max = prn_max_from_line(line)
    if written_max is not None:
        updates["prn_max_per_day"] = written_max

    if _STAT.search(line) or _PRN.search(line):
        updates["kind"] = "prn"
        updates["dose"] = None

    if med.drug:
        surface = _surface_drug(line, med.drug)
        if surface:
            updates["drug"] = surface
    elif not med.drug:
        lead = _leading_drug(line)
        if lead:
            updates["drug"] = lead

    if med.strength:
        surface_s = _surface_strength(line, med.strength)
        if surface_s:
            updates["strength"] = surface_s

    unit_amt = _UNIT_AMT.search(line)
    if unit_amt and not re.search(r"IU\s*/\s*ml", line, re.I) and "dose" not in updates:
        amt = float(unit_amt.group(1))
        slots = _freq_slots(line)
        morning = amt if _MORNING.search(line) else 0.0
        afternoon = amt if _NOON.search(line) else 0.0
        night = amt if (_NIGHT.search(line) or _AT_NIGHT.search(line) or _PM.search(line)) else 0.0
        if slots:
            updates["dose"] = Dose(
                morning=slots[0] * amt,
                afternoon=slots[1] * amt,
                night=slots[2] * amt,
                unit="unit",
            )
            updates["form"] = "injection"
        elif morning + afternoon + night > 0:
            updates["dose"] = Dose(morning=morning, afternoon=afternoon, night=night, unit="unit")
            updates["form"] = "injection"
        strength_now = updates.get("strength", med.strength)
        if strength_now and (
            re.search(r"unit", str(strength_now), re.I)
            or strength_eq(strength_now, unit_amt.group(1))
            or strength_eq(strength_now, f"{unit_amt.group(1)} unit")
        ):
            updates["strength"] = None

    unit = _default_unit(line, med)
    kind_now = updates.get("kind", med.kind)
    if "dose" not in updates and kind_now != "prn" and kind_now != "taper":
        parsed = _dose_from_line(line, unit)
        dose_now = med.dose
        if parsed is not None and (dose_now is None or _guessed_od(dose_now) or _DOSE_TRIPLE.search(line)):
            updates["dose"] = parsed
        elif dose_now and not _DOSE_TRIPLE.search(line) and not _OD_BD.search(line):
            night_only = bool(
                (_NIGHT.search(line) or _AT_NIGHT.search(line))
                and not _MORNING.search(line)
                and not _NOON.search(line)
            )
            times = sum(bool(p.search(line)) for p in (_MORNING, _NOON, _NIGHT))
            if times >= 2 and _guessed_od(dose_now):
                updates["dose"] = Dose(
                    morning=1.0 if _MORNING.search(line) else 0.0,
                    afternoon=1.0 if _NOON.search(line) else 0.0,
                    night=1.0 if _NIGHT.search(line) else 0.0,
                    unit=unit if (med.form == "drops" or re.search(r"\bdrops?\b", line, re.I)) else dose_now.unit,
                )
            elif night_only and dose_now.morning > 0:
                night = dose_now.night if dose_now.night else 1.0
                updates["dose"] = Dose(morning=0.0, afternoon=0.0, night=night, unit=dose_now.unit)

    if "dose" not in updates and med.dose is not None and kind_now == "daily" and not line_has_dose_cue(line):
        checks = list(med.needs_check or [])
        if "dose" not in checks:
            checks.append("dose")
        if "schedule" not in checks:
            checks.append("schedule")
        updates["dose"] = None
        updates["needs_check"] = checks

    if _WEEKLY.search(line) and med.every_n_days == 1:
        updates["every_n_days"] = 7

    strength_now = updates.get("strength", med.strength)
    if _ml_is_dose_not_strength(line, strength_now):
        updates["strength"] = None

    dose_final = updates.get("dose", med.dose)
    if dose_final is not None and kind_now == "daily":
        drop = {"dose"}
        if "except" not in line.lower():
            drop.add("schedule")
        checks = [c for c in (updates.get("needs_check", med.needs_check) or []) if c not in drop]
        updates["needs_check"] = checks

    if not updates:
        return med
    return med.model_copy(update=updates)
