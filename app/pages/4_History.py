"""Active meds and change history (SQLite)."""

from pillclerk.ui import apply_theme, FOOD_NAMES, SCHEDULE_NAMES, ASK_NAMES
from html import escape
from pillclerk.store import load_meds, load_history
from pillclerk.provenance import context_text

apply_theme()
import streamlit as st

st.title("History")
st.caption("Saved on this laptop. Photos stay local; text parsing may use the configured hosted service.")
meds = load_meds()
if not meds:
    st.info("Nothing saved yet. Confirm a chart, then tap Save to local history.")
else:
    st.subheader("Active saved copy")
    for m in meds:
        dose = ""
        if m.dose:
            dose = f"{m.dose.morning:g}-{m.dose.afternoon:g}-{m.dose.night:g} {m.dose.unit}"
        schedule = (f"Scheduled · every {m.every_n_days} day(s)" if m.kind == "daily"
                    else "When needed (PRN)" if m.kind == "prn" else "Taper — follow recorded steps")
        duration = f"{m.duration_days} days" if m.duration_days is not None else "No end date recorded — check the prescription"
        st.markdown(
            f"""
<div class="pc-card">
  <b>{escape(m.drug or "ASK")}</b> {escape(m.strength or "")}
  <div class="pc-lede">{schedule} · {dose} · {FOOD_NAMES[m.food]} · {duration}</div>
</div>
""",
            unsafe_allow_html=True,
        )
        if m.note:
            st.text(m.note)
        if m.kind == "prn":
            st.text(f"Recorded PRN maximum: {m.prn_max_per_day} per day" if m.prn_max_per_day is not None
                    else "PRN maximum not recorded — check the prescription")
        if m.taper:
            st.table([{"Step": i + 1, "Days": step.days,
                       "Morning": step.dose.morning, "Afternoon": step.dose.afternoon,
                       "Night": step.dose.night, "Unit": step.dose.unit}
                      for i, step in enumerate(m.taper)])

history = load_history()
if history:
    st.subheader("Saved copies")
    st.caption("Newest first, up to 100 copies. Compare the recorded fields with the prescription. Earlier copies are for reference; this page does not change the active chart.")
    for revision in history:
        with st.expander(f"Copy {revision['id']} · {revision['saved_at']}"):
            if revision.get("context"):
                st.text(context_text(revision["context"]))
            if revision["note"]:
                st.text(revision["note"])
            st.table([{
                "Medicine": med.drug or "ASK",
                "Strength": med.strength or "Not recorded",
                "Form": med.form,
                "Schedule": SCHEDULE_NAMES[med.kind],
                "Morning": med.dose.morning if med.dose else "—",
                "Afternoon": med.dose.afternoon if med.dose else "—",
                "Night": med.dose.night if med.dose else "—",
                "Unit": med.dose.unit if med.dose else "—",
                "Food": FOOD_NAMES[med.food],
                "Days": med.duration_days if med.duration_days is not None else "No end date recorded",
                "Every N days": med.every_n_days,
                "PRN maximum/day": med.prn_max_per_day or "Not recorded",
                "ASK": ", ".join(ASK_NAMES[field] for field in med.needs_check) or "—",
                "Written instructions": med.note or "Not recorded",
            } for med in revision["meds"]])
            for med in revision["meds"]:
                if med.taper:
                    st.text(f"{med.drug or 'ASK'}: recorded taper steps")
                    st.table([{"Step": i + 1, "Days": step.days,
                               "Morning": step.dose.morning, "Afternoon": step.dose.afternoon,
                               "Night": step.dose.night, "Unit": step.dose.unit}
                              for i, step in enumerate(med.taper)])
