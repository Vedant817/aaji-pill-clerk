"""LLM renderer: Google AI Studio Gemma 4 31B, optional Backboard.

Paid calls happen only when a backend method is invoked. Do not call this
module until GEMINI / Backboard keys are in .env and the user has agreed to spend.
DigitalOcean is dropped.
"""

from __future__ import annotations

import json
import re
import time
from typing import Protocol

import httpx

from pillclerk import config
from pillclerk.privacy import log_sent_payload, redact_secret, strip_pii
from pillclerk.schema import SYSTEM_PROMPT, MedLine

TEACHER = config.GEMINI_MODEL
STYLES = {
    "clinic_print": "Printed clinic software line, e.g. 'TAB. X 500MG  1-0-1  AFTER FOOD  x 30 DAYS'",
    "doctor_short": "Indian doctor's handwritten shorthand: OD/BD/TDS/HS/SOS, AC/PC, 1-0-1, x5d, 1/12",
    "hinglish_wa": "A caregiver's WhatsApp message in Hinglish, casual, may skip the strength",
    "marathi": "Marathi in Devanagari as a family member would write it (सकाळी/दुपारी/रात्री, जेवणानंतर)",
    "hindi": "Hindi in Devanagari (सुबह/दोपहर/रात, खाने के बाद)",
    "mixed": "Mix English drug name with Hindi time words",
}
RENDER_SYS = (
    "Write ONE realistic prescription or instruction line that encodes EXACTLY the JSON given. "
    "Do not add or drop information. Use the requested style. Output the line only."
)


class ChatBackend(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> str: ...


class GeminiBackend:
    """Google AI Studio / Gemini API. Model id gemma-4-31b-it (official list)."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or config.require_env("GEMINI_API_KEY")
        self.model = model or config.GEMINI_MODEL
        self.base = config.GEMINI_API_BASE.rstrip("/")

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> str:
        system = " ".join(m["content"] for m in messages if m["role"] == "system")
        contents: list[dict] = []
        for m in messages:
            if m["role"] == "system":
                continue
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "thinkingConfig": {"thinkingLevel": "minimal"},
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        url = f"{self.base}/models/{model or self.model}:generateContent"
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        last_err: Exception | None = None
        for attempt in range(6):
            try:
                with httpx.Client(timeout=120.0) as client:
                    r = client.post(url, headers=headers, json=payload)
                    if r.status_code == 400 and "generationConfig" in payload:
                        cfg = dict(payload["generationConfig"])
                        cfg.pop("thinkingConfig", None)
                        cfg.pop("responseMimeType", None)
                        payload["generationConfig"] = cfg
                        last_err = httpx.HTTPStatusError(
                            r.text[:200], request=r.request, response=r
                        )
                        continue
                    if r.status_code in {429, 500, 503}:
                        time.sleep(min(2**attempt, 30))
                        last_err = httpx.HTTPStatusError(
                            f"{r.status_code}", request=r.request, response=r
                        )
                        continue
                    r.raise_for_status()
                    data = r.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                return "".join(str(p.get("text") or "") for p in parts).strip()
            except httpx.HTTPError as exc:
                last_err = exc
                time.sleep(min(2**attempt, 30))
        raise RuntimeError(f"Gemini generateContent failed: {redact_secret(last_err, self.api_key)}")


class BackboardBackend:
    """Optional Backboard drop-in. Native API is not OpenAI-compatible; we wrap it."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or config.require_env("BACKBOARD_API_KEY")
        self.base_url = (base_url or config.BACKBOARD_BASE_URL).rstrip("/")
        self.provider = config.BACKBOARD_LLM_PROVIDER
        self.model_name = config.BACKBOARD_MODEL_NAME

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> str:
        system = " ".join(m["content"] for m in messages if m["role"] == "system")
        user = "\n".join(m["content"] for m in messages if m["role"] != "system")
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "content": user,
            "system_prompt": system or None,
            "llm_provider": self.provider,
            "model_name": model or self.model_name,
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=60.0) as client:
            r = client.post(f"{self.base_url}/threads/messages", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        return str(data.get("content") or data.get("message") or "").strip()


def get_llm_backend() -> ChatBackend:
    name = config.llm_backend()
    if name == "template":
        raise RuntimeError(
            "LLM_BACKEND=template uses the free Python renderer only. "
            "It does not call Gemini, Backboard, or Tinker for messy text. "
            "Set LLM_BACKEND=gemini or backboard if you want an LLM renderer."
        )
    if name == "backboard":
        return BackboardBackend()
    if name == "tinker":
        raise RuntimeError(
            "LLM_BACKEND=tinker for synthetic render is not wired yet. "
            "Use --renderer template (free) or LLM_BACKEND=gemini."
        )
    return GeminiBackend()


def _model_name(backend: ChatBackend) -> str:
    return str(getattr(backend, "model", None) or getattr(backend, "model_name", None) or type(backend).__name__)


def render(gold: MedLine, style: str, backend: ChatBackend | None = None) -> str:
    backend = backend or get_llm_backend()
    raw = f"STYLE: {STYLES[style]}\nJSON: {gold.model_dump_json(exclude_defaults=True)}"
    clean, stripped = strip_pii(raw)
    messages = [
        {"role": "system", "content": RENDER_SYS},
        {"role": "user", "content": clean},
    ]
    log_sent_payload(
        system="render",
        set_path="synthetic_render",
        model=_model_name(backend),
        line=clean,
        stripped=stripped,
        messages=messages,
    )
    return backend.complete(messages, temperature=0.9, max_tokens=120)


def parse_back(line: str, backend: ChatBackend | None = None) -> MedLine | None:
    backend = backend or get_llm_backend()
    clean, stripped = strip_pii(line)
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + "\nSchema: " + json.dumps(MedLine.model_json_schema()),
        },
        {"role": "user", "content": clean},
    ]
    log_sent_payload(
        system="parse_back",
        set_path="synthetic_parse_back",
        model=_model_name(backend),
        line=clean,
        stripped=stripped,
        messages=messages,
    )
    txt = backend.complete(messages, temperature=0.0, max_tokens=400)
    txt = re.sub(r"^```(?:json)?|```$", "", txt.strip()).strip()
    try:
        return MedLine.model_validate_json(txt)
    except Exception:
        return None


def to_chat_row(line: str, gold: MedLine) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": line},
            {"role": "assistant", "content": gold.model_dump_json()},
        ]
    }
