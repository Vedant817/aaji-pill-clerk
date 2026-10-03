"""Paste prescription lines (EXTRACT_BACKEND=manual). Photos stay on this machine."""

from pillclerk.ui import apply_theme, stepper
from pillclerk.drafts import drafts_from_text

apply_theme()
import streamlit as st

stepper("Scan")
st.title("Scan")
st.caption(
    "Paste one medicine line per row from the slip in front of you. "
    "Photos stay on this laptop. Local OCR is not claimed."
)

text = st.text_area(
    "Prescription lines",
    height=240,
    placeholder="Paste one medicine line per row",
)
c0, c1 = st.columns([1, 1])
with c0:
    load = st.button("Load lines", type="primary")
with c1:
    clear = st.button("Clear")

if clear:
    st.session_state.pop("drafts", None)
    st.session_state.pop("parse_note", None)
    st.rerun()

if load:
    raw = text.strip()
    if not raw:
        st.warning("Paste at least one line from the prescription.")
    else:
        drafts = drafts_from_text(raw)
        st.session_state["drafts"] = drafts
        st.session_state.pop("parse_note", None)
        st.success(f"Loaded {len(drafts)} lines. Open Review to confirm each one.")
        st.page_link("pages/2_Review.py", label="Go to Review →")
elif st.session_state.get("drafts"):
    st.info(f"{len(st.session_state['drafts'])} line(s) loaded. Open Review to confirm.")
    st.page_link("pages/2_Review.py", label="Go to Review →")
