"""Active meds and change history (SQLite)."""

import streamlit as st

from pillclerk.store import load_meds

st.title("History")
meds = load_meds()
if not meds:
    st.write("Nothing saved yet.")
else:
    for m in meds:
        st.write(f"- **{m.drug}** {m.strength or ''} {m.kind} {m.food} {m.duration_days or 'continue'}")
