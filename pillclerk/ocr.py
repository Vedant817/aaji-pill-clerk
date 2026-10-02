"""Photo / paste → raw prescription lines.

EXTRACT_BACKEND=manual: split pasted text (default, no model).
EXTRACT_BACKEND=ollama: local gemma4:e4b (optional, needs disk).
EXTRACT_BACKEND=hosted: DigitalOcean Gemma (optional, needs a card).
"""

from __future__ import annotations

from pillclerk import config


def lines_from_text(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def extract_from_image(path: str) -> list[str]:
    backend = config.extract_backend()
    if backend == "manual":
        raise RuntimeError(
            "EXTRACT_BACKEND=manual: paste the lines instead of sending a photo to a model."
        )
    if backend == "hosted":
        raise RuntimeError(
            "EXTRACT_BACKEND=hosted needs DigitalOcean. This weekend we skip DO. "
            "Paste the transcribed lines, or set EXTRACT_BACKEND=ollama if gemma4:e4b is pulled."
        )
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
