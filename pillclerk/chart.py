"""Big-font printable fridge chart (HTML; print from the browser, A4 landscape)."""

from __future__ import annotations

from html import escape

from pillclerk.schedule import Dosing
from pillclerk.schema import MedLine

LABELS = {
    "en": {
        "morning": "☀️ Morning",
        "afternoon": "🌤️ Afternoon",
        "night": "🌙 Night",
        "tab": "tab",
        "after": "after food",
        "before": "before food",
        "with": "with food",
        "empty_stomach": "empty stomach",
        "any": "",
        "prn": "Only if needed",
        "ask": "ASK",
    },
    "mr": {
        "morning": "☀️ सकाळी",
        "afternoon": "🌤️ दुपारी",
        "night": "🌙 रात्री",
        "tab": "गोळी",
        "after": "जेवणानंतर",
        "before": "जेवणाआधी",
        "with": "जेवणासोबत",
        "empty_stomach": "उपाशीपोटी",
        "any": "",
        "prn": "गरज लागली तरच",
        "ask": "विचारा",
    },
    "hi": {
        "morning": "☀️ सुबह",
        "afternoon": "🌤️ दोपहर",
        "night": "🌙 रात",
        "tab": "गोली",
        "after": "खाने के बाद",
        "before": "खाने से पहले",
        "with": "खाने के साथ",
        "empty_stomach": "खाली पेट",
        "any": "",
        "prn": "जरूरत पर ही",
        "ask": "पूछें",
    },
}


def _amt(amount: float) -> str:
    return "½" if amount == 0.5 else f"{amount:g}"


def chart_html(
    plan: list[Dosing],
    lang: str = "mr",
    footer: str = "",
    prn: list[MedLine] | None = None,
) -> str:
    L = LABELS.get(lang, LABELS["en"])
    rows: list[str] = []
    for slot in ("morning", "afternoon", "night"):
        cells = "".join(
            f"<div class='pill'><b>{escape(d.med.drug or L['ask'])}</b> {escape(d.med.strength or '')}"
            f"<br/>{_amt(d.amount)} {L['tab']} · {L[d.med.food]}</div>"
            for d in plan
            if d.slot == slot
        ) or "—"
        rows.append(f"<tr><th>{L[slot]}</th><td>{cells}</td></tr>")
    if prn:
        cells = "".join(
            f"<div class='pill'><b>{escape(m.drug or L['ask'])}</b> {escape(m.strength or '')}"
            f"<br/>{L['prn']}</div>"
            for m in prn
        )
        rows.append(f"<tr><th>{L['prn']}</th><td>{cells}</td></tr>")
    return f"""<!doctype html><meta charset="utf-8">
<style>@page{{size:A4 landscape;margin:12mm}} body{{font-family:'Noto Sans Devanagari','Noto Sans',sans-serif}}
th{{font-size:40px;text-align:left;padding:12px 24px;white-space:nowrap}} td{{font-size:30px}}
.pill{{display:inline-block;border:3px solid #333;border-radius:14px;padding:10px 18px;margin:8px}}
.ask{{border-color:#c00;color:#c00}}
tr{{border-bottom:4px solid #999}} footer{{font-size:16px;margin-top:20px}}</style>
<table>{''.join(rows)}</table><footer>{escape(footer)}</footer>"""
