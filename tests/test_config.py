"""Backend env switches. No keys required."""

import json

import pytest

from pillclerk import config


def test_theme_uses_senior_care_palette() -> None:
    from pillclerk.ui import ACCENT, ASK, CSS, PRIMARY

    assert PRIMARY == "#0369A1"
    assert ACCENT == "#16A34A"
    assert ASK == "#DC2626"
    assert "Figtree" in CSS
    assert "Noto Sans Devanagari" in CSS


def test_as_token_ids_unwraps_batch_encoding() -> None:
    from pillclerk.infer import as_token_ids

    assert as_token_ids({"input_ids": [1, 2, 3]}) == [1, 2, 3]
    assert as_token_ids([[4, 5]]) == [4, 5]


def test_extract_json_strips_fences() -> None:
    from pillclerk.infer import _extract_json

    raw = '```json\n{"drug": "Glycomet"}\n```'
    assert _extract_json(raw) == '{"drug": "Glycomet"}'


def test_b0_fair_few_shot_not_in_eval_sets() -> None:
    from pathlib import Path

    from pillclerk.infer import FEW_SHOT, JSON_ONLY, chat_messages

    eval_lines = set()
    for p in (
        Path("data/synth/synth_test.jsonl"),
        Path("data/heldout/handwritten_realistic.jsonl"),
    ):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                eval_lines.add(json.loads(line)["line"])
    assert len(FEW_SHOT) == 3
    from pillclerk.infer import GEMINI_EXTRA_FEW_SHOT

    assert len(GEMINI_EXTRA_FEW_SHOT) == 3
    for user, gold in FEW_SHOT:
        assert user not in eval_lines
        gold.model_dump_json()
    msgs = chat_messages("TAB. X 5MG 1-0-0 AFTER FOOD x 5 DAYS", few_shot=True)
    assert msgs[0]["role"] == "system"
    assert "JSON object only" in msgs[0]["content"]
    assert "dose is an object" in JSON_ONLY
    assert sum(1 for m in msgs if m["role"] == "assistant") == 3
    assert msgs[-1]["content"].startswith("TAB. X")
    plain = chat_messages("hello", few_shot=False)
    assert len(plain) == 2


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


def test_digitalocean_backend_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "digitalocean")
    with pytest.raises(ValueError, match="dropped"):
        config.llm_backend()
    monkeypatch.setenv("EXTRACT_BACKEND", "hosted")
    with pytest.raises(ValueError):
        config.extract_backend()
    monkeypatch.setenv("EXTRACT_BACKEND", "gemini")
    with pytest.raises(ValueError, match="never leave"):
        config.extract_backend()


def test_render_yaml_uses_port_and_free_plan() -> None:
    from pathlib import Path

    text = Path("render.yaml").read_text(encoding="utf-8")
    assert "$PORT" in text
    assert "plan: free" in text
    assert "LLM_BACKEND" in text
    assert "digitalocean" not in text.lower()
    assert not Path(".do/app.yaml").exists()
    arch = Path("docs/architecture.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "render.yaml provided; not deployed" in arch
    assert "render.yaml provided; not deployed" in readme


def test_gemini_key_status_presence_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "secret-should-not-leak")
    status = config.key_status()
    assert status["GEMINI_API_KEY"] is True
    assert "secret-should-not-leak" not in str(status)
    assert "DO_MODEL_ACCESS_KEY" not in status


def test_template_backend_skips_paid_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_BACKEND", "template")
    from pillclerk.render import get_llm_backend

    with pytest.raises(RuntimeError, match="template"):
        get_llm_backend()
