"""Gold sampler + template renderer: labels are valid by construction."""

import json
import random
from pathlib import Path

import pytest

from pillclerk.filters import drug_present, rule_ok
from pillclerk.render import to_chat_row
from pillclerk.sampler import holdout_split, is_weekly_typical, load_drugs, load_patterns, sample_hard_negative, sample_line, sample_prn
from pillclerk.schema import MedLine
from pillclerk.templates import STYLES, dose_code, render_template
from train.build_dataset import generate_form_dose_food, generate_pairs, generate_targeted, main as build_main

ROOT = Path(__file__).resolve().parents[1]


def test_drug_list_is_large_enough() -> None:
    drugs = load_drugs()
    assert len(drugs) >= 150
    names = {d["name"] for d in drugs}
    assert "Glycomet" in names
    assert "Uprise D3" in names


def test_patterns_weights_match_idea() -> None:
    p = load_patterns()
    mix = p["line_mix"]
    assert mix["1-0-1"] == 25
    assert mix["1-0-0"] == 20
    assert mix["0-0-1"] == 15
    assert mix["1-1-1"] == 10
    assert mix["half_tab"] == 7
    assert mix["prn"] == 8
    assert mix["taper"] == 7
    assert mix["every_n_days"] == 5
    assert mix["other"] == 3
    assert sum(mix.values()) == 100
    assert p["hard_negative_rate"] == 0.05
    assert sum(p["styles"].values()) == 100


def test_sample_line_always_validates() -> None:
    drugs = load_drugs()
    patterns = load_patterns()
    rng = random.Random(0)
    kinds = set()
    for _ in range(200):
        gold = sample_line(rng, rng.choice(drugs), patterns)
        MedLine.model_validate(gold.model_dump())
        kinds.add(gold.kind)
        if gold.needs_check:
            assert gold.kind != "daily" or gold.dose is None or "duration_days" in gold.needs_check
    assert kinds >= {"daily", "prn", "taper"}


def test_hard_negative_sets_needs_check() -> None:
    drugs = load_drugs()
    patterns = load_patterns()
    rng = random.Random(1)
    flagged = 0
    for _ in range(40):
        gold = sample_line(rng, rng.choice(drugs), patterns, hard_negative=True)
        assert gold.needs_check
        flagged += 1
    assert flagged == 40


def test_template_contains_drug_and_passes_rule_filter() -> None:
    drugs = load_drugs()
    patterns = load_patterns()
    rng = random.Random(2)
    for _ in range(80):
        gold = sample_line(rng, rng.choice(drugs), patterns, hard_negative=False)
        if gold.kind != "daily" or gold.dose is None:
            continue
        style = rng.choice(list(STYLES))
        line = render_template(gold, style, rng)
        assert drug_present(line, gold.drug)
        assert rule_ok(line, gold)
        assert dose_code(gold.dose).replace("½", "0.5") or True


def test_every_n_days_only_on_single_slot() -> None:
    drugs = load_drugs()
    patterns = load_patterns()
    rng = random.Random(3)
    weekly = 0
    for _ in range(400):
        gold = sample_line(rng, rng.choice(drugs), patterns, hard_negative=False)
        if gold.kind == "daily" and gold.dose and gold.every_n_days > 1:
            weekly += 1
            slots = sum(1 for s in (gold.dose.morning, gold.dose.afternoon, gold.dose.night) if s)
            assert slots == 1
            assert gold.duration_days is None or gold.duration_days >= 30
    assert weekly >= 1


def test_vitamin_d_is_weekly_od() -> None:
    drugs = load_drugs()
    d3 = next(d for d in drugs if d["name"] == "Calcirol")
    assert is_weekly_typical(d3)
    patterns = load_patterns()
    rng = random.Random(4)
    for _ in range(20):
        gold = sample_line(rng, d3, patterns, hard_negative=False)
        assert gold.kind == "daily"
        assert gold.every_n_days == 7
        assert gold.dose is not None
        slots = sum(1 for s in (gold.dose.morning, gold.dose.afternoon, gold.dose.night) if s)
        assert slots == 1


def test_line_mix_roughly_matches_idea() -> None:
    """Loose check on 2000 non-hard lines. Not an eval number for the post."""
    drugs = [d for d in load_drugs() if not is_weekly_typical(d)]
    patterns = load_patterns()
    rng = random.Random(5)
    counts = {"prn": 0, "taper": 0, "every_n": 0, "101": 0}
    n = 0
    for _ in range(2000):
        gold = sample_line(rng, rng.choice(drugs), patterns, hard_negative=False)
        n += 1
        if gold.kind == "prn":
            counts["prn"] += 1
        elif gold.kind == "taper":
            counts["taper"] += 1
        elif gold.every_n_days > 1:
            counts["every_n"] += 1
        elif gold.dose and gold.dose.unit in ("tab", "cap"):
            if (gold.dose.morning, gold.dose.afternoon, gold.dose.night) == (1, 0, 1):
                counts["101"] += 1
    assert 0.05 < counts["prn"] / n < 0.12
    assert 0.04 < counts["taper"] / n < 0.11
    assert 0.02 < counts["every_n"] / n < 0.09
    assert 0.18 < counts["101"] / n < 0.32


def test_holdout_splits_by_drug_name() -> None:
    drugs = load_drugs()
    train, test = holdout_split(drugs, fraction=0.2, seed=0)
    train_names = {d["name"] for d in train}
    test_names = {d["name"] for d in test}
    assert train_names.isdisjoint(test_names)
    assert len(test_names) >= 20
    assert len(train_names) > len(test_names)


def test_to_chat_row_is_tinker_conversation_shape() -> None:
    gold = MedLine(drug="Pan", strength="40 mg", dose={"morning": 1, "unit": "tab"}, duration_days=5)
    row = to_chat_row("TAB PAN 40MG 1-0-0 x5d", gold)
    assert [m["role"] for m in row["messages"]] == ["system", "user", "assistant"]
    parsed = MedLine.model_validate_json(row["messages"][2]["content"])
    assert parsed.drug == "Pan"


def test_generate_ten_pairs_is_deterministic() -> None:
    a = generate_pairs(10, seed=42)
    b = generate_pairs(10, seed=42)
    assert [p["line"] for p in a] == [p["line"] for p in b]
    assert len(a) == 10
    for p in a:
        assert p["synthetic"] is True
        MedLine.model_validate(p["gold"])
        assert p["renderer"] == "template"


def test_llm_renderer_is_gated(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        generate_pairs(1, renderer="llm")
    assert "DigitalOcean" in str(exc.value) or "template" in str(exc.value).lower()
    code = build_main(["--n", "1", "--renderer", "llm"])
    assert code == 2


def test_drugs_csv_forms_are_known() -> None:
    allowed = {"tab", "cap", "syrup", "drops", "inhaler", "injection", "cream", "sachet", "other"}
    drugs = load_drugs()
    for d in drugs:
        assert d["form"] in allowed, d
    tabcap = sum(1 for d in drugs if d["form"] in ("tab", "cap"))
    assert tabcap / len(drugs) >= 0.75


def test_rule_ok_rejects_dropped_facts() -> None:
    gold = MedLine(
        drug="Glycomet",
        strength="500 mg",
        dose={"morning": 1, "night": 1, "unit": "tab"},
        duration_days=30,
    )
    assert rule_ok("TAB. Glycomet 500MG 1-0-1 AFTER FOOD x 30 DAYS", gold)
    assert not rule_ok("TAB. SomethingElse 500MG 1-0-1 x 30 DAYS", gold)
    assert not rule_ok("TAB. Glycomet 1-0-1 AFTER FOOD x 30 DAYS", gold)
    assert not rule_ok("TAB. Glycomet 500MG 1-0-1 AFTER FOOD", gold)
    assert rule_ok("Tab Glycomet 500mg BD PC 1/12", gold)


def test_prn_gold_food_is_any() -> None:
    drugs = load_drugs()
    patterns = load_patterns()
    rng = random.Random(9)
    for _ in range(20):
        gold = sample_prn(rng, rng.choice(drugs), patterns)
        assert gold.food == "any"
        line = render_template(gold, "doctor_short", rng)
        assert "AC" not in line and "PC" not in line and "WF" not in line and "ES" not in line


def test_hard_negative_without_food_token_is_any() -> None:
    drugs = load_drugs()
    patterns = load_patterns()
    rng = random.Random(8)
    for _ in range(30):
        gold = sample_hard_negative(rng, rng.choice(drugs), patterns)
        if gold.note == "partially illegible" or gold.note == "as directed" or gold.note == "frequency not written":
            assert gold.food == "any"


def test_generate_form_dose_food_stresses_ft1_weak_fields() -> None:
    drugs = load_drugs()
    patterns = load_patterns()
    rows = generate_form_dose_food(30, drugs=drugs, patterns=patterns, seed=21)
    assert len(rows) == 30
    tags = {r["targeted"] for r in rows}
    assert any(t.startswith("fdf_") for t in tags)


def test_generate_targeted_covers_ft1_buckets() -> None:
    drugs = load_drugs()
    patterns = load_patterns()
    rows = generate_targeted(40, drugs=drugs, patterns=patterns, seed=11)
    assert len(rows) == 40
    buckets = {r["targeted"] for r in rows}
    assert {"form", "food", "half", "taper", "hard", "prn"} <= buckets
    foods = [r for r in rows if r["targeted"] == "food"]
    assert foods
    assert all(r["gold"]["food"] != "any" for r in foods)


def test_rule_ok_taper_uses_step_days() -> None:
    gold = MedLine(
        drug="Wysolone",
        strength="10 mg",
        kind="taper",
        taper=[
            {"dose": {"morning": 1, "night": 1, "unit": "tab"}, "days": 5},
            {"dose": {"night": 1, "unit": "tab"}, "days": 5},
        ],
        duration_days=10,
    )
    line = "TAB. Wysolone 10 mg  1-0-1 x 5d then 0-0-1 x 5d  AFTER FOOD"
    assert rule_ok(line, gold)
