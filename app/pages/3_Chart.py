"""Fridge chart, .ics reminders, refill dates."""

from datetime import date

from pillclerk.ui import apply_theme, stepper
from pillclerk.chart import chart_html, LABELS
from pillclerk.ics import to_ics
from pillclerk.schedule import SLOTS, expand, prn_meds, refill_date
from pillclerk.schema import MedLine
from pillclerk.review import export_blockers
from pillclerk.store import save_meds
from pillclerk.validate import all_confirmed, schedule_conflicts
from pillclerk.provenance import CopyContext

apply_theme()
import streamlit as st
import streamlit.components.v1 as components

stepper("Chart")
st.title("Chart")

drafts = st.session_state.get("drafts") or []
meds = [MedLine.model_validate(d["gold"]) for d in drafts]
if not drafts:
    st.warning("No confirmed lines yet.")
    st.page_link("pages/1_Scan.py", label="← Start at Scan")
    st.stop()
if not all(d.get("confirmed") for d in drafts) or not all_confirmed(meds):
    st.markdown(
        '<div class="pc-ask">A human must confirm every line on Review first. ASK cells block the chart.</div>',
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Review.py", label="← Back to Review")
    st.stop()

conflicts = schedule_conflicts(meds)
if conflicts:
    st.markdown(
        '<div class="pc-ask">Two lines name the same drug with different dose or kind. '
        "The clerk copied both. Ask the doctor or pharmacist which one to follow.</div>",
        unsafe_allow_html=True,
    )
    st.stop()

for blocker in export_blockers(drafts):
    st.error(blocker)
    st.stop()

c1, c2, c3 = st.columns(3)
start = c1.date_input("Start date", value=date.today())
lang = c2.selectbox("Chart language", ["mr", "hi", "en"], index=0,
                    format_func=lambda value: {"mr": "मराठी (Marathi)", "hi": "हिन्दी (Hindi)", "en": "English"}[value])
st.caption("Set caregiver reminder times. Check these against the prescription before exporting.")
time_cols = st.columns(3)
slot_times = {slot: col.time_input(slot.capitalize(), value=default)
              for col, (slot, default) in zip(time_cols, SLOTS.items())}

with st.expander("Source and check record", expanded=True):
    source_reference = st.text_input("Prescription reference (avoid patient names)", key="pc_chart_source")
    prescription_date = st.date_input("Prescription date (leave blank if not recorded)", value=None, key="pc_chart_source_date")
    checker = st.text_input("Checked by (initials or a pseudonym)", key="pc_chart_checker")
    checked_on = st.date_input("Checked on", value=date.today(), key="pc_chart_checked_on")
context = None
try:
    context = CopyContext(source_reference=source_reference, prescription_date=prescription_date,
                          checker=checker, checked_on=checked_on, start_date=start,
                          slot_times=slot_times,
                          ongoing_confirmed=[bool(d.get("ongoing_confirmed")) for d in drafts]).model_dump(mode="json")
except ValueError:
    st.warning("Enter a prescription reference, checker initials and check date before downloading or saving this copy.")

plan = expand(meds, start)
html = chart_html(
    plan,
    lang=lang,
    footer=LABELS[lang]["footer"],
    prn=prn_meds(meds),
    slot_times=slot_times,
    context=context,
)
components.html(html, height=460, scrolling=True)
d1, d2, d3 = st.columns(3)
history_note = st.text_input("History note (optional)", help="Record the source or reason for this saved copy. Avoid names and contact details.")
with d1:
    st.download_button("Download fridge chart.html", html.encode("utf-8"), "fridge-chart.html", "text/html", disabled=context is None)
with d2:
    st.download_button("Download reminders.ics", to_ics(plan, slot_times=slot_times, context=context), "pillclerk.ics", "text/calendar", disabled=context is None)
with d3:
    if st.button("Save to local history", disabled=context is None):
        save_meds(meds, note=history_note.strip(), context=context)
        st.success("Saved on this laptop (SQLite).")
st.caption("To print: download the HTML chart, open it in your browser, then choose Print and landscape orientation.")

with st.expander("Add reminders to Google Calendar on Android"):
    st.write("On a computer, open Google Calendar with the same account used on the phone. In Settings → Import & export, select the downloaded ICS and choose the destination calendar. Import once, then enable that calendar and sync on Android.")
    st.write("Check the local reminder times, quantities and final recurrence dates against this chart. Check each event's notification setting and Android's Calendar notification permission. An exported alarm does not prove the phone will display or sound a reminder.")
    st.link_button("Google Calendar import instructions", "https://support.google.com/calendar/answer/37118?co=GENIE.Platform%3DDesktop&hl=en")

st.subheader("Stock and refill dates")
for i, m in enumerate(meds):
    if m.kind != "daily" or not m.dose:
        continue
    stock = st.number_input(f"{m.drug}: stock remaining ({m.dose.unit})", min_value=0.0,
                            value=None, key=f"stock_{i}_{m.model_dump_json()}")
    if stock is not None:
        rd = refill_date(m, start, float(stock))
        if rd:
            st.write(f"Stock runs out for **{m.drug}** on {rd.isoformat()}.")
        else:
            st.caption(f"{m.drug}: entered stock covers the prescribed course.")
