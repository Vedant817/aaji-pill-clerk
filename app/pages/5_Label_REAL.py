"""Label photographed family lines. Photos stay on this laptop."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pillclerk.ui import apply_theme
from eval.family_real import REAL
from pillclerk.ocr import transcribe_local
from pillclerk.schema import CheckField, Dose, Food, Form, Kind, MedLine, Unit
from pillclerk.validate import extra_rules

apply_theme()
import streamlit as st
import streamlit.components.v1 as components

RAW = ROOT / "data" / "real" / "raw"
PHOTOS = (".jpg", ".jpeg", ".png", ".webp", ".heic")
FORMS: list[Form] = ["tab", "cap", "syrup", "drops", "inhaler", "injection", "cream", "sachet", "other"]
KINDS: list[Kind] = ["daily", "prn", "taper"]
FOODS: list[Food] = ["before", "after", "with", "empty_stomach", "any"]
UNITS: list[Unit] = ["tab", "cap", "ml", "drop", "puff", "unit", "sachet", "apply"]
CHECKS: list[CheckField] = ["drug", "strength", "dose", "food", "duration_days", "schedule"]


def _photos() -> list[Path]:
    if not RAW.is_dir():
        return []
    return sorted(p for p in RAW.iterdir() if p.suffix.lower() in PHOTOS)


def _gt_count() -> int:
    if not REAL.is_file():
        return 0
    return sum(1 for ln in REAL.read_text(encoding="utf-8").splitlines() if ln.strip())


def _append(line: str, med: MedLine, source: str) -> None:
    REAL.parent.mkdir(parents=True, exist_ok=True)
    n = _gt_count() + 1
    row = {
        "id": f"{source}-l{n:03d}",
        "line": line.strip(),
        "gold": json.loads(med.model_dump_json()),
        "source": source,
        "style": "photographed",
        "synthetic": False,
        "held_out": True,
        "photographed": True,
    }
    with REAL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


st.title("Label REAL")
st.caption(
    "Photographed family lines only. Gold copies the slip. Photos never leave this laptop "
    "(local Ollama gemma4:e4b, or type). Gemini is not used here."
)

photos = _photos()
labelled = _gt_count()
target = 80
st.markdown(f"**{labelled} / {target} labelled** · {len(photos)} photos in `data/real/raw/`")
if labelled < 50:
    st.info("Fewer than 50 lines is a **small real set** — 95% CIs will be shown prominently.")

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
    const b = [...doc.querySelectorAll('button')].find(x => x.innerText.includes('Next photo'));
    if (b) b.click();
  }
});
</script>
""",
    height=0,
)

if "photo_i" not in st.session_state:
    st.session_state.photo_i = 0
if photos:
    i = st.session_state.photo_i % len(photos)
    photo = photos[i]
    st.caption(f"Photo {i + 1}/{len(photos)} · {photo.name}")
    try:
        st.image(str(photo), width=480)
    except Exception:
        st.write(photo.name)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Propose line (local Ollama)"):
            try:
                proposed = transcribe_local(str(photo))
                st.session_state.line_box = "\n".join(proposed)
            except Exception as exc:
                st.warning(f"Ollama unavailable — type the line. ({exc})")
    with c2:
        if st.button("Next photo"):
            st.session_state.photo_i = i + 1
            st.rerun()
else:
    photo = None
    st.warning("No photos yet. Drop files in data/real/raw/ (rx01.jpg …). WhatsApp screenshots optional.")

line = st.text_area(
    "Transcribed line (pre-filled from local Ollama if you tapped Propose)",
    height=80,
    key="line_box",
)
c1, c2, c3 = st.columns(3)
drug = c1.text_input("Drug")
strength = c2.text_input("Strength")
form = c3.selectbox("Form", FORMS)
c1, c2, c3 = st.columns(3)
kind = c1.selectbox("Kind", KINDS)
food = c2.selectbox("Food", FOODS)
duration = c3.number_input("Duration days (0=continue)", min_value=0, value=0)
m1, m2, m3, m4 = st.columns(4)
morning = m1.number_input("Morning", min_value=0.0, max_value=20.0, value=0.0, step=0.5)
afternoon = m2.number_input("Afternoon", min_value=0.0, max_value=20.0, value=0.0, step=0.5)
night = m3.number_input("Night", min_value=0.0, max_value=20.0, value=0.0, step=0.5)
unit = m4.selectbox("Unit", UNITS)
prn = st.number_input("PRN max/day (0=unset)", min_value=0, value=0)
ask = st.checkbox("ASK — field is unclear; do not guess")
flags = st.multiselect("needs_check details", CHECKS, default=(["dose", "schedule"] if ask else []))
if ask and not flags:
    flags = ["dose"]

src = photo.stem if photo else "manual"
st.caption("Keyboard: **A** accept & next · **N** next photo (when not typing in a field).")

if st.button("Accept", type="primary"):
    if not line.strip():
        st.warning("Paste or propose a line first.")
    else:
        dose = None if kind == "prn" else Dose(morning=morning, afternoon=afternoon, night=night, unit=unit)
        med = extra_rules(
            MedLine(
                drug=drug.strip() or None,
                strength=strength.strip() or None,
                form=form,
                kind=kind,
                dose=dose,
                food=food,
                duration_days=int(duration) or None,
                prn_max_per_day=int(prn) or None,
                needs_check=flags,
                note=line.strip(),
            )
        )
        _append(line, med, src)
        st.session_state.line_box = ""
        if photos:
            st.session_state.photo_i = st.session_state.photo_i + 1
        st.success(f"Saved {src}. Now {_gt_count()} / {target}.")
        st.rerun()
