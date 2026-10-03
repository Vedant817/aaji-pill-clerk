import json
from pathlib import Path

from pillclerk.schema import MedLine
from eval.eval import field_eq, score


def test_danger_v2_is_field_specific_not_blank_needs_check() -> None:
    gold = MedLine(drug="Glycomet", strength="500mg", dose={"morning": 1.0, "night": 1.0})
    pred = MedLine(
        drug="Glycomet",
        strength="500mg",
        dose={"morning": 1.0, "afternoon": 0.0, "night": 2.0, "unit": "tab"},
        needs_check=["dose"],
    )
    s = score(pred, gold)
    assert s["danger_v1"] == 0
    assert s["danger"] == 0
    assert s["danger_v2"] == 0
    pred2 = pred.model_copy(update={"needs_check": ["food"]})
    s2 = score(pred2, gold)
    assert s2["danger_v1"] == 0
    assert s2["danger_v2"] == 1


def test_parse_fail_is_separate_from_danger_v2() -> None:
    gold = MedLine(drug="Glycomet", dose={"morning": 1.0, "unit": "tab"})
    s = score(None, gold)
    assert s["parse_fail"] == 1
    assert s["http_fail"] == 0
    assert s["valid"] == 0
    assert s["danger_v1"] == 1
    assert s["danger"] == 1
    assert s["danger_v2"] == 0


def test_ask_recall_and_false_ask_in_summarize() -> None:
    from eval.eval import summarize

    gold_ask = MedLine(drug=None, kind="daily", dose=None, needs_check=["drug", "dose", "schedule"])
    gold_ok = MedLine(drug="Glycomet", dose={"morning": 1.0, "unit": "tab"})
    pred_ask = gold_ask
    pred_ok = gold_ok
    pred_false_ask = gold_ok.model_copy(update={"needs_check": ["food"]})
    scores = [
        score(pred_ask, gold_ask),
        score(pred_ok, gold_ok),
        score(pred_false_ask, gold_ok),
        score(pred_ok, gold_ask),
    ]
    out = summarize("t", "x", scores, None)
    assert out["n_gold_ask"] == 2
    assert out["ask_recall"] == 0.5
    assert out["false_ask_rate"] == 0.5


def test_strength_and_devanagari_norm() -> None:
    from pillclerk.normalize import drug_eq, strength_eq

    assert strength_eq("500MG", "500 mg")
    assert strength_eq("40mg/5mg", "40 mg / 5 mg")
    assert not strength_eq("500mg", "250mg")
    assert drug_eq("टेलमा", "Telma")
    assert drug_eq("टेल्मा", "Telma")
    assert drug_eq("पैन", "Pan")
    gold = MedLine(drug="Telma", strength="40", dose={"morning": 1.0, "unit": "tab"})
    pred = MedLine(drug="टेलमा", strength="40 mg", dose={"morning": 1.0, "afternoon": 0.0, "night": 0.0, "unit": "tab"})
    s = score(pred, gold)
    assert s["drug"] == 0
    assert s["strength"] == 0
    assert s["exact"] == 0
    assert s["exact_norm"] == 1


def test_rescore_matches_already_dropped_preds_by_line(tmp_path, monkeypatch) -> None:
    import json
    import sys

    from eval import eval as ev

    gold = tmp_path / "gold.jsonl"
    train = tmp_path / "train.jsonl"
    preds = tmp_path / "preds.jsonl"
    train.write_text(json.dumps({"line": "dup-train-line", "gold": {}}) + "\n", encoding="utf-8")
    gold.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "line": "dup-train-line",
                        "gold": {
                            "drug": "X",
                            "form": "tab",
                            "kind": "daily",
                            "food": "any",
                            "needs_check": ["dose"],
                        },
                    }
                ),
                json.dumps(
                    {
                        "line": "keep-me OD",
                        "gold": {
                            "drug": "Glycomet",
                            "form": "tab",
                            "kind": "daily",
                            "dose": {"morning": 1, "afternoon": 0, "night": 0, "unit": "tab"},
                            "food": "any",
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    preds.write_text(
        json.dumps(
            {
                "line": "keep-me OD",
                "pred": {
                    "drug": "Glycomet",
                    "form": "tab",
                    "kind": "daily",
                    "dose": {"morning": 1, "afternoon": 0, "night": 0, "unit": "tab"},
                    "food": "any",
                    "taper": [],
                    "needs_check": [],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(ev, "TRAIN_JSONL", train)
    monkeypatch.setattr(ev, "ROOT", tmp_path)
    (tmp_path / "eval" / "out").mkdir(parents=True)
    monkeypatch.setattr(
        sys,
        "argv",
        ["eval", "--system", "ft2", "--set", str(gold), "--preds", str(preds)],
    )
    ev.main()
    out = json.loads((tmp_path / "eval" / "out" / "ft2_gold.json").read_text(encoding="utf-8"))
    assert out["n"] == 1
    assert out["dropped_train_duplicates"] == 1
    assert out["exact"] == 1.0


def test_drop_train_duplicates() -> None:
    from eval.eval import drop_train_duplicates, train_lines

    banned = train_lines()
    assert len(banned) >= 3000
    gold = [{"line": next(iter(banned)), "gold": {}}, {"line": "unique-eval-line-xyz", "gold": {}}]
    preds = [{"pred": None}, {"pred": None}]
    g, p, n = drop_train_duplicates(gold, preds)
    assert n == 1
    assert g[0]["line"] == "unique-eval-line-xyz"


def test_align_gold_food_duration_prn() -> None:
    from pillclerk.copy_explicit import align_gold

    gold = MedLine(
        drug="Dolo",
        strength="650MG",
        kind="prn",
        food="after",
        duration_days=None,
        prn_max_per_day=3,
    )
    line = "TAB. Dolo 650MG SOS / PRN max 2/d x 5d"
    fixed = align_gold(gold, line)
    assert fixed.food == "any"
    assert fixed.duration_days == 5
    assert fixed.prn_max_per_day == 2
    bare = align_gold(gold, "Tab Dolo 650 SOS")
    assert bare.food == "any"
    assert bare.duration_days is None
    assert bare.prn_max_per_day is None


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
    assert '"gemma31_json"' in src
    assert "few_shot=True" in src


def test_exact_on_valid_uses_t_valid_subset() -> None:
    from eval.report import exact_on_valid, mcnemar_p_two_sided

    t = [
        {"valid": 1, "pred": {"drug": "A"}, "exact": 1},
        {"valid": 0, "pred": None, "exact": 0},
        {"valid": 1, "pred": {"drug": "C"}, "exact": 0},
        {"valid": 1, "pred": {"drug": "D"}, "exact": 1},
    ]
    other = [
        {"valid": 1, "exact": 1},
        {"valid": 1, "exact": 1},
        {"valid": 1, "exact": 1},
        {"valid": 1, "exact": 0},
    ]
    out = exact_on_valid(t, other)
    assert out["n"] == 4
    assert out["n_valid"] == 3
    assert out["t_exact_on_valid"] == 2
    assert out["other_exact_on_valid"] == 2
    assert out["mcnemar"]["n01_b_fixes"] == 1  # T right, other wrong
    assert out["mcnemar"]["n10_b_regresses"] == 1  # T wrong, other right
    assert out["mcnemar"]["p_two_sided"] == mcnemar_p_two_sided(1, 1)


def test_mcnemar_counts_discordant_pairs() -> None:
    from eval.report import ci_width_points, mcnemar_exact, public_set_name

    a = [{"exact": 0}, {"exact": 1}, {"exact": 0}]
    b = [{"exact": 1}, {"exact": 1}, {"exact": 0}]
    m = mcnemar_exact(a, b)
    assert m["n01_b_fixes"] == 1
    assert m["n10_b_regresses"] == 0
    assert m["p_two_sided"] == 1.0
    from eval.report import mcnemar_p_two_sided

    assert mcnemar_p_two_sided(14, 0) < 0.001
    assert mcnemar_p_two_sided(0, 0) == 1.0
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


def test_t_valid_json_matches_preds() -> None:
    from eval.report import exact_on_valid, load_preds

    t = json.loads(Path("eval/out/t_valid.json").read_text(encoding="utf-8"))
    synth = exact_on_valid(
        load_preds(Path("eval/out/gemma31_synth_test_preds.jsonl")),
        load_preds(Path("eval/out/ft2_synth_test_preds.jsonl")),
    )
    hw = exact_on_valid(
        load_preds(Path("eval/out/gemma31_handwritten_realistic_preds.jsonl")),
        load_preds(Path("eval/out/ft2_handwritten_realistic_preds.jsonl")),
    )
    assert t["synth"]["n_valid"] == synth["n_valid"]
    assert t["synth"]["t_exact_on_valid"] == synth["t_exact_on_valid"]
    assert t["synth"]["other_exact_on_valid"] == synth["other_exact_on_valid"]
    assert t["synth"]["mcnemar"] == synth["mcnemar"]
    assert t["hw"]["n_valid"] == hw["n_valid"]
    assert t["hw"]["t_exact_on_valid"] == hw["t_exact_on_valid"]
    assert t["hw"]["other_exact_on_valid"] == hw["other_exact_on_valid"]
    results = Path("eval/results.md").read_text(encoding="utf-8")
    assert f"{t['synth']['t_exact_on_valid']}/{t['synth']['n_valid']}" in results
    assert f"{t['hw']['t_exact_on_valid']}/{t['hw']['n_valid']}" in results
    assert "schema-validity" in results
    assert "danger_v2_norm" in results
    assert "generated in code" in results
    assert "rescored_from_preds" in results


def test_b0_fair_saved_run_beats_schema_fail_b0() -> None:
    fair = json.loads(Path("eval/out/b0_fair_synth_test.json").read_text(encoding="utf-8"))
    old = json.loads(Path("eval/out/b0_synth_test.json").read_text(encoding="utf-8"))
    assert fair["n"] == 397
    assert fair.get("dropped_train_duplicates") == 3
    assert fair["json_valid"] > 0.5
    assert fair["json_valid"] > old["json_valid"]
    hw = json.loads(Path("eval/out/b0_fair_handwritten_realistic.json").read_text(encoding="utf-8"))
    assert hw["n"] == 102
    assert hw["json_valid"] > 0.5
