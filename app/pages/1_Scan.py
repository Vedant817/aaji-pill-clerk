"""Paste prescription lines (EXTRACT_BACKEND=manual). Photos stay on this machine."""

from pillclerk.ui import apply_theme, stepper
from pillclerk.drafts import drafts_from_text
from pillclerk.review import clear_review_keys
from pillclerk.config import extract_backend
from pillclerk.ocr import extract_from_image
from pathlib import Path
from tempfile import TemporaryDirectory

apply_theme()
import streamlit as st

stepper("Scan")
st.title("Scan")
st.caption(
    "Paste one medicine line per row from the slip in front of you. "
    "Photos stay on this laptop. Check extracted text against the photo before loading it."
)


def _photo_changed():
    st.session_state["scan_extracted"] = False
    st.session_state["scan_text_checked"] = False
    st.session_state["scan_text"] = ""


def _text_changed():
    st.session_state["scan_text_checked"] = False


def _clear_scan():
    # Widget values may only be reset before the new page run instantiates them.
    st.session_state.pop("drafts", None)
    clear_review_keys(st.session_state)
    st.session_state["scan_extracted"] = False
    st.session_state["scan_text_checked"] = False
    st.session_state["scan_text"] = ""


photo = st.file_uploader("Prescription photo (local reference while typing)", type=["jpg", "jpeg", "png", "webp"], on_change=_photo_changed)
if photo is not None:
    st.image(photo, caption="Type what you can read. Use [?] for anything unclear.")
    backend = extract_backend()
    if backend == "manual":
        st.caption("Manual transcription is selected. Local OCR can be configured with EXTRACT_BACKEND=windows or ollama.")
    elif st.button("Read text locally from photo"):
        try:
            with st.spinner("Reading locally. Check every character against the photo."):
                with TemporaryDirectory(prefix="pillclerk-ocr-") as temporary:
                    path = Path(temporary) / ("reference" + Path(photo.name).suffix.lower())
                    path.write_bytes(photo.getvalue())
                    lines = extract_from_image(str(path))
            st.session_state["scan_text"] = "\n".join(lines)
            st.session_state["scan_extracted"] = True
            st.session_state["scan_text_checked"] = False
            if not lines:
                st.warning("No text was found. Type what you can read from the photo.")
        except (OSError, RuntimeError, ValueError):
            st.error("Local extraction is unavailable for this image. Type the lines below; nothing was sent to a hosted image service.")
    if backend == "windows":
        st.caption("Windows OCR uses installed language support. Printed-text extraction is supported; handwriting accuracy has not been validated.")

text = st.text_area(
    "Prescription lines",
    height=240,
    placeholder="Paste one medicine line per row",
    key="scan_text",
    on_change=_text_changed,
)
checked = True
if st.session_state.get("scan_extracted"):
    checked = st.checkbox("I checked the extracted text against the photo and removed non-medicine lines", key="scan_text_checked")
c0, c1 = st.columns([1, 1])
with c0:
    load = st.button("Load lines", type="primary", disabled=not checked)
with c1:
    st.button("Clear", on_click=_clear_scan)

if load:
    raw = text.strip()
    if not raw:
        st.warning("Paste at least one line from the prescription.")
    else:
        drafts = drafts_from_text(raw)
        clear_review_keys(st.session_state)
        st.session_state["drafts"] = drafts
        st.session_state["review_i"] = 0
        st.switch_page("pages/2_Review.py")
elif st.session_state.get("drafts"):
    st.info(f"{len(st.session_state['drafts'])} line(s) loaded. Open Review to confirm.")
    st.page_link("pages/2_Review.py", label="Go to Review →")
