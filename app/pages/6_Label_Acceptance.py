"""Blind, local human annotation. No parser calls or automatic gold suggestions."""
import json

import streamlit as st

from pillclerk.acceptance import (DEFAULT_DIR, latest_annotations, load_manifest,
    mark_page_complete, page_path, save_annotation)
from pillclerk.schema import MedLine
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
own = [r for r in latest_annotations().values() if r["round"] == round_name and r["image"] == image]
st.caption(f"This round has {len(own)} saved medicine lines for the page. Other-round answers are hidden.")
line_no = st.number_input("Medicine line number (top to bottom)", min_value=1, step=1)
line = st.text_area("Exact medicine transcription. Use [?] for unreadable text.", key=f"accept_line_{round_name}_{image}_{line_no}")
with st.expander("Gold JSON field schema"):
    st.json(MedLine.model_json_schema())
gold = st.text_area("Gold JSON: enter every field explicitly; missing values are null or ASK.", key=f"accept_gold_{round_name}_{image}_{line_no}")
if st.button("Save my annotation"):
    try:
        save_annotation(image=image, line_no=int(line_no), round_name=round_name,
                        annotator=annotator, line=line, gold=json.loads(gold))
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
