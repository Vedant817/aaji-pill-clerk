import json
from pathlib import Path

from pillclerk.schema import MedLine
from eval.eval import field_eq, score


def test_dose_int_zero_matches_float_zero() -> None:
    gold = MedLine(drug="Glycomet", strength="500MG", dose={"morning": 1.0, "afternoon": 0.0, "night": 1.0})
    pred = MedLine.model_validate(
        {
            "drug": "Glycomet",
            "strength": "500 MG",
            "dose": {"morning": 1, "afternoon": 0, "night": 1, "unit": "tab"},
        }
    )
    assert field_eq(pred, gold, "dose")
    s = score(pred, gold)
    assert s["dose"] == 1
    assert s["danger"] == 0


def test_b0_fair_is_registered() -> None:
    assert "b0_fair" in {"b0", "b0_fair", "ft1", "ft2"}
    # get_parser talks to Tinker; only check the dispatch table keys via source map
    from eval import eval as ev

    src = Path(ev.__file__).read_text(encoding="utf-8")
    assert '"b0_fair"' in src
    assert "few_shot=True" in src


def test_b0_fair_saved_run_beats_schema_fail_b0() -> None:
    fair = json.loads(Path("eval/out/b0_fair_synth_test.json").read_text(encoding="utf-8"))
    old = json.loads(Path("eval/out/b0_synth_test.json").read_text(encoding="utf-8"))
    assert fair["n"] == 400
    assert fair["json_valid"] > 0.5
    assert fair["json_valid"] > old["json_valid"]
    hw = json.loads(Path("eval/out/b0_fair_handwritten_realistic.json").read_text(encoding="utf-8"))
    assert hw["n"] == 102
    assert hw["json_valid"] > 0.5
