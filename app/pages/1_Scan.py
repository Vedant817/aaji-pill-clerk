"""Paste prescription lines (EXTRACT_BACKEND=manual). Photos stay on this machine."""

from pillclerk.ui import apply_theme, stepper
from pillclerk.config import ROOT
from pillclerk.drafts import drafts_from_text

apply_theme()
import streamlit as st

DEMO = ROOT / "data" / "demo" / "prescriptions" / "aaji_sample.txt"

stepper("Scan")
st.title("Scan")
st.caption("Paste one medicine line per row. Photo OCR is off (no DigitalOcean, no local Gemma).")

text = st.text_area(
    "Prescription lines",
    height=240,
    placeholder="TAB. Glycomet 500MG  1-0-1  AFTER FOOD  x 30 DAYS\nTab Telma 40mg OD ES 1/12",
)
c0, c1 = st.columns([1, 1])
with c0:
    load_demo = st.button("Load demo slip")
with c1:
    load = st.button("Load lines", type="primary")

raw = ""
if load_demo:
    raw = DEMO.read_text(encoding="utf-8") if DEMO.is_file() else ""
elif load:
    raw = text.strip()

if raw:
    drafts = drafts_from_text(raw)
    st.session_state["drafts"] = drafts
    st.session_state.pop("parse_note", None)
    st.success(f"Loaded {len(drafts)} lines. Open Review to confirm each one.")
    st.page_link("pages/2_Review.py", label="Go to Review →")
elif load or load_demo:
    st.warning("Paste at least one line, or tap Load demo slip.")
