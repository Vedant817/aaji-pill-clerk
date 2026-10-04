"""Big-font printable fridge chart (HTML; print from the browser, A4 landscape)."""

from __future__ import annotations

from html import escape
from datetime import time, timedelta

from pillclerk.schedule import Dosing, SLOTS
from pillclerk.schema import MedLine
from pillclerk.provenance import context_text, reminder_times

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
        "no_end": "No end date recorded — verify written continuation",
        "every": "every {n} days",
        "maximum": "max {n}/day",
        "footer": "Clerk copy of the prescription. Not medical advice. If anything looks different, ask the doctor or pharmacist.",
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
        "no_end": "शेवटची तारीख नोंदलेली नाही — पुढे चालू ठेवण्याची लिखित सूचना तपासा",
        "every": "दर {n} दिवसांनी",
        "maximum": "कमाल {n}/दिवस",
        "footer": "डॉक्टरांच्या प्रिस्क्रिप्शनची प्रत. हा वैद्यकीय सल्ला नाही. फरक दिसल्यास डॉक्टर किंवा फार्मासिस्टला विचारा.",
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
        "no_end": "अंतिम तारीख दर्ज नहीं है — जारी रखने का लिखित निर्देश जाँचें",
        "every": "हर {n} दिन",
        "maximum": "अधिकतम {n}/दिन",
        "footer": "डॉक्टर के पर्चे की प्रति। यह चिकित्सा सलाह नहीं है। कोई अंतर दिखे तो डॉक्टर या फार्मासिस्ट से पूछें।",
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
    context: dict | None = None,
) -> str:
    L = LABELS.get(lang, LABELS["en"])
    times = reminder_times(slot_times, context)
    rows: list[str] = []
    for slot in ("morning", "afternoon", "night"):
        cells = "".join(
            f"<div class='pill'><b>{escape(d.med.drug or L['ask'])}</b> {escape(d.med.strength or '')}"
            f"<br/>{_amt(d.amount)} {L['tab'] if d.unit == 'tab' else escape(d.unit)} · {L[d.med.food]}"
            f"<br/>{d.start.isoformat()} → {(d.start + timedelta(days=d.days - 1)).isoformat() if d.days else L['no_end']}"
            f"{' · ' + L['every'].format(n=d.every_n_days) if d.every_n_days > 1 else ''}"
            f"{'<br/>' + escape(d.med.note) if d.med.note else ''}</div>"
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
            f"{' · ' + L['maximum'].format(n=m.prn_max_per_day) if m.prn_max_per_day else ''}"
            f"{'<br/>' + escape(m.note) if m.note else ''}</div>"
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
<table>{''.join(rows)}</table><footer style="white-space:pre-line">{escape(context_text(context, lang))}\n{escape(footer)}</footer>"""
