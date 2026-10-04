"""Blind, local human annotation. No parser calls or automatic gold suggestions."""
import json

import streamlit as st

from pillclerk.acceptance import (DEFAULT_DIR, latest_annotations, load_manifest,
    mark_page_complete, page_path, save_annotation)
from pillclerk.schema import MedLine
from pillclerk.schema import Form, Food, Kind, Unit, CheckField
from pillclerk.annotation_form import manual_gold
from typing import get_args
from pillclerk.ui import apply_theme

apply_theme()
st.title("Independent prescription labels")
st.caption("Read only the original photo. Two different people label every medicine line separately. No model suggestions are used.")
if not (DEFAULT_DIR / "manifest.json").is_file():
    st.info("Prepare the reserved page queue first: python -m scripts.prepare_acceptance")
    st.stop()
manifest = load_manifest()
annotator = st.text_input("Annotator ID (use the same ID throughout your round)")
round_name = st.selectbox("Annotation round", ["A", "B"])
image = st.selectbox("Reserved page", [p["image"] for p in manifest["pages"]])
try:
    st.image(str(page_path(image)), caption="Original public HMR page; simulated record, not family data.")
except (ValueError, OSError) as exc:
    st.error(str(exc))
    st.stop()
own = [r for r in latest_annotations().values() if r["round"] == round_name and r["image"] == image and r["annotator"] == annotator.strip()]
st.caption(f"This round has {len(own)} saved medicine lines for the page. Other-round answers are hidden.")
line_no = st.number_input("Medicine line number (top to bottom)", min_value=1, step=1)
prefix = f"accept_{annotator.strip()}_{round_name}_{image}_{line_no}"
line = st.text_area("Exact medicine transcription. Use [?] for unreadable text.", key=prefix + "_line")
mode = st.radio("Enter copied fields", ["Form", "Advanced JSON"], key=prefix + "_mode")
with st.expander("Gold JSON field schema"):
    st.json(MedLine.model_json_schema())
blob = None
if mode == "Advanced JSON":
    gold = st.text_area("Gold JSON: enter every field explicitly; missing values are null or ASK.", key=prefix + "_json")
else:
    st.caption("Fields start blank. Copy only the original image; no model suggestions are shown. Use zero only where the source has no dose in that slot.")
    drug = st.text_input("Medicine name (blank if unreadable)", key=prefix + "_drug")
    strength = st.text_input("Written strength (blank if absent)", key=prefix + "_strength")
    form = st.selectbox("Written form", get_args(Form), index=None, key=prefix + "_form")
    kind = st.selectbox("Schedule kind", get_args(Kind), index=None, key=prefix + "_kind")
    food = st.selectbox("Food instruction (any if not written)", get_args(Food), index=None, key=prefix + "_food")
    duration = st.number_input("Written duration in days (blank if unclear)", min_value=1, value=None, step=1, key=prefix + "_duration")
    interval = st.number_input("Every N days (1 for a written daily schedule)", min_value=1, max_value=30, value=None, step=1, key=prefix + "_interval")
    checks = st.multiselect("Fields requiring ASK", get_args(CheckField), key=prefix + "_checks")
    def dose_fields(key):
        amounts = {slot: st.number_input(slot.capitalize() + " amount", min_value=0.0, max_value=20.0, value=None, step=0.5, key=key + slot) for slot in ("morning", "afternoon", "night")}
        amounts["unit"] = st.selectbox("Written administration unit", get_args(Unit), index=None, key=key + "unit")
        return amounts
    dose, taper, prn_limit = None, [], None
    if kind == "daily" and not st.checkbox("Fixed dose is unclear (ASK)", key=prefix + "_unknown_dose"):
        dose = dose_fields(prefix + "_dose_")
    if kind == "taper":
        count = st.number_input("Number of written taper steps", min_value=1, max_value=20, value=None, step=1, key=prefix + "_steps")
        for n in range(count or 0):
            st.markdown(f"Step {n + 1}")
            days = st.number_input("Step days", min_value=1, max_value=90, value=None, step=1, key=f"{prefix}_step{n}_days")
            taper.append({"days": days, "dose": dose_fields(f"{prefix}_step{n}_dose_")})
    if kind == "prn":
        prn_limit = st.number_input("Written maximum per day (blank if absent)", min_value=1, value=None, step=1, key=prefix + "_prn")
if st.button("Save my annotation"):
    try:
        blob = json.loads(gold) if mode == "Advanced JSON" else manual_gold(drug=drug, strength=strength,
            form=form, kind=kind, food=food, duration=duration, interval=interval, dose=dose,
            taper=taper, prn_limit=prn_limit, checks=checks)
        save_annotation(image=image, line_no=int(line_no), round_name=round_name,
                        annotator=annotator, line=line, gold=blob)
        st.success("Saved locally. Gold is not finalized until both rounds agree.")
    except (ValueError, TypeError) as exc:
        st.error(str(exc))
checked = st.checkbox("I entered every visible medicine line on this page, including unclear lines as ASK.")
if st.button("Mark my page complete", disabled=not checked):
    try:
        mark_page_complete(image, round_name, annotator)
        st.success("Page completion recorded for this annotation round.")
    except ValueError as exc:
        st.error(str(exc))

st.caption("To revise a saved line, re-enter it under the same ID, round, page and line number. Revisions invalidate previous completion; mark the page complete again after checking it.")
