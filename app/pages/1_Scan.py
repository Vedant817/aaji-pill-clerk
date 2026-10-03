"""Paste prescription lines (EXTRACT_BACKEND=manual). Photos stay on this machine."""

from pillclerk.ui import apply_theme, stepper
from pillclerk.drafts import drafts_from_text
from pillclerk.review import clear_review_keys

apply_theme()
import streamlit as st

stepper("Scan")
st.title("Scan")
st.caption(
    "Paste one medicine line per row from the slip in front of you. "
    "Photos stay on this laptop. Local OCR is not claimed."
)
photo = st.file_uploader("Prescription photo (local reference while typing)", type=["jpg", "jpeg", "png", "webp"])
if photo is not None:
    st.image(photo, caption="Type what you can read. Use [?] for anything unclear.")

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
    clear_review_keys(st.session_state)
    st.rerun()

if load:
    raw = text.strip()
    if not raw:
        st.warning("Paste at least one line from the prescription.")
    else:
        drafts = drafts_from_text(raw)
        clear_review_keys(st.session_state)
        st.session_state["drafts"] = drafts
        st.session_state["review_i"] = 0
        st.switch_page("pages/2_Review.py")
elif st.session_state.get("drafts"):
    st.info(f"{len(st.session_state['drafts'])} line(s) loaded. Open Review to confirm.")
    st.page_link("pages/2_Review.py", label="Go to Review →")
