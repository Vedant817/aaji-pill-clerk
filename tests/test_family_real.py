from collections import Counter
from pathlib import Path

from pillclerk.schema import MedLine
from eval.family_real import HELD, rows, SPECS


def test_real_set_meets_idea_size() -> None:
    data = rows()
    assert len(data) >= 80
    sources = {r["source"] for r in data}
    assert len(sources) >= 15
    assert sum(1 for r in data if r["source"].startswith("wa")) >= 20
    assert all(r["synthetic"] is False for r in data)


def test_real_gold_validates_and_matches_written_food() -> None:
    foods = Counter()
    forms = Counter()
    kinds = Counter()
    ask = 0
    for r in rows():
        gold = MedLine.model_validate(r["gold"])
        foods[gold.food] += 1
        forms[gold.form] += 1
        kinds[gold.kind] += 1
        if gold.needs_check:
            ask += 1
    assert foods["after"] >= 10
    assert foods["before"] >= 5
    assert foods["empty_stomach"] >= 4
    assert forms["cap"] >= 3
    assert forms["syrup"] >= 2
    assert forms["inhaler"] >= 2
    assert forms["injection"] >= 2
    assert kinds["prn"] >= 3
    assert kinds["taper"] >= 1
    assert ask >= 4


def test_specs_roundtrip() -> None:
    assert len(SPECS) == len(rows())


def test_heldout_file_is_handwritten_realistic_not_real() -> None:
    assert HELD.name == "handwritten_realistic.jsonl"
    assert HELD.is_file()
    assert "real_style" not in HELD.name
    text = HELD.read_text(encoding="utf-8")
    assert text.count("\n") >= 80
    assert Path("eval/results.md").read_text(encoding="utf-8").count("Hand-written realistic") >= 1
