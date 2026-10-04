"""Active meds and change history (SQLite)."""

from pillclerk.ui import apply_theme
from html import escape
from pillclerk.store import load_meds, load_history

apply_theme()
import streamlit as st

st.title("History")
st.caption("Saved on this laptop. Photos stay local; text parsing may use the configured hosted service.")
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
  <b>{escape(m.drug or "ASK")}</b> {escape(m.strength or "")}
  <div class="pc-lede">{m.kind} · {dose} · {m.food} · {m.duration_days or "continue"} days</div>
</div>
""",
            unsafe_allow_html=True,
        )

history = load_history()
if history:
    st.subheader("Saved copies")
    st.caption("Newest first, up to 100 copies. Compare the recorded fields with the prescription. Earlier copies are for reference; this page does not change the active chart.")
    for revision in history:
        with st.expander(f"Copy {revision['id']} · {revision['saved_at']}"):
            if revision["note"]:
                st.text(revision["note"])
            st.table([{
                "Medicine": med.drug or "ASK",
                "Strength": med.strength or "Not recorded",
                "Form": med.form,
                "Schedule": med.kind,
                "Morning": med.dose.morning if med.dose else "—",
                "Afternoon": med.dose.afternoon if med.dose else "—",
                "Night": med.dose.night if med.dose else "—",
                "Unit": med.dose.unit if med.dose else "—",
                "Food": med.food,
                "Days": med.duration_days if med.duration_days is not None else "Not recorded / continue",
                "Every N days": med.every_n_days,
                "PRN maximum/day": med.prn_max_per_day or "Not recorded",
                "ASK": ", ".join(med.needs_check) or "—",
            } for med in revision["meds"]])
            for med in revision["meds"]:
                if med.taper:
                    st.text(f"{med.drug or 'ASK'}: recorded taper steps")
                    st.table([{"Step": i + 1, "Days": step.days,
                               "Morning": step.dose.morning, "Afternoon": step.dose.afternoon,
                               "Night": step.dose.night, "Unit": step.dose.unit}
                              for i, step in enumerate(med.taper)])
