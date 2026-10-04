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
from urllib.parse import urlparse
from ipaddress import ip_address

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
    import httpx

    client = local_ocr_client()
    model = config.OLLAMA_EXTRACT_MODEL
    # Model aliases can redirect through Ollama Cloud even on a local daemon.
    try:
        metadata = client._request_raw("POST", "/api/show", json={"model": model}).json()
    except (httpx.HTTPError, ollama.ResponseError, ConnectionError, ValueError) as exc:
        raise RuntimeError("Local OCR model is unavailable. Start Ollama or type the lines.") from exc
    if not isinstance(metadata, dict):
        raise RuntimeError("Local OCR returned invalid model information. Type the lines instead.")
    if metadata.get("remote_host") or metadata.get("remote_model"):
        raise PrivacyError("Photo extraction requires a locally stored model, not an Ollama Cloud alias.")
    try:
        r = client.chat(
            model=model,
            think=False,
            options={"temperature": 0, "num_ctx": 4096, "num_predict": 1024},
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
    except (httpx.HTTPError, ollama.ResponseError, ConnectionError) as exc:
        raise RuntimeError("Local OCR failed or timed out. Type the lines instead.") from exc
    if r.done_reason == "length":
        raise RuntimeError("Local OCR output was truncated. Type the lines or read a smaller photo.")
    return lines_from_text(r.message.content or "")


def local_ocr_client():
    """Restrict image requests to loopback and bound connection/read waits."""
    import ollama
    import httpx

    host = config._get("OLLAMA_HOST", "http://127.0.0.1:11434")
    if "://" not in host:
        host = "http://" + host
    parsed = urlparse(host)
    try:
        loopback = parsed.hostname == "localhost" or ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        loopback = False
    if not loopback or parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise PrivacyError("Photo extraction requires Ollama on this laptop's loopback address.")
    if "cloud" in config.OLLAMA_EXTRACT_MODEL.casefold():
        raise PrivacyError("Photo extraction requires a local Ollama model; cloud tags are disabled.")
    return ollama.Client(host=host, timeout=httpx.Timeout(300, connect=5), trust_env=False)
