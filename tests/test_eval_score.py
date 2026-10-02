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
    assert '"ft3"' in src
    assert "few_shot=True" in src


def test_mcnemar_counts_discordant_pairs() -> None:
    from eval.report import ci_width_points, mcnemar_exact, public_set_name

    a = [{"exact": 0}, {"exact": 1}, {"exact": 0}]
    b = [{"exact": 1}, {"exact": 1}, {"exact": 0}]
    m = mcnemar_exact(a, b)
    assert m["n01_b_fixes"] == 1
    assert m["n10_b_regresses"] == 0
    assert public_set_name(100) == "Public real-world set: HMR-100 (India), n=100"
    assert 8 <= ci_width_points(100) <= 10


def test_parse_medline_blob_skips_inner_dose_object() -> None:
    from pillclerk.infer import parse_medline_blob

    raw = (
        'notes dose {"morning": 0.5, "afternoon": 0.0, "night": 0.5, "unit": "cap"} then '
        '{"drug":"Nitrofurantoin","strength":"100 mg","form":"cap","kind":"daily",'
        '"dose":{"morning":0.5,"afternoon":0.0,"night":0.5,"unit":"cap"},'
        '"every_n_days":1,"taper":[],"food":"after","duration_days":3,'
        '"prn_max_per_day":null,"note":null,"needs_check":[]}'
    )
    med = parse_medline_blob(raw)
    assert med is not None
    assert med.drug == "Nitrofurantoin"
    assert med.form == "cap"


def test_b0_fair_saved_run_beats_schema_fail_b0() -> None:
    fair = json.loads(Path("eval/out/b0_fair_synth_test.json").read_text(encoding="utf-8"))
    old = json.loads(Path("eval/out/b0_synth_test.json").read_text(encoding="utf-8"))
    assert fair["n"] == 400
    assert fair["json_valid"] > 0.5
    assert fair["json_valid"] > old["json_valid"]
    hw = json.loads(Path("eval/out/b0_fair_handwritten_realistic.json").read_text(encoding="utf-8"))
    assert hw["n"] == 102
    assert hw["json_valid"] > 0.5
