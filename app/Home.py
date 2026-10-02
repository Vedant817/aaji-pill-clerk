"""Streamlit home. Safety first."""

from pillclerk.ui import apply_theme
from pillclerk.config import extract_backend, llm_backend, parser_backend, tinker_parser_ready

apply_theme()

import streamlit as st

st.markdown(
    """
<div class="pc-hero">
  <p class="pc-kicker">Family clerk · not a clinician</p>
  <h1>Aaji's Pill Clerk</h1>
  <p class="pc-lede">
    Copy what the doctor wrote into a confirmed schedule, a big-font fridge chart,
    and phone reminders. Unclear fields show as <b>ASK</b> in red. A human confirms
    every line before anything is printed.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="pc-grid">
  <div class="pc-tile"><b>1. Scan</b><br/>Paste one medicine line per row. Photos stay on this laptop.</div>
  <div class="pc-tile"><b>2. Review</b><br/>The clerk fills JSON. You fix ASK cells and confirm each line.</div>
  <div class="pc-tile"><b>3. Chart</b><br/>Print the fridge chart and download <code>.ics</code> reminders.</div>
</div>
""",
    unsafe_allow_html=True,
)

ready = parser_backend() == "tinker" and tinker_parser_ready()
st.markdown(
    f'<span class="pc-badge">{"Tinker parser ready" if ready else "Parser path empty"}</span>',
    unsafe_allow_html=True,
)
st.caption(
    f"LLM_BACKEND={llm_backend()} · EXTRACT_BACKEND={extract_backend()} · PARSER_BACKEND={parser_backend()}"
)

st.page_link("pages/1_Scan.py", label="Start with Scan →")

st.info(
    "This is a personal family tool built in a weekend. It is not a medical device "
    "and is not validated for clinical use. It never suggests or changes a dose."
)
