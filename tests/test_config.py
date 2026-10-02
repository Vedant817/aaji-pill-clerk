"""Backend env switches. No keys required."""

import pytest

from pillclerk import config


def test_as_token_ids_unwraps_batch_encoding() -> None:
    from pillclerk.infer import as_token_ids

    assert as_token_ids({"input_ids": [1, 2, 3]}) == [1, 2, 3]
    assert as_token_ids([[4, 5]]) == [4, 5]


def test_extract_json_strips_fences() -> None:
    from pillclerk.infer import _extract_json

    raw = '```json\n{"drug": "Glycomet"}\n```'
    assert _extract_json(raw) == '{"drug": "Glycomet"}'


def test_set_dotenv_value_does_not_echo_secret(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = tmp_path / ".env"
    env.write_text("TINKER_API_KEY=\nPILLCLERK_TINKER_PATH=\n", encoding="utf-8")
    from pillclerk.config import set_dotenv_value

    set_dotenv_value("PILLCLERK_TINKER_PATH", "tinker://weights/sampler", path=env)
    text = env.read_text(encoding="utf-8")
    assert "PILLCLERK_TINKER_PATH=tinker://weights/sampler" in text
    assert "TINKER_API_KEY=" in text


def test_apply_tinker_checkpoint(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pillclerk import config

    ck = tmp_path / "checkpoint_v1.json"
    ck.write_text(
        '{"sampler": "tinker://abc:train:0/sampler_weights/pillclerk-v1"}',
        encoding="utf-8",
    )
    env = tmp_path / ".env"
    env.write_text("PILLCLERK_TINKER_PATH=\n", encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    assert config.apply_tinker_checkpoint(ck) is True
    assert config._get("PILLCLERK_TINKER_PATH").startswith("tinker://")


def test_tinker_parser_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINKER_API_KEY", "x")
    monkeypatch.setenv("PILLCLERK_TINKER_PATH", "")
    from pillclerk.config import tinker_parser_ready

    assert tinker_parser_ready() is False
    monkeypatch.setenv("PILLCLERK_TINKER_PATH", "tinker://x")
    assert tinker_parser_ready() is True


def test_key_status_never_returns_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TINKER_API_KEY", "secret-should-not-leak")
    status = config.key_status()
    blob = str(status)
    assert "secret-should-not-leak" not in blob
    assert status["TINKER_API_KEY"] is True


def test_default_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.delenv("EXTRACT_BACKEND", raising=False)
    monkeypatch.delenv("PARSER_BACKEND", raising=False)
    monkeypatch.delenv("PILLCLERK_BACKEND", raising=False)
    assert config.llm_backend() == "template"
    assert config.extract_backend() == "manual"
    assert config.parser_backend() == "tinker"


def test_parser_backend_falls_back_to_pillclerk_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PARSER_BACKEND", raising=False)
    monkeypatch.setenv("PILLCLERK_BACKEND", "tinker")
    assert config.parser_backend() == "tinker"


def test_invalid_backend_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "openai")
    with pytest.raises(ValueError):
        config.llm_backend()


def test_template_backend_skips_paid_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "template")
    from pillclerk.render import get_llm_backend

    with pytest.raises(RuntimeError, match="template"):
        get_llm_backend()
