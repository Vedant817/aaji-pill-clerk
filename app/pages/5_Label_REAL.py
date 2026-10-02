"""Label Public real-world set: HMR-100 (India). Images never leave this laptop."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pillclerk.ui import apply_theme
from pillclerk.ocr import transcribe_local
from pillclerk.public_data import (
    BD_TARGET_LINES,
    DATASETS,
    HMR_TARGET_PAGES,
    freq_to_dose,
    gold_overlaps_train,
    labelled_count,
    list_images,
    make_gold_row,
    near_duplicates,
    parse_medicine_name,
    refuse_daily_zero_dose,
    set_title,
    upsert_gold,
    work_items,
)
from pillclerk.schema import CheckField, Dose, Food, Form, Kind, MedLine, Unit
from pillclerk.validate import extra_rules

apply_theme()
import streamlit as st
import streamlit.components.v1 as components

FORMS: list[Form] = ["tab", "cap", "syrup", "drops", "inhaler", "injection", "cream", "sachet", "other"]
KINDS: list[Kind] = ["daily", "prn", "taper"]
FOODS: list[Food] = ["before", "after", "with", "empty_stomach", "any"]
UNITS: list[Unit] = ["tab", "cap", "ml", "drop", "puff", "unit", "sachet", "apply"]
CHECKS: list[CheckField] = ["drug", "strength", "dose", "food", "duration_days", "schedule"]
FREQS = ["", "1-0-1", "1+0+1", "1-0-0", "0-0-1", "1-1-1", "OD", "BD", "TDS", "HS", "SOS"]


def _init_state() -> None:
    st.session_state.setdefault("pub_dataset", "hmr100")
    st.session_state.setdefault("pub_i", 0)
    st.session_state.setdefault("line_box", "")
    st.session_state.setdefault("drug_box", "")
    st.session_state.setdefault("strength_box", "")
    st.session_state.setdefault("propose_note", "")


def _apply_medicine_hint(token: str) -> None:
    hint = parse_medicine_name(token)
    if hint["drug"] and not st.session_state.get("drug_box"):
        st.session_state.drug_box = hint["drug"]
    if hint["strength"] and not st.session_state.get("strength_box"):
        st.session_state.strength_box = hint["strength"]
    if hint["form"]:
        st.session_state.form_box = hint["form"]


_init_state()

st.title(set_title("hmr100"))
st.caption(
    "MIRAGE (arXiv 2410.09729): simulated records written by doctors — handwriting and "
    "notation are real, the patients are not. Never family data. Images stay on this "
    "laptop (local Gemma e4b). Illegible means ASK."
)

dataset = st.radio(
    "Set",
    ["hmr100", "bd200"],
    format_func=lambda k: DATASETS[k]["title"],
    horizontal=True,
    key="pub_dataset",
)
meta = DATASETS[dataset]
target = int(meta["target"])
n_labelled = labelled_count(dataset)
images_all = list_images(dataset)
all_pages = st.checkbox("Queue every page (default is first 30 HMR pages ≈ 100 lines)", value=False)
max_pages = None if all_pages else (int(meta["pages"] or 0) or None)
images = images_all if all_pages or not max_pages else images_all[:max_pages]
items = work_items(dataset, max_pages=max_pages)
unlabelled = [it for it in items if not it["labelled"]]

st.markdown(
    f"**{set_title(dataset, n_labelled)}** · target {target} lines"
    + (f" (~{HMR_TARGET_PAGES} pages)" if dataset == "hmr100" else f" (notation stress, ~{BD_TARGET_LINES} lines)")
    + f" · {len(images)} images in `data/public/{dataset}/`"
)
st.progress(min(1.0, n_labelled / target) if target else 0.0)
if n_labelled < target:
    st.info(f"{target - n_labelled} lines left. At n≈100, 95% CIs are about ±8–9 points; only report gaps larger than that.")
else:
    st.success(f"Target reached ({n_labelled} / {target}). Optional: switch to BD-200 for a notation stress test.")

overlap = gold_overlaps_train(dataset)
if overlap:
    st.error(
        f"{len(overlap)} labelled line(s) are near-duplicates of train.jsonl. "
        "Remove them before scoring. Public gold must stay held-out."
    )

components.html(
    """
<script>
const doc = window.parent.document;
doc.addEventListener('keydown', (e) => {
  if (['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)) return;
  if (e.key === 'a' || e.key === 'A') {
    const b = [...doc.querySelectorAll('button')].find(x => x.innerText.includes('Accept'));
    if (b) b.click();
  }
  if (e.key === 'n' || e.key === 'N') {
    const b = [...doc.querySelectorAll('button')].find(x => x.innerText.includes('Next'));
    if (b) b.click();
  }
});
</script>
""",
    height=0,
)

if not images:
    st.warning(
        f"No images in `data/public/{dataset}/`. Run `scripts/download_public.sh` "
        "(or `uv run --with pyarrow --with huggingface_hub python scripts/download_public.py`). "
        "HMR images are CC BY-ND 4.0 and must never be committed."
    )
    st.stop()

if unlabelled:
    default_i = next((i for i, it in enumerate(items) if not it["labelled"]), 0)
else:
    default_i = 0
if st.session_state.pub_i >= len(items):
    st.session_state.pub_i = default_i

i = st.session_state.pub_i % len(items)
item = items[i]
photo: Path = item["image"]
line_no = int(item["line_no"])
hint = item["medicine"]

left, right = st.columns([3, 2])
with left:
    st.caption(
        f"Image {images.index(photo) + 1}/{len(images)} · {photo.name} · line {line_no} "
        f"{'labelled' if item['labelled'] else 'unlabelled'}"
    )
    try:
        st.image(str(photo), width=520)
    except Exception:
        st.write(photo.name)
with right:
    page_lines = [it for it in items if it["image"] == photo]
    st.markdown("**labels.csv medicines** (name only — you still type schedule)")
    for it in page_lines:
        mark = "✓" if it["labelled"] else "○"
        st.write(f"{mark} {it['line_no']}. {it['medicine'] or '(no name in csv)'}")
    if hint:
        parsed = parse_medicine_name(hint)
        st.caption(f"Pre-fill drug from csv: **{parsed['drug'] or hint}**")

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Propose line (local Gemma e4b)"):
        try:
            proposed = transcribe_local(str(photo))
            # Prefer the line that matches this medicine name.
            chosen = ""
            if hint and proposed:
                h = hint.lower()
                chosen = next((p for p in proposed if h.split()[0].lower() in p.lower()), "")
            if not chosen:
                chosen = proposed[line_no - 1] if 0 < line_no <= len(proposed) else "\n".join(proposed)
            st.session_state.line_box = chosen
            st.session_state.propose_note = f"local e4b · {len(proposed)} line(s)"
            _apply_medicine_hint(hint)
        except Exception as exc:
            st.session_state.propose_note = f"Ollama unavailable — type the line. ({exc})"
            _apply_medicine_hint(hint)
        st.rerun()
with c2:
    if st.button("Prefill drug from csv"):
        _apply_medicine_hint(hint)
        st.rerun()
with c3:
    if st.button("Next"):
        st.session_state.pub_i = i + 1
        st.session_state.line_box = ""
        st.session_state.drug_box = ""
        st.session_state.strength_box = ""
        st.rerun()

if st.session_state.get("propose_note"):
    st.caption(st.session_state.propose_note)

if hint and not st.session_state.drug_box:
    _apply_medicine_hint(hint)

line = st.text_area(
    "Transcribed line (correct the e4b text). Gold copies what you see.",
    height=90,
    key="line_box",
)
c1, c2, c3 = st.columns(3)
drug = c1.text_input("Drug", key="drug_box")
strength = c2.text_input("Strength", key="strength_box")
form = c3.selectbox("Form", FORMS, key="form_box")
c1, c2, c3 = st.columns(3)
freq = c1.selectbox("Frequency", FREQS, key="freq_box")
kind = c2.selectbox("Kind", KINDS, key="kind_box")
food = c3.selectbox("Food", FOODS, index=FOODS.index("any"), key="food_box")
duration = st.number_input("Duration days (0=continue / Bangla duration you translate)", min_value=0, value=0, key="dur_box")
m1, m2, m3, m4 = st.columns(4)
morning = m1.number_input("Dose morning", min_value=0.0, max_value=20.0, value=0.0, step=0.5, key="morn_box")
afternoon = m2.number_input("Afternoon", min_value=0.0, max_value=20.0, value=0.0, step=0.5, key="aft_box")
night = m3.number_input("Night", min_value=0.0, max_value=20.0, value=0.0, step=0.5, key="night_box")
unit = m4.selectbox("Unit", UNITS, key="unit_box")
prn = st.number_input("PRN max/day (0=unset)", min_value=0, value=0, key="prn_box")
illegible = st.checkbox("Illegible — ASK (do not guess)", key="ask_box")
flags = st.multiselect(
    "needs_check details",
    CHECKS,
    default=(["drug", "dose", "schedule"] if illegible else []),
    key="flags_box",
)
if illegible and not flags:
    flags = ["drug", "dose", "schedule"]

st.caption("Keyboard: **A** accept · **N** next (when not typing in a field).")

if st.button("Accept", type="primary"):
    if not line.strip():
        st.warning("Propose or type the line first.")
    else:
        dups = near_duplicates(line)
        if dups:
            st.error("This line (or a near-duplicate) is already in train.jsonl. Skip it — public gold must stay held-out.")
            st.code(dups[0][:240])
        else:
            mapped = freq_to_dose(freq) if freq else None
            use_kind: Kind = kind
            dose: Dose | None
            if mapped:
                dose, use_kind = mapped
                if dose is not None:
                    dose = Dose(morning=dose.morning, afternoon=dose.afternoon, night=dose.night, unit=unit)
            elif use_kind == "prn":
                dose = None
            else:
                dose = Dose(morning=morning, afternoon=afternoon, night=night, unit=unit)
            m_amt = 0.0 if dose is None else float(dose.morning)
            a_amt = 0.0 if dose is None else float(dose.afternoon)
            n_amt = 0.0 if dose is None else float(dose.night)
            if refuse_daily_zero_dose(
                kind=use_kind, morning=m_amt, afternoon=a_amt, night=n_amt, ask=bool(illegible)
            ):
                st.error("kind=daily with dose 0-0-0 is refused unless ASK is ticked.")
                st.stop()
            if illegible:
                if use_kind == "daily" and (dose is None or (dose.morning + dose.afternoon + dose.night) == 0):
                    dose = None
                    flags = list(dict.fromkeys([*flags, "dose", "schedule"]))
                if not drug.strip():
                    flags = list(dict.fromkeys([*flags, "drug"]))
            med = extra_rules(
                MedLine(
                    drug=None if illegible and not drug.strip() else (drug.strip() or None),
                    strength=strength.strip() or None,
                    form=form,
                    kind=use_kind,
                    dose=None if use_kind == "prn" else dose,
                    food=food,
                    duration_days=int(duration) or None,
                    prn_max_per_day=int(prn) or None,
                    needs_check=flags,
                    note=line.strip(),
                )
            )
            row = make_gold_row(
                dataset=dataset,
                image_name=photo.name,
                line_no=line_no,
                line=line,
                med=med,
                medicine_hint=hint,
            )
            upsert_gold(dataset, row)
            st.session_state.line_box = ""
            st.session_state.drug_box = ""
            st.session_state.strength_box = ""
            st.session_state.pub_i = i + 1
            st.success(f"Saved {photo.name} line {line_no}. {set_title(dataset, labelled_count(dataset))}")
            st.rerun()
