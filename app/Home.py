"""Streamlit home. Safety first. Pages land after the MVP parser works."""

import streamlit as st

st.set_page_config(page_title="Aaji's Pill Clerk", layout="wide")
st.title("Aaji's Pill Clerk")
st.markdown(
    """
**It's a clerk, not a clinician.** This tool copies what the doctor wrote
into a schedule. It never suggests or changes a dose. Unclear fields show
as **ASK**. A human confirms every line before the fridge chart or `.ics`
is produced.

This is a personal family tool built in a weekend. It is **not** a medical
device and is not validated for clinical use.
"""
)
st.info("MVP in progress: photo → extracted lines → human confirm → parser → schedule → chart + .ics")
