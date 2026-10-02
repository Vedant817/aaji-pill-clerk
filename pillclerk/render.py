"""LLM renderer: DigitalOcean Gemma 4 31B, optional Backboard. Same ChatBackend interface.

Paid calls happen only when a backend method is invoked. Do not call this module
until TINKER / DO / Backboard keys are in .env and the user has agreed to spend.
"""

from __future__ import annotations

import json
import re
from typing import Protocol

import httpx
from openai import OpenAI

from pillclerk import config
from pillclerk.schema import SYSTEM_PROMPT, MedLine

TEACHER = config.DO_TEACHER_MODEL
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


class DigitalOceanBackend:
    """OpenAI-compatible client for https://inference.do-ai.run/v1."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> None:
        self.model = model or config.DO_TEACHER_MODEL
        self.client = OpenAI(
            base_url=(base_url or config.DO_BASE_URL),
            api_key=api_key or config.require_env("DO_MODEL_ACCESS_KEY"),
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        model: str | None = None,
    ) -> str:
        r = self.client.chat.completions.create(
            model=model or self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,  # type: ignore[arg-type]
        )
        content = r.choices[0].message.content
        return (content or "").strip()


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
            "It does not call DigitalOcean, Backboard, or Tinker for messy text. "
            "Set LLM_BACKEND=backboard or tinker if you want an LLM renderer without DigitalOcean."
        )
    if name == "backboard":
        return BackboardBackend()
    if name == "tinker":
        raise RuntimeError(
            "LLM_BACKEND=tinker for synthetic render is not wired yet. "
            "Use --renderer template (free) or LLM_BACKEND=backboard."
        )
    return DigitalOceanBackend()


def render(gold: MedLine, style: str, backend: ChatBackend | None = None) -> str:
    backend = backend or get_llm_backend()
    return backend.complete(
        [
            {"role": "system", "content": RENDER_SYS},
            {
                "role": "user",
                "content": f"STYLE: {STYLES[style]}\nJSON: {gold.model_dump_json(exclude_defaults=True)}",
            },
        ],
        temperature=0.9,
        max_tokens=120,
    )


def parse_back(line: str, backend: ChatBackend | None = None) -> MedLine | None:
    backend = backend or get_llm_backend()
    txt = backend.complete(
        [
            {
                "role": "system",
                "content": SYSTEM_PROMPT + "\nSchema: " + json.dumps(MedLine.model_json_schema()),
            },
            {"role": "user", "content": line},
        ],
        temperature=0.0,
        max_tokens=400,
    )
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
            {"role": "assistant", "content": gold.model_dump_json(exclude_defaults=True)},
        ]
    }
