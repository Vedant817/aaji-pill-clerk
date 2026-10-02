"""Append a photographed family line to gitignored data/real/gt.jsonl."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pillclerk.ui import apply_theme
from eval.family_real import REAL, rows, write
from pillclerk.schema import CheckField, Dose, Food, Form, Kind, MedLine, Unit
from pillclerk.validate import extra_rules

apply_theme()
import streamlit as st

st.title("Label REAL")
st.caption(
    "Photographed family lines only. Gold must copy the slip. Photos stay in data/real/raw/ (gitignored). "
    "The bundled hand-written realistic set is not REAL."
)

if st.button("Write bundled hand-written realistic set (not photographed)"):
    stats = write()
    st.success(
        f"Wrote {stats['n']} hand-written realistic lines "
        f"({stats['sources']} slips, {stats['whatsapp']} WhatsApp). Not REAL."
    )

line = st.text_area("Transcribed line", height=80)
c1, c2, c3 = st.columns(3)
drug = c1.text_input("Drug")
strength = c2.text_input("Strength")
FORMS: list[Form] = ["tab", "cap", "syrup", "drops", "inhaler", "injection", "cream", "sachet", "other"]
form = c3.selectbox("Form", FORMS)
c1, c2, c3 = st.columns(3)
KINDS: list[Kind] = ["daily", "prn", "taper"]
FOODS: list[Food] = ["before", "after", "with", "empty_stomach", "any"]
kind = c1.selectbox("Kind", KINDS)
food = c2.selectbox("Food", FOODS)
duration = c3.number_input("Duration days (0=continue)", min_value=0, value=0)
m1, m2, m3, m4 = st.columns(4)
UNITS: list[Unit] = ["tab", "cap", "ml", "drop", "puff", "unit", "sachet", "apply"]
morning = m1.number_input("Morning", min_value=0.0, max_value=20.0, value=0.0, step=0.5)
afternoon = m2.number_input("Afternoon", min_value=0.0, max_value=20.0, value=0.0, step=0.5)
night = m3.number_input("Night", min_value=0.0, max_value=20.0, value=0.0, step=0.5)
unit = m4.selectbox("Unit", UNITS)
prn = st.number_input("PRN max/day (0=unset)", min_value=0, value=0)
CHECKS: list[CheckField] = ["drug", "strength", "dose", "food", "duration_days", "schedule"]
flags = st.multiselect("needs_check (ASK)", CHECKS)

if st.button("Append line", type="primary"):
    if not line.strip():
        st.warning("Paste a line first.")
    else:
        dose = None if kind == "prn" else Dose(morning=morning, afternoon=afternoon, night=night, unit=unit)
        med = extra_rules(
            MedLine(
                drug=drug.strip() or None,
                strength=strength.strip() or None,
                form=form,
                kind=kind,
                dose=dose,
                food=food,
                duration_days=int(duration) or None,
                prn_max_per_day=int(prn) or None,
                needs_check=flags,
                note=line.strip(),
            )
        )
        REAL.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "line": line.strip(),
            "gold": json.loads(med.model_dump_json()),
            "source": "manual",
            "style": "transcribed",
            "synthetic": False,
            "held_out": True,
        }
        with REAL.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        st.success(f"Appended. File now has more than the bundled {len(rows())} lines.")
