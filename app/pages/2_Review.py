"""Line-by-line review. Red = needs_check / ASK. Nothing proceeds until confirmed."""

import streamlit as st

from pillclerk.config import tinker_parser_ready
from pillclerk.schema import CheckField, Dose, Food, Form, Kind, MedLine, Unit
from pillclerk.validate import extra_rules

st.title("Review")
st.caption("A human must confirm every line. ASK fields stay red until you fill them.")

drafts = st.session_state.get("drafts") or []
if not drafts:
    st.warning("No lines yet. Load them on the Scan page.")
    st.stop()


def _push_gold(i: int, gold: MedLine) -> None:
    d = gold.dose or Dose()
    st.session_state[f"drug{i}"] = gold.drug or ""
    st.session_state[f"str{i}"] = gold.strength or ""
    st.session_state[f"form{i}"] = gold.form
    st.session_state[f"kind{i}"] = gold.kind
    st.session_state[f"food{i}"] = gold.food
    st.session_state[f"dur{i}"] = int(gold.duration_days or 0)
    st.session_state[f"n{i}"] = int(gold.every_n_days)
    st.session_state[f"am{i}"] = float(d.morning)
    st.session_state[f"noon{i}"] = float(d.afternoon)
    st.session_state[f"pm{i}"] = float(d.night)
    st.session_state[f"unit{i}"] = d.unit
    st.session_state[f"prn{i}"] = int(gold.prn_max_per_day or 0)
    st.session_state[f"ok{i}"] = False


if tinker_parser_ready():
    if st.button("Fill fields from Tinker parser"):
        from pillclerk.infer import get_parser

        parse = get_parser()
        filled = 0
        failed = 0
        next_drafts: list[dict] = []
        for i, draft in enumerate(drafts):
            pred = parse(draft["line"])
            if pred is None:
                failed += 1
                next_drafts.append(draft)
                continue
            filled += 1
            _push_gold(i, pred)
            next_drafts.append(
                {"line": draft["line"], "gold": pred.model_dump(), "confirmed": False}
            )
        st.session_state["drafts"] = next_drafts
        st.session_state["parse_note"] = f"Parser filled {filled} line(s); {failed} stayed ASK."
        st.rerun()
else:
    st.info("Tinker sampler path is not set yet. Fill fields by hand, then confirm each line.")

if st.session_state.get("parse_note"):
    st.caption(st.session_state["parse_note"])

FOODS: list[Food] = ["before", "after", "with", "empty_stomach", "any"]
FORMS: list[Form] = ["tab", "cap", "syrup", "drops", "inhaler", "injection", "cream", "sachet", "other"]
KINDS: list[Kind] = ["daily", "prn", "taper"]
UNITS: list[Unit] = ["tab", "cap", "ml", "drop", "puff", "unit", "sachet", "apply"]

updated: list[dict] = []
for i, draft in enumerate(drafts):
    gold = MedLine.model_validate(draft["gold"])
    with st.expander(f"{i + 1}. {draft['line']}", expanded=True):
        st.code(draft["line"])
        if gold.needs_check:
            st.error("ASK: " + ", ".join(gold.needs_check))
        c1, c2, c3 = st.columns(3)
        drug = c1.text_input("Drug", gold.drug or "", key=f"drug{i}")
        strength = c2.text_input("Strength", gold.strength or "", key=f"str{i}")
        form = c3.selectbox("Form", FORMS, index=FORMS.index(gold.form), key=f"form{i}")
        c1, c2, c3, c4 = st.columns(4)
        kind = c1.selectbox("Kind", KINDS, index=KINDS.index(gold.kind), key=f"kind{i}")
        food = c2.selectbox("Food", FOODS, index=FOODS.index(gold.food), key=f"food{i}")
        duration = c3.number_input(
            "Duration days (0 = continue)",
            min_value=0,
            value=int(gold.duration_days or 0),
            key=f"dur{i}",
        )
        every = c4.number_input("Every N days", min_value=1, value=int(gold.every_n_days), key=f"n{i}")
        d = gold.dose or Dose()
        m1, m2, m3, m4 = st.columns(4)
        morning = m1.number_input("Morning", min_value=0.0, max_value=20.0, value=float(d.morning), step=0.5, key=f"am{i}")
        afternoon = m2.number_input("Afternoon", min_value=0.0, max_value=20.0, value=float(d.afternoon), step=0.5, key=f"noon{i}")
        night = m3.number_input("Night", min_value=0.0, max_value=20.0, value=float(d.night), step=0.5, key=f"pm{i}")
        unit = m4.selectbox("Unit", UNITS, index=UNITS.index(d.unit), key=f"unit{i}")
        prn_max = st.number_input(
            "PRN max per day (0 = unset)",
            min_value=0,
            value=int(gold.prn_max_per_day or 0),
            key=f"prn{i}",
        )
        confirmed = st.checkbox("I confirm this line copies the prescription", value=draft.get("confirmed", False), key=f"ok{i}")
        checks: list[CheckField] = []
        if not drug.strip():
            checks.append("drug")
        dose = None if kind == "prn" else Dose(morning=morning, afternoon=afternoon, night=night, unit=unit)
        if kind == "daily" and dose and (dose.morning + dose.afternoon + dose.night) == 0:
            checks.append("dose")
        taper = list(gold.taper) if kind == "taper" else []
        if kind == "taper" and not taper:
            kind = "daily"
            checks.append("schedule")
        med = extra_rules(
            MedLine(
                drug=drug.strip() or None,
                strength=strength.strip() or None,
                form=form,
                kind=kind,
                dose=dose,
                every_n_days=int(every),
                taper=taper,
                food=food,
                duration_days=int(duration) or None,
                prn_max_per_day=int(prn_max) or None,
                needs_check=checks,
                note=draft["line"],
            )
        )
        if not confirmed:
            st.caption("Not confirmed yet.")
        updated.append({"line": draft["line"], "gold": med.model_dump(), "confirmed": confirmed and not med.needs_check})

st.session_state["drafts"] = updated
if updated and all(d["confirmed"] for d in updated):
    st.success("Every line is confirmed. Open Chart to print and download .ics.")
else:
    st.warning("Chart stays locked until every line is confirmed and has no ASK fields.")
