import hashlib
import json
from types import SimpleNamespace

import pytest

from pillclerk import acceptance, infer
from pillclerk.schema import Dose, MedLine
from scripts.prepare_ai_reference import build


def test_ai_reference_provenance_and_images_are_checked(tmp_path, monkeypatch):
    monkeypatch.setattr(acceptance, "ROOT", tmp_path)
    image = tmp_path / "page.jpg"
    image.write_bytes(b"test-only image")
    queue = tmp_path / "queue"
    queue.mkdir()
    (queue / "manifest.json").write_text(json.dumps({"image_directory": ".", "pages": [{
        "image": "page.jpg", "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}]}))
    drafts = tmp_path / "drafts.json"
    drafts.write_text(json.dumps({"page.jpg": [["Tab TestOnly 1-0-0 x5d",
        MedLine(drug="TestOnly", dose=Dose(morning=1), duration_days=5).model_dump()]]}))
    output = tmp_path / "reference"
    manifest = build(drafts, output, queue)
    assert manifest["independent_annotation_rounds"] == 0
    gold = json.loads((output / "ai_reference.jsonl").read_text())
    assert not gold["human_verified"] and not gold["double_checked"]
    assert gold["label_origin"] == "ai_single_agent"
    assert build(drafts, output, queue) == manifest
    image.write_bytes(b"modified")
    with pytest.raises(ValueError, match="image changed"):
        build(drafts, output, queue)


def fake_sampling(monkeypatch, raw):
    import tinker
    calls = []
    tokenizer = SimpleNamespace(apply_chat_template=lambda *a, **kw: [1, 2, 3], decode=lambda tokens: raw)

    def sample(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(result=lambda: SimpleNamespace(sequences=[SimpleNamespace(tokens=[1, 2], stop_reason="stop")]))

    client = SimpleNamespace(get_tokenizer=lambda: tokenizer, sample=sample)
    monkeypatch.setattr(tinker, "ServiceClient", lambda: SimpleNamespace(create_sampling_client=lambda **kwargs: client))
    return calls


def test_raw_schema_failure_is_visible_despite_recovery(monkeypatch):
    fake_sampling(monkeypatch, "invalid JSON")
    out = infer.make_tinker_parser("tinker://test", detailed=True)("Tab [?] [?]")
    assert out.raw == "invalid JSON" and out.pred is not None
    assert out.error == "raw_schema" and out.accepted_config["recovery_used"]
    assert out.finish_reason == "stop"


def test_sampling_budget_refuses_before_provider_call(monkeypatch):
    calls = fake_sampling(monkeypatch, "invalid JSON")
    parse = infer.make_tinker_parser("tinker://test", detailed=True, sampling_budget_usd=0.000001)
    with pytest.raises(RuntimeError, match="budget exhausted"):
        parse("Tab TestOnly 1-0-0")
    assert not calls
    with pytest.raises(ValueError, match="finite"):
        infer.make_tinker_parser("tinker://test", sampling_budget_usd=float("nan"))


def test_explicit_checkpoint_does_not_change_active_environment(tmp_path, monkeypatch):
    from eval.eval import get_parser
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(json.dumps({"sampler": "tinker://candidate"}))
    monkeypatch.setenv("PILLCLERK_TINKER_PATH", "tinker://active")
    monkeypatch.setattr(infer, "make_tinker_parser", lambda path, **kwargs: (path, kwargs))
    path, options = get_parser("candidate", checkpoint=str(checkpoint), sampling_budget_usd=0.3)
    assert path == "tinker://candidate" and options["detailed"]
    import os
    assert os.environ["PILLCLERK_TINKER_PATH"] == "tinker://active"
