"""One line at a time. A human confirms each copy before Chart unlocks."""

from pillclerk.ui import apply_theme, stepper
from pillclerk.config import parser_backend, tinker_parser_ready
from pillclerk.review import (
    WIDGET_PREFIX,
    clear_widget_keys,
    drafts_need_parse,
    med_from_fields,
    n_confirmed,
    next_unconfirmed,
    updated_draft,
)
from pillclerk.schema import Dose, Food, Form, Kind, MedLine, Unit, TaperStep
from pillclerk.validate import schedule_conflicts

apply_theme()
import streamlit as st

stepper("Review")
st.title("Review")
st.caption("Check this line against the slip, then confirm. ASK fields stay red.")

drafts = st.session_state.get("drafts") or []
if not drafts:
    st.warning("No lines yet. Paste them on the Scan page.")
    st.page_link("pages/1_Scan.py", label="← Back to Scan")
    st.stop()


def _push_gold(i: int, gold: MedLine) -> None:
    d = gold.dose or Dose()
    p = f"{WIDGET_PREFIX}{i}_"
    st.session_state[p + "drug"] = gold.drug or ""
    st.session_state[p + "str"] = gold.strength or ""
    st.session_state[p + "form"] = gold.form
    st.session_state[p + "kind"] = gold.kind
    st.session_state[p + "food"] = gold.food
    st.session_state[p + "dur"] = int(gold.duration_days or 0)
    st.session_state[p + "n"] = int(gold.every_n_days)
    st.session_state[p + "am"] = float(d.morning)
    st.session_state[p + "noon"] = float(d.afternoon)
    st.session_state[p + "pm"] = float(d.night)
    st.session_state[p + "unit"] = d.unit
    st.session_state[p + "prn"] = int(gold.prn_max_per_day or 0)


def _parse_all() -> None:
    from pillclerk.infer import get_parser

    try:
        parse = get_parser()
    except Exception as exc:
        st.session_state["parsed_once"] = True
        st.session_state["parse_note"] = f"Parser unavailable ({type(exc).__name__}). Review manually or retry."
        return
    filled = 0
    failed = 0
    next_drafts: list[dict] = []
    for i, draft in enumerate(drafts):
        try:
            pred = parse(draft["line"])
        except Exception:
            # Keep the original ASK draft; never invent a successful parse.
            pred = None
        if pred is None:
            failed += 1
            next_drafts.append(draft)
            continue
        filled += 1
        next_drafts.append({"line": draft["line"], "gold": pred.model_dump(), "confirmed": False})
    clear_widget_keys(st.session_state)
    st.session_state["drafts"] = next_drafts
    st.session_state["parsed_once"] = True
    st.session_state["parse_note"] = f"Parser filled {filled} line(s); {failed} stayed ASK."
    first = next_unconfirmed(next_drafts)
    st.session_state["review_i"] = 0 if first is None else first


backend = parser_backend()
parser_ready = backend == "ollama" or tinker_parser_ready()
if parser_ready and drafts_need_parse(drafts) and not st.session_state.get("parsed_once"):
    with st.spinner("Reading the lines…"):
        _parse_all()
    st.rerun()

if parser_ready:
    if st.button(f"Fill fields from {backend} parser"):
        with st.spinner("Reading the lines…"):
            _parse_all()
        st.rerun()
else:
    st.info("Tinker sampler path is not set yet. Fill fields by hand, then confirm each line.")

if st.session_state.get("parse_note"):
    st.markdown(
        f'<div class="pc-ok">{st.session_state["parse_note"]}</div>',
        unsafe_allow_html=True,
    )

drafts = st.session_state.get("drafts") or drafts
n = len(drafts)
done = n_confirmed(drafts)
st.progress(done / n if n else 0)
m1, m2, m3 = st.columns(3)
m1.metric("Confirmed", f"{done} / {n}")
m2.metric("Left", n - done)
m3.metric("Lines", n)

i = int(st.session_state.get("review_i") or 0)
i = max(0, min(i, n - 1))
st.session_state["review_i"] = i
draft = drafts[i]
gold = MedLine.model_validate(draft["gold"])
p = f"{WIDGET_PREFIX}{i}_"

FOODS: list[Food] = ["before", "after", "with", "empty_stomach", "any"]
FORMS: list[Form] = ["tab", "cap", "syrup", "drops", "inhaler", "injection", "cream", "sachet", "other"]
KINDS: list[Kind] = ["daily", "prn", "taper"]
UNITS: list[Unit] = ["tab", "cap", "ml", "drop", "puff", "unit", "sachet", "apply"]

seed = p + "seeded"
# Streamlit removes widget state when another page is visited. The separate
# seeded flag survives; reseed missing widgets from the saved draft on return.
field_keys = ("drug", "str", "form", "kind", "food", "dur", "n", "am", "noon", "pm", "unit", "prn")
if not st.session_state.get(seed) or any(p + key not in st.session_state for key in field_keys):
    _push_gold(i, gold)
    st.session_state[seed] = True

st.subheader(f"Line {i + 1} of {n}")
st.code(draft["line"])
if draft.get("confirmed"):
    st.markdown('<div class="pc-ok">Confirmed. Change a field and confirm again if the slip disagrees.</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
drug = c1.text_input("Drug", key=p + "drug")
strength = c2.text_input("Strength", key=p + "str")
form = c3.selectbox("Form", FORMS, key=p + "form")
c1, c2, c3, c4 = st.columns(4)
kind = c1.selectbox("Kind", KINDS, key=p + "kind")
food = c2.selectbox("Food", FOODS, key=p + "food")
duration = c3.number_input("Duration days (0 = continue)", min_value=0, key=p + "dur")
every = c4.number_input("Every N days", min_value=1, key=p + "n")
m1, m2, m3, m4 = st.columns(4)
morning = m1.number_input("Morning", min_value=0.0, max_value=20.0, step=0.5, key=p + "am")
afternoon = m2.number_input("Afternoon", min_value=0.0, max_value=20.0, step=0.5, key=p + "noon")
night = m3.number_input("Night", min_value=0.0, max_value=20.0, step=0.5, key=p + "pm")
unit = m4.selectbox("Unit", UNITS, key=p + "unit")
prn_max = st.number_input("PRN max per day (0 = unset)", min_value=0, key=p + "prn")
taper = list(gold.taper)
if kind == "taper":
    import pandas as pd
    rows = st.data_editor(pd.DataFrame([
        {"days": step.days, **step.dose.model_dump()} for step in taper
    ], columns=["days", "morning", "afternoon", "night", "unit"]),
        num_rows="dynamic", key=p + "taper", hide_index=True).to_dict("records")
    try:
        taper = [TaperStep(days=row["days"], dose=Dose(**{k: row[k] for k in ("morning", "afternoon", "night", "unit")})) for row in rows]
    except (ValueError, TypeError, KeyError):
        st.error("Each taper step needs positive days, valid doses, and a unit. Check the prescription.")
        st.stop()

try:
    med = med_from_fields(
        line=draft["line"],
        drug=drug,
        strength=strength,
        form=form,
        kind=kind,
        food=food,
        duration=int(duration),
        every=int(every),
        morning=float(morning),
        afternoon=float(afternoon),
        night=float(night),
        unit=unit,
        prn_max=int(prn_max),
        taper=taper,
    )
except ValueError:
    st.error("These fields do not form a valid prescription copy. Check the dose, unit, and schedule.")
    st.stop()

if med.needs_check:
    st.markdown(
        f'<div class="pc-ask">ASK: {", ".join(med.needs_check)}</div>',
        unsafe_allow_html=True,
    )

# Parser uncertainty must be explicitly resolved by the caregiver.
parser_checks = draft.get("parser_checks", gold.needs_check)
unresolved = []
resolved = []
for check in parser_checks:
    if not st.checkbox(f"I checked {check} against the prescription and resolved the ASK",
                       value=check in draft.get("resolved_checks", []), key=p + "resolve_" + check):
        unresolved.append(check)
    else:
        resolved.append(check)
med = med.model_copy(update={"needs_check": sorted(set(med.needs_check + unresolved))})
drafts[i] = updated_draft({**draft, "parser_checks": parser_checks, "resolved_checks": resolved}, med)
st.session_state["drafts"] = drafts
done = n_confirmed(drafts)

nav1, nav2, nav3 = st.columns([1, 2, 1])
with nav1:
    if st.button("Back", disabled=i == 0):
        st.session_state["review_i"] = i - 1
        st.rerun()
with nav2:
    if st.button("Confirm this line", type="primary", disabled=bool(med.needs_check)):
        drafts[i] = {**drafts[i], "confirmed": True}
        st.session_state["drafts"] = drafts
        nxt = next_unconfirmed(drafts, after=i)
        if nxt is None:
            st.switch_page("pages/3_Chart.py")
            st.stop()
        st.session_state["review_i"] = nxt
        st.rerun()
with nav3:
    if st.button("Next", disabled=i >= n - 1):
        st.session_state["review_i"] = i + 1
        st.rerun()

conflicts = schedule_conflicts([MedLine.model_validate(d["gold"]) for d in drafts])
if conflicts:
    bits = []
    for name, a, b in conflicts:
        bits.append(
            f"{name}: {a.kind}/{a.dose.model_dump() if a.dose else None} vs "
            f"{b.kind}/{b.dose.model_dump() if b.dose else None}"
        )
    st.markdown(
        '<div class="pc-ask">Same drug, different copy. Clerk keeps both; a human picks. '
        + " · ".join(bits)
        + "</div>",
        unsafe_allow_html=True,
    )

if done == n and n:
    st.markdown(
        '<div class="pc-ok">Every line is confirmed. Open Chart to print and download .ics.</div>',
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Chart.py", label="Go to Chart →")
else:
    st.warning("Chart stays locked until every line is confirmed and has no ASK fields.")
