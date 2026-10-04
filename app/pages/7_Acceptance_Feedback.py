"""Record actual caregiver or phone observations locally; no default successes."""
import streamlit as st
from pillclerk.feedback import DEFAULT_PATH, Observation, save_observation, shareable_summary
from pillclerk.ui import apply_theme

apply_theme()
st.title("Caregiver and phone checks")
st.caption("Record what actually happened. This page does not verify identity or replace independent labels. Avoid patient names, medicine text and account details.")
with st.form("acceptance_observation"):
    observer = st.text_input("Observer ID (use a pseudonym)")
    source = st.selectbox("Who observed it?", ["human_self_report", "human_observer", "agent_test"], index=None)
    context = st.selectbox("Input used", ["synthetic_input", "real_prescription"], index=None)
    device = st.text_input("Device model and OS version")
    calendar = st.text_input("Calendar app and version")
    zone = st.text_input("Device/calendar timezone")
    labels = {"workflow": "Completed Scan → Review → Chart", "ask_understood": "Caregiver explained ASK", "source_compared": "Caregiver compared each line with the source", "ics_import": "Imported the actual exported ICS", "recurrence": "Checked recurrence end dates and times", "notification": "Observed a phone notification", "sound": "Heard the reminder sound"}
    statuses = {field: st.selectbox(label, ["not_checked", "pass", "fail"], key="feedback_" + field) for field, label in labels.items()}
    words = st.text_area("Actual feedback and corrections (optional)")
    attested = st.checkbox("This records an actual observation from the stated source, not a simulated success")
    consent = st.selectbox("Permission to share aggregate results", ["Keep private", "Permission given"], index=None)
    submitted = st.form_submit_button("Save observation locally")
if submitted:
    try:
        if consent is None:
            raise ValueError("Record whether sharing permission was given")
        record = Observation(observer_id=observer, source=source, context=context,
            actual_observation_attested=attested, sharing_allowed=consent == "Permission given",
            device=device, calendar_app=calendar, timezone=zone, feedback=words, **statuses)
        save_observation(record)
        st.success("Saved in gitignored local storage. No feedback was published or sent to a model.")
    except (ValueError, TypeError) as exc:
        st.error(str(exc))
st.caption("Only explicitly consented aggregate results can be exported; private words and identities are excluded.")
if DEFAULT_PATH.is_file():
    import json
    st.download_button("Download consented aggregate checks", json.dumps(shareable_summary(), indent=2), "acceptance-checks.json", "application/json")
