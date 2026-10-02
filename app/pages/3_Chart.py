"""Fridge chart, .ics reminders, refill dates."""

from datetime import date

from pillclerk.ui import apply_theme, stepper
from pillclerk.chart import chart_html
from pillclerk.ics import to_ics
from pillclerk.schedule import expand, prn_meds, refill_date
from pillclerk.schema import MedLine
from pillclerk.store import save_meds
from pillclerk.validate import all_confirmed

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

c1, c2, c3 = st.columns(3)
start = c1.date_input("Start date", value=date.today())
lang = c2.selectbox("Chart language", ["mr", "hi", "en"], index=0)
stock = c3.number_input("Tablets in stock (first daily med)", min_value=0, value=30)

plan = expand(meds, start)
html = chart_html(
    plan,
    lang=lang,
    footer="Clerk copy of the prescription. Not medical advice. If anything looks different, ask the doctor or pharmacist.",
    prn=prn_meds(meds),
)
components.html(html, height=460, scrolling=True)
d1, d2, d3 = st.columns(3)
with d1:
    st.download_button("Download fridge chart.html", html.encode("utf-8"), "fridge-chart.html", "text/html")
with d2:
    st.download_button("Download reminders.ics", to_ics(plan), "pillclerk.ics", "text/calendar")
with d3:
    if st.button("Save to local history"):
        save_meds(meds, note="confirmed")
        st.success("Saved on this laptop (SQLite).")

for m in meds:
    rd = refill_date(m, start, float(stock))
    if rd:
        st.write(f"Refill **{m.drug}**: {rd.isoformat()}")
