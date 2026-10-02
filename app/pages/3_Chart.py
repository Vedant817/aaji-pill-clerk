"""Fridge chart, .ics reminders, refill dates."""

from datetime import date

import streamlit as st
import streamlit.components.v1 as components

from pillclerk.chart import chart_html
from pillclerk.ics import to_ics
from pillclerk.schedule import expand, prn_meds, refill_date
from pillclerk.schema import MedLine
from pillclerk.store import save_meds
from pillclerk.validate import all_confirmed

st.title("Chart")

drafts = st.session_state.get("drafts") or []
meds = [MedLine.model_validate(d["gold"]) for d in drafts]
if not drafts:
    st.warning("No confirmed lines yet.")
    st.stop()
if not all(d.get("confirmed") for d in drafts) or not all_confirmed(meds):
    st.error("A human must confirm every line on Review first. ASK cells block the chart.")
    st.stop()

start = st.date_input("Start date", value=date.today())
lang = st.selectbox("Chart language", ["mr", "hi", "en"], index=0)
stock = st.number_input("Tablets in stock (for refill date, first daily med)", min_value=0, value=30)

plan = expand(meds, start)
html = chart_html(plan, lang=lang, footer="Clerk copy of the prescription. Not medical advice.", prn=prn_meds(meds))
components.html(html, height=420, scrolling=True)
st.download_button("Download fridge chart.html", html.encode("utf-8"), "fridge-chart.html", "text/html")
st.download_button("Download reminders.ics", to_ics(plan), "pillclerk.ics", "text/calendar")

for m in meds:
    rd = refill_date(m, start, float(stock))
    if rd:
        st.write(f"Refill {m.drug}: {rd.isoformat()}")

if st.button("Save to local history"):
    save_meds(meds, note="confirmed")
    st.success("Saved on this laptop (SQLite).")
