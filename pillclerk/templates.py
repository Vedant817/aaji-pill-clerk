"""Deterministic messy-text renderer (the 30% template path). No LLM."""

from __future__ import annotations

import random

from pillclerk.schema import Dose, MedLine

STYLES = (
    "clinic_print",
    "doctor_short",
    "hinglish_wa",
    "hindi",
    "marathi",
    "mixed",
)

_FOOD_EN = {
    "before": "BEFORE FOOD",
    "after": "AFTER FOOD",
    "with": "WITH FOOD",
    "empty_stomach": "EMPTY STOMACH",
    "any": "",
}
_FOOD_SHORT = {
    "before": "AC",
    "after": "PC",
    "with": "WF",
    "empty_stomach": "ES",
    "any": "",
}
_FOOD_HI = {
    "before": "खाने से पहले",
    "after": "खाने के बाद",
    "with": "खाने के साथ",
    "empty_stomach": "खाली पेट",
    "any": "",
}
_FOOD_MR = {
    "before": "जेवणाआधी",
    "after": "जेवणानंतर",
    "with": "जेवणासोबत",
    "empty_stomach": "उपाशीपोटी",
    "any": "",
}
_FOOD_HINGLISH = {
    "before": "khane se pehle",
    "after": "khane ke baad",
    "with": "khane ke saath",
    "empty_stomach": "khali pet",
    "any": "",
}

_FORM_EN = {
    "tab": "TAB.",
    "cap": "CAP.",
    "syrup": "SYR.",
    "drops": "DROPS",
    "inhaler": "INH.",
    "injection": "INJ.",
    "cream": "CREAM",
    "sachet": "SACHET",
    "other": "",
}
_FORM_SHORT = {
    "tab": "Tab",
    "cap": "Cap",
    "syrup": "Syr",
    "drops": "Drops",
    "inhaler": "Inh",
    "injection": "Inj",
    "cream": "Cream",
    "sachet": "Sachet",
    "other": "Tab",
}


def dose_code(dose: Dose) -> str:
    def fmt(x: float) -> str:
        if x == 0.5:
            return "½"
        if x == int(x):
            return str(int(x))
        return f"{x:g}"

    return f"{fmt(dose.morning)}-{fmt(dose.afternoon)}-{fmt(dose.night)}"


def latin_abbrev(dose: Dose) -> str:
    m, a, n = dose.morning, dose.afternoon, dose.night
    if any(x not in (0, 0.0, 1, 1.0) for x in (m, a, n)):
        return dose_code(dose)
    if m and not a and not n:
        return "OD"
    if n and not m and not a:
        return "HS"
    if m and n and not a and m == n:
        return "BD"
    if m and a and n:
        return "TDS"
    return dose_code(dose)


def _dur(days: int | None, style: str, *, omit: bool = False) -> str:
    if omit:
        return ""
    if days is None:
        return {"clinic_print": "CONTINUE", "doctor_short": "cont", "hinglish_wa": "continue"}.get(style, "")
    if style == "clinic_print":
        return f"x {days} DAYS"
    if style == "doctor_short":
        return f"x{days}d" if days != 30 else "1/12"
    if style == "hinglish_wa":
        return f"{days} din"
    if style == "hindi":
        return f"{days} दिन"
    if style == "marathi":
        return f"{days} दिवस"
    return f"x {days}d"


def _amount_words(x: float, lang: str) -> str:
    half = {"hi": "आधी", "mr": "अर्धी", "hinglish": "aadhi"}
    one = {"hi": "एक", "mr": "एक", "hinglish": "ek"}
    two = {"hi": "दो", "mr": "दोन", "hinglish": "do"}
    if x == 0.5:
        return half[lang]
    if x == 1:
        return one[lang]
    if x == 2:
        return two[lang]
    if x == int(x):
        return str(int(x))
    return f"{x:g}"


def _slot_line(med: MedLine, lang: str) -> str:
    assert med.dose is not None
    d = med.dose
    parts: list[str] = []
    if lang == "hi":
        labels = (("सुबह", d.morning), ("दोपहर", d.afternoon), ("रात", d.night))
        joiner, word_lang = " ", "hi"
    elif lang == "mr":
        labels = (("सकाळी", d.morning), ("दुपारी", d.afternoon), ("रात्री", d.night))
        joiner, word_lang = " ", "mr"
    else:
        labels = (("subah", d.morning), ("dopahar", d.afternoon), ("raat ko", d.night))
        joiner, word_lang = " ", "hinglish"
    for label, amt in labels:
        if amt:
            parts.append(f"{label} {_amount_words(amt, word_lang)}")
    return joiner.join(parts)


def _weekly(med: MedLine, style: str) -> str:
    if med.every_n_days == 7:
        if style in {"hindi"}:
            return " हफ्ते में एक बार"
        if style == "marathi":
            return " आठवड्यातून एकदा"
        if style == "hinglish_wa":
            return " hafte mein ek baar"
        return " WEEKLY"
    if med.every_n_days > 1:
        return f" every {med.every_n_days}d"
    return ""


def render_hard_negative(gold: MedLine, style: str) -> str:
    name = gold.drug or "[?]"
    strength = gold.strength or ""
    note = gold.note or ""
    form = _FORM_SHORT.get(gold.form, "Tab")
    if "illegible" in note or gold.drug is None:
        return f"{form} {name} {strength} 1-[?]-[?] { _dur(gold.duration_days, 'doctor_short')}".strip()
    if "as directed" in note:
        return f"{form} {name} {strength} as directed".strip()
    return f"{form} {name} {strength} x {gold.duration_days or 5}d".strip()


def render_template(gold: MedLine, style: str, rng: random.Random | None = None) -> str:
    rng = rng or random.Random(0)
    if gold.needs_check and gold.kind == "daily" and gold.dose is None:
        return _noise(render_hard_negative(gold, style), rng)

    name = gold.drug or "ASK"
    strength = gold.strength or ""
    form = _FORM_EN.get(gold.form, "TAB.")
    form_short = _FORM_SHORT.get(gold.form, "Tab")

    if gold.kind == "prn":
        maxd = f" max {gold.prn_max_per_day}/d" if gold.prn_max_per_day else ""
        if style == "doctor_short":
            line = f"{form_short} {name} {strength} SOS{maxd} {_dur(gold.duration_days, style)}".strip()
        elif style == "hinglish_wa":
            line = f"{form_short} {name} {strength} zarurat pe {maxd} {_dur(gold.duration_days, style)}".strip()
        elif style == "hindi":
            line = f"{form_short} {name} {strength} जरूरत पर {_dur(gold.duration_days, style)}".strip()
        elif style == "marathi":
            line = f"{form_short} {name} {strength} गरजेनुसार {_dur(gold.duration_days, style)}".strip()
        else:
            line = f"{form} {name} {strength}  SOS / PRN{maxd}  {_dur(gold.duration_days, 'clinic_print')}".strip()
        return _noise(line, rng)

    if gold.kind == "taper" and gold.taper:
        s1, s2 = gold.taper[0], gold.taper[1] if len(gold.taper) > 1 else gold.taper[0]
        line = (
            f"{form} {name} {strength}  {dose_code(s1.dose)} x {s1.days}d then "
            f"{dose_code(s2.dose)} x {s2.days}d  {_FOOD_EN.get(gold.food, '')}"
        )
        return _noise(" ".join(line.split()), rng)

    assert gold.dose is not None
    weekly = _weekly(gold, style)
    omit_dur = "duration_days" in gold.needs_check
    if style == "clinic_print":
        food = _FOOD_EN[gold.food]
        line = f"{form} {name} {strength}  {dose_code(gold.dose)}  {food}  {_dur(gold.duration_days, style, omit=omit_dur)}{weekly}"
    elif style == "doctor_short":
        food = _FOOD_SHORT[gold.food]
        line = f"{form_short} {name} {strength} {latin_abbrev(gold.dose)} {food} {_dur(gold.duration_days, style, omit=omit_dur)}{weekly}"
    elif style == "hinglish_wa":
        food = _FOOD_HINGLISH[gold.food]
        line = f"{form_short} {name} {strength} {_slot_line(gold, 'hinglish')} {food} {_dur(gold.duration_days, style, omit=omit_dur)}{weekly}"
    elif style == "hindi":
        food = _FOOD_HI[gold.food]
        line = f"{form_short} {name} {strength} {_slot_line(gold, 'hi')} {food} {_dur(gold.duration_days, style, omit=omit_dur)}{weekly}"
    elif style == "marathi":
        food = _FOOD_MR[gold.food]
        line = f"{form_short} {name} {strength} {_slot_line(gold, 'mr')} {food} {_dur(gold.duration_days, style, omit=omit_dur)}{weekly}"
    else:  # mixed
        food = _FOOD_HINGLISH[gold.food]
        line = (
            f"{form.rstrip('.')} {name} {strength} {dose_code(gold.dose)} "
            f"{_slot_line(gold, 'hi')} {food} {_dur(gold.duration_days, 'doctor_short', omit=omit_dur)}{weekly}"
        )
    return _noise(" ".join(line.split()), rng)


def _noise(line: str, rng: random.Random) -> str:
    ops = rng.randint(0, 2)
    out = line
    for _ in range(ops):
        choice = rng.choice(["dots", "spaces", "rx", "num", "squash"])
        if choice == "dots":
            out = out.replace("TAB.", "TAB").replace("CAP.", "CAP").replace("tab.", "tab")
        elif choice == "spaces":
            out = out.replace("  ", " ")
        elif choice == "rx" and rng.random() < 0.5:
            out = "℞ " + out
        elif choice == "num" and rng.random() < 0.3:
            out = f"{rng.randint(1, 8)}. {out}"
        elif choice == "squash":
            out = out.replace(" mg", "mg").replace(" mcg", "mcg")
    return " ".join(out.split())
