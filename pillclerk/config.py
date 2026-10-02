"""Env-switched backends. No secrets are hardcoded."""

from __future__ import annotations

import os
from typing import Literal

LlmBackend = Literal["template", "digitalocean", "backboard", "tinker"]
ExtractBackend = Literal["manual", "ollama", "hosted"]
ParserBackend = Literal["tinker", "ollama"]


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def llm_backend() -> LlmBackend:
    value = _get("LLM_BACKEND", "template").lower()
    if value not in ("template", "digitalocean", "backboard", "tinker"):
        raise ValueError(
            "LLM_BACKEND must be template, digitalocean, backboard, or tinker, "
            f"got {value!r}"
        )
    return value  # type: ignore[return-value]


def extract_backend() -> ExtractBackend:
    value = _get("EXTRACT_BACKEND", "manual").lower()
    if value not in ("manual", "ollama", "hosted"):
        raise ValueError(f"EXTRACT_BACKEND must be manual, ollama, or hosted, got {value!r}")
    return value  # type: ignore[return-value]


def parser_backend() -> ParserBackend:
    value = _get("PARSER_BACKEND") or _get("PILLCLERK_BACKEND", "tinker")
    value = value.lower()
    if value not in ("tinker", "ollama"):
        raise ValueError(f"PARSER_BACKEND must be tinker or ollama, got {value!r}")
    return value  # type: ignore[return-value]


def require_env(name: str) -> str:
    value = _get(name)
    if not value:
        raise RuntimeError(
            f"Missing {name}. Copy .env.example to .env and fill it in. "
            "Do not commit secrets."
        )
    return value


DO_BASE_URL = _get("DO_BASE_URL", "https://inference.do-ai.run/v1")
DO_TEACHER_MODEL = _get("DO_TEACHER_MODEL", "gemma-4-31B-it")
BACKBOARD_BASE_URL = _get("BACKBOARD_BASE_URL", "https://app.backboard.io/api")
BACKBOARD_LLM_PROVIDER = _get("BACKBOARD_LLM_PROVIDER", "google")
BACKBOARD_MODEL_NAME = _get("BACKBOARD_MODEL_NAME", "gemma-4-31b-it")
OLLAMA_EXTRACT_MODEL = _get("OLLAMA_EXTRACT_MODEL", "gemma4:e4b")
OLLAMA_PARSER_MODEL = _get("OLLAMA_PARSER_MODEL", "pillclerk")
