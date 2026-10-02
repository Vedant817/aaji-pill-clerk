"""Backend env switches. No keys required."""

import pytest

from pillclerk import config


def test_default_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.delenv("EXTRACT_BACKEND", raising=False)
    monkeypatch.delenv("PARSER_BACKEND", raising=False)
    monkeypatch.delenv("PILLCLERK_BACKEND", raising=False)
    assert config.llm_backend() == "digitalocean"
    assert config.extract_backend() == "hosted"
    assert config.parser_backend() == "tinker"


def test_parser_backend_falls_back_to_pillclerk_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PARSER_BACKEND", raising=False)
    monkeypatch.setenv("PILLCLERK_BACKEND", "tinker")
    assert config.parser_backend() == "tinker"


def test_invalid_backend_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "openai")
    with pytest.raises(ValueError):
        config.llm_backend()
