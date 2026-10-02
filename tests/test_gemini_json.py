import json
from pathlib import Path

from pillclerk.infer import (
    FEW_SHOT,
    GEMINI_EXTRA_FEW_SHOT,
    JSON_SCHEMA_HINTS,
    classify_gemini_failure,
    gemini_teacher_messages,
)
from pillclerk.render import accepted_config_flags, gemini_generation_configs
from pillclerk.schema import MEDLINE_GEMINI_SCHEMA, MedLine
from eval.overlap import vs_eval
from eval.eval import score
from train.build_dataset import eval_drug_names


def test_medline_gemini_schema_has_enums_and_taper() -> None:
    schema = MEDLINE_GEMINI_SCHEMA
    assert schema["type"] == "OBJECT"
    assert schema["properties"]["form"]["enum"] == [
        "tab",
        "cap",
        "syrup",
        "drops",
        "inhaler",
        "injection",
        "cream",
        "sachet",
        "other",
    ]
    unit = schema["properties"]["dose"]["properties"]["unit"]["enum"]
    assert unit == ["tab", "cap", "ml", "drop", "puff", "unit", "sachet", "apply"]
    taper_dose = schema["properties"]["taper"]["items"]["properties"]["dose"]
    assert taper_dose["properties"]["unit"]["enum"] == unit
    assert "days" in schema["properties"]["taper"]["items"]["properties"]
    assert schema["properties"]["strength"]["type"] == "STRING"


def test_json_mode_config_tries_mime_and_schema_first() -> None:
    cfgs = gemini_generation_configs(temperature=0.0, max_tokens=1024, json_mode=True)
    assert cfgs[0]["responseMimeType"] == "application/json"
    assert "responseSchema" in cfgs[0]
    assert "thinkingConfig" in cfgs[0]
    flags = accepted_config_flags(cfgs[0])
    assert flags["responseMimeType"] == "application/json"
    assert flags["responseSchema"] is True
    plain = gemini_generation_configs(temperature=0.0, max_tokens=64, json_mode=False)
    assert "responseMimeType" not in plain[0]


def test_gemini_json_prompt_has_hints_and_six_shots() -> None:
    msgs = gemini_teacher_messages("Tab X 5mg OD", json_mode=True)
    blob = msgs[0]["content"]
    assert "tab|cap|ml|drop|puff|unit|sachet|apply" in blob
    assert "strength is a string" in blob
    assert "taper is a list" in JSON_SCHEMA_HINTS
    assert blob.count("Line:") == 7  # 6 examples + the query
    assert "Metrogyl" in blob
    assert "Timolol" in blob
    assert "Huminsulin" in blob
    old = gemini_teacher_messages("Tab X 5mg OD", json_mode=False)
    assert old[0]["content"].count("Line:") == 4
    assert "Huminsulin" not in old[0]["content"]


def test_extra_few_shot_not_in_eval_sets() -> None:
    assert len(FEW_SHOT) == 3
    assert len(GEMINI_EXTRA_FEW_SHOT) == 3
    lines = [u for u, _ in GEMINI_EXTRA_FEW_SHOT]
    overlap = vs_eval(lines, extra_name="gemini_extra_few_shot")
    assert overlap["any_exact_eval"] is False
    assert overlap["any_near_eval"] is False
    banned = eval_drug_names()
    for _u, gold in GEMINI_EXTRA_FEW_SHOT:
        assert gold.drug and gold.drug.lower() not in banned


def test_classify_gemini_failure_taxonomy() -> None:
    gold = MedLine(drug="Glycomet", dose={"morning": 1.0, "unit": "tab"})
    assert classify_gemini_failure("{}", "MAX_TOKENS", None) == "truncated"
    assert classify_gemini_failure("not json", None, None) == "no_json"
    assert classify_gemini_failure('{"drug": 1}', None, None) == "schema"
    assert classify_gemini_failure('{"drug":"X"}', None, gold) is None


def test_http_fail_is_not_parse_fail() -> None:
    gold = MedLine(drug="Glycomet", dose={"morning": 1.0, "unit": "tab"})
    s = score(None, gold, error="http_500")
    assert s["http_fail"] == 1
    assert s["parse_fail"] == 0
    assert s["danger_v2"] == 0
    assert s["danger_v2_norm"] == 0
    s2 = score(None, gold, error="schema")
    assert s2["parse_fail"] == 1
    assert s2["http_fail"] == 0
    assert s2["danger_v2"] == 0


def test_danger_v2_uses_normalised_drug_strength() -> None:
    gold = MedLine(drug="Telma", strength="40 mg", dose={"morning": 1.0, "unit": "tab"})
    pred = MedLine(drug="टेल्मा", strength="40mg", dose={"morning": 1.0, "afternoon": 0.0, "night": 0.0, "unit": "tab"})
    s = score(pred, gold)
    assert s["drug"] == 0
    assert s["exact"] == 0
    assert s["exact_norm"] == 1
    assert s["danger_v2_strict"] == 1
    assert s["danger_v2_norm"] == 0
    assert s["danger_v2"] == 0


def test_write_raw_jsonl(tmp_path: Path, monkeypatch) -> None:
    from eval import eval as ev

    monkeypatch.setattr(ev, "ROOT", tmp_path)
    (tmp_path / "eval" / "out").mkdir(parents=True)
    out = {"system": "gemma31_json", "n": 1}
    preds = [{"line": "x", "pred": None, "parse_fail": 0, "http_fail": 1}]
    raw = [{"line": "x", "raw": "", "error": "http_500", "finish_reason": None, "accepted_config": {}}]
    ev.write_out(out, preds, "data/synth/synth_test.jsonl", "gemma31_json", raw)
    path = tmp_path / "eval" / "out" / "gemma31_json_synth_test_raw.jsonl"
    row = json.loads(path.read_text(encoding="utf-8"))
    assert row["error"] == "http_500"


def test_eval_registers_gemma31_json() -> None:
    from eval import eval as ev

    src = Path(ev.__file__).read_text(encoding="utf-8")
    assert '"gemma31_json"' in src
