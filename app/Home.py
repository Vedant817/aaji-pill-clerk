"""Streamlit home. Safety first."""

import streamlit as st

from pillclerk.config import extract_backend, llm_backend, parser_backend, tinker_parser_ready

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
st.caption(
    f"LLM_BACKEND={llm_backend()} · EXTRACT_BACKEND={extract_backend()} · PARSER_BACKEND={parser_backend()}"
)
st.info("MVP: paste lines → review (ASK in red) → fridge chart + .ics")
if parser_backend() == "tinker" and tinker_parser_ready():
    st.caption("Tinker parser is ready. Review can fill fields from the hosted LoRA.")
elif parser_backend() == "tinker":
    st.caption("Tinker parser path is empty until SFT writes train/checkpoint_v1.json.")
