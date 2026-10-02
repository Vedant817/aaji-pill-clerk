"""Active meds and change history (SQLite)."""

from pillclerk.ui import apply_theme
from pillclerk.store import load_meds

apply_theme()
import streamlit as st

st.title("History")
st.caption("Saved on this laptop only. Real prescriptions are never uploaded.")
meds = load_meds()
if not meds:
    st.info("Nothing saved yet. Confirm a chart, then tap Save to local history.")
else:
    for m in meds:
        dose = ""
        if m.dose:
            dose = f"{m.dose.morning:g}-{m.dose.afternoon:g}-{m.dose.night:g}"
        st.markdown(
            f"""
<div class="pc-card">
  <b>{m.drug or "ASK"}</b> {m.strength or ""}
  <div class="pc-lede">{m.kind} · {dose} · {m.food} · {m.duration_days or "continue"} days</div>
</div>
""",
            unsafe_allow_html=True,
        )
