"""Photo / paste → raw prescription lines.

EXTRACT_BACKEND=manual: split pasted text (default, no model).
EXTRACT_BACKEND=ollama: local gemma4:e4b on this laptop.
Real photos never leave the laptop. Gemini is not an extract backend.
"""

from __future__ import annotations

from pathlib import Path

from pillclerk import config
from pillclerk.privacy import PrivacyError, is_photo_path, is_real_path


def lines_from_text(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def extract_from_image(path: str) -> list[str]:
    backend = config.extract_backend()
    p = Path(path)
    if backend == "manual":
        raise RuntimeError(
            "EXTRACT_BACKEND=manual: paste the lines instead of sending a photo to a model."
        )
    if (is_photo_path(p) or is_real_path(p)) and backend != "ollama":
        raise PrivacyError("Prescription photos stay on this laptop. Use local Ollama or type the line.")
    import ollama

    return transcribe_local(path)


def transcribe_local(path: str) -> list[str]:
    """Always local Ollama. Never Gemini. Used for photographed slips."""
    import ollama

    r = ollama.chat(
        model=config.OLLAMA_EXTRACT_MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    "Transcribe each medicine line of this prescription verbatim, one per line. "
                    "Write [?] for unreadable characters."
                ),
                "images": [path],
            }
        ],
    )
    return lines_from_text(r.message.content or "")
