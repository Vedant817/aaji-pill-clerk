"""Paste prescription lines (EXTRACT_BACKEND=manual). Photos stay on this machine."""

from pillclerk.ui import apply_theme, stepper
from pillclerk.ocr import lines_from_text
from pillclerk.schema import Dose, MedLine

apply_theme()
import streamlit as st

stepper("Scan")
st.title("Scan")
st.caption("Paste one medicine line per row. Photo OCR is off (no DigitalOcean, no local Gemma).")

text = st.text_area(
    "Prescription lines",
    height=240,
    placeholder="TAB. Glycomet 500MG  1-0-1  AFTER FOOD  x 30 DAYS\nTab Telma 40mg OD ES 1/12",
)
c1, c2 = st.columns([1, 3])
with c1:
    load = st.button("Load lines", type="primary")
if load and text.strip():
    lines = lines_from_text(text)
    drafts: list[dict] = []
    for line in lines:
        drafts.append(
            {
                "line": line,
                "gold": MedLine(
                    drug=None,
                    kind="daily",
                    dose=Dose(),
                    needs_check=["drug", "dose", "schedule"],
                    note=line,
                ).model_dump(),
                "confirmed": False,
            }
        )
    st.session_state["drafts"] = drafts
    st.session_state.pop("parse_note", None)
    st.success(f"Loaded {len(drafts)} lines. Open Review to confirm each one.")
    st.page_link("pages/2_Review.py", label="Go to Review →")
elif load:
    st.warning("Paste at least one line.")
