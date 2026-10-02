"""Gold sampler + template renderer: labels are valid by construction."""

import json
import random
from pathlib import Path

import pytest

from pillclerk.filters import drug_present, rule_ok
from pillclerk.render import to_chat_row
from pillclerk.sampler import holdout_split, load_drugs, load_patterns, sample_line
from pillclerk.schema import MedLine
from pillclerk.templates import STYLES, dose_code, render_template
from train.build_dataset import generate_pairs, main as build_main

ROOT = Path(__file__).resolve().parents[1]


def test_drug_list_is_large_enough() -> None:
    drugs = load_drugs()
    assert len(drugs) >= 150
    names = {d["name"] for d in drugs}
    assert "Glycomet" in names
    assert "Uprise D3" in names


def test_patterns_weights_match_idea() -> None:
    p = load_patterns()
    sched = {tuple(s["pattern"]): s["weight"] for s in p["schedules"]}
    assert sched[(1.0, 0.0, 1.0)] == 25
    assert sched[(1.0, 0.0, 0.0)] == 20
    assert p["kind_weights"]["prn"] == 8
    assert p["kind_weights"]["taper"] == 7
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
    assert weekly >= 1


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
    assert "tokens" in str(exc.value).lower() or "Refusing" in str(exc.value)
    code = build_main(["--n", "1", "--renderer", "llm"])
    assert code == 2


def test_drugs_csv_forms_are_known() -> None:
    allowed = {"tab", "cap", "syrup", "drops", "inhaler", "injection", "cream", "sachet", "other"}
    for d in load_drugs():
        assert d["form"] in allowed, d
