"""Big-font printable fridge chart (HTML; print from the browser, A4 landscape)."""

from __future__ import annotations

from html import escape
from datetime import time, timedelta

from pillclerk.schedule import Dosing, SLOTS
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
        "days": "days",
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
        "days": "दिवस",
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
        "days": "दिन",
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
    slot_times: dict[str, time] | None = None,
) -> str:
    L = LABELS.get(lang, LABELS["en"])
    times = slot_times or SLOTS
    rows: list[str] = []
    for slot in ("morning", "afternoon", "night"):
        cells = "".join(
            f"<div class='pill'><b>{escape(d.med.drug or L['ask'])}</b> {escape(d.med.strength or '')}"
            f"<br/>{_amt(d.amount)} {L['tab'] if d.unit == 'tab' else escape(d.unit)} · {L[d.med.food]}"
            f"<br/>{d.start.isoformat()} → {(d.start + timedelta(days=d.days - 1)).isoformat() if d.days else 'until changed'}"
            f"{' · every ' + str(d.every_n_days) + ' days' if d.every_n_days > 1 else ''}</div>"
            for d in plan
            if d.slot == slot
        ) or "—"
        rows.append(f"<tr><th>{L[slot]}<br/>{times[slot].strftime('%H:%M')}</th><td>{cells}</td></tr>")
    if prn:
        cells = "".join(
            f"<div class='pill'><b>{escape(m.drug or L['ask'])}</b> {escape(m.strength or '')}"
            f"<br/>{L['prn']}"
            f"{' · ' + L[m.food] if L[m.food] else ''}"
            f"{' · ' + str(m.duration_days) + ' ' + L['days'] if m.duration_days is not None else ''}"
            f"{' · max ' + str(m.prn_max_per_day) + '/day' if m.prn_max_per_day else ''}</div>"
            for m in prn
        )
        rows.append(f"<tr><th>{L['prn']}</th><td>{cells}</td></tr>")
    return f"""<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Figtree:wght@600;700&family=Noto+Sans:wght@500;700&family=Noto+Sans+Devanagari:wght@600;700&display=swap">
<style>
@page{{size:A4 landscape;margin:12mm}}
body{{font-family:'Noto Sans Devanagari','Noto Sans','Figtree',sans-serif;background:#F0F9FF;color:#0C4A6E;margin:0;padding:12px}}
table{{width:100%;border-collapse:separate;border-spacing:0 10px}}
th{{font-family:'Figtree',sans-serif;font-size:36px;text-align:left;padding:14px 20px;white-space:nowrap;color:#0369A1;width:220px}}
td{{font-size:28px}}
.pill{{display:inline-block;background:#FFFFFF;border:2px solid #E0F2FE;border-radius:18px;padding:12px 18px;margin:6px;box-shadow:0 8px 20px rgba(12,74,110,.08)}}
.ask{{border-color:#DC2626;color:#DC2626}}
footer{{font-size:16px;margin-top:16px;color:#475569}}
</style>
<table>{''.join(rows)}</table><footer>{escape(footer)}</footer>"""
