"""Photo / paste → raw prescription lines.

EXTRACT_BACKEND=manual: split pasted text (default, no model).
EXTRACT_BACKEND=ollama: local gemma4:e4b on this laptop.
EXTRACT_BACKEND=windows: installed Windows OCR, local printed-text extraction.
Real photos never leave the laptop. Gemini is not an extract backend.
"""

from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys

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
    if backend == "windows":
        return transcribe_windows(p)
    if (is_photo_path(p) or is_real_path(p)) and backend != "ollama":
        raise PrivacyError("Prescription photos stay on this laptop. Use local Ollama or type the line.")
    import ollama

    return transcribe_local(path)


def transcribe_windows(path: Path) -> list[str]:
    """Windows' installed OCR engine, offline; no model download or hosted images."""
    if sys.platform != "win32":
        raise RuntimeError("Windows OCR needs Windows. Type the lines or configure local Ollama.")
    if not path.is_file():
        raise FileNotFoundError("Reference image is missing")
    executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    script = Path(__file__).parent / "resources/windows_ocr.ps1"
    try:
        result = subprocess.run([str(executable), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", str(script), "-ImagePath", str(path.resolve()),
            "-LanguageTag", config._get("WINDOWS_OCR_LANGUAGE", "en-US")],
            capture_output=True, encoding="utf-8-sig", timeout=60, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Local OCR timed out. Type the prescription lines instead.") from exc
    if result.returncode:
        raise RuntimeError("Windows OCR could not read this image. Check the installed language or type the lines.")
    try:
        payload = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("Local OCR returned an invalid result. Type the lines instead.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Local OCR returned an invalid result. Type the lines instead.")
    lines = payload.get("lines")
    if not isinstance(lines, list) or any(not isinstance(x, str) for x in lines):
        raise RuntimeError("Local OCR returned an invalid result. Type the lines instead.")
    return [x.strip() for x in lines if x.strip()]


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
