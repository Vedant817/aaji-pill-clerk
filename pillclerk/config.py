"""Env-switched backends. No secrets are hardcoded."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

LlmBackend = Literal["template", "digitalocean", "backboard", "tinker"]
ExtractBackend = Literal["manual", "ollama", "hosted"]
ParserBackend = Literal["tinker", "ollama"]

ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path | None = None) -> Path | None:
    """Load KEY=value from .env into os.environ if the key is not already set."""
    env_path = path or ROOT / ".env"
    if not env_path.is_file():
        return None
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value
    return env_path


load_dotenv()


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


def key_status() -> dict[str, bool]:
    """Presence only. Never returns secret values."""
    return {
        "TINKER_API_KEY": bool(_get("TINKER_API_KEY")),
        "PILLCLERK_TINKER_PATH": bool(_get("PILLCLERK_TINKER_PATH")),
        "DO_MODEL_ACCESS_KEY": bool(_get("DO_MODEL_ACCESS_KEY")),
        "BACKBOARD_API_KEY": bool(_get("BACKBOARD_API_KEY")),
    }


def tinker_parser_ready() -> bool:
    return bool(_get("TINKER_API_KEY") and _get("PILLCLERK_TINKER_PATH"))


def set_dotenv_value(name: str, value: str, path: Path | None = None) -> Path:
    """Set KEY=value in a .env file. Does not print the value."""
    env_path = path or ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
    prefix = f"{name}="
    written = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(prefix) and not stripped.startswith("#"):
            out.append(f"{name}={value}")
            written = True
        else:
            out.append(line)
    if not written:
        out.append(f"{name}={value}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.environ[name] = value
    return env_path


def apply_tinker_checkpoint(checkpoint: Path | None = None) -> bool:
    """Copy sampler path from checkpoint JSON into .env and os.environ."""
    ck = checkpoint or ROOT / "train" / "checkpoint_v1.json"
    if not ck.is_file():
        return False
    data = json.loads(ck.read_text(encoding="utf-8"))
    sampler = str(data.get("sampler") or "").strip()
    if not sampler.startswith("tinker://"):
        return False
    set_dotenv_value("PILLCLERK_TINKER_PATH", sampler)
    return True


DO_BASE_URL = _get("DO_BASE_URL", "https://inference.do-ai.run/v1")
DO_TEACHER_MODEL = _get("DO_TEACHER_MODEL", "gemma-4-31B-it")
BACKBOARD_BASE_URL = _get("BACKBOARD_BASE_URL", "https://app.backboard.io/api")
BACKBOARD_LLM_PROVIDER = _get("BACKBOARD_LLM_PROVIDER", "google")
BACKBOARD_MODEL_NAME = _get("BACKBOARD_MODEL_NAME", "gemma-4-31b-it")
OLLAMA_EXTRACT_MODEL = _get("OLLAMA_EXTRACT_MODEL", "gemma4:e4b")
OLLAMA_PARSER_MODEL = _get("OLLAMA_PARSER_MODEL", "pillclerk")
BASE_MODEL = "Qwen/Qwen3-8B"
RENDERER_NAME = "qwen3_disable_thinking"
