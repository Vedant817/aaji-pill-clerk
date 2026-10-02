from collections import Counter

from eval.overlap import vs_eval
from pillclerk.sampler import load_drugs, load_patterns
from train.build_dataset import eval_drug_names, generate_ft3_danger


def test_ft3_danger_drugs_not_in_eval_sets() -> None:
    rows = generate_ft3_danger(48, drugs=load_drugs(), patterns=load_patterns(), seed=2026)
    banned = eval_drug_names()
    drugs = {(r.get("gold") or {}).get("drug") for r in rows}
    assert drugs
    assert all(d and d.lower() not in banned for d in drugs)
    tags = Counter(r.get("targeted") for r in rows)
    assert tags["ft3_insulin"] >= 1
    assert tags["ft3_syrup"] >= 1
    assert tags["ft3_syrup_ask"] >= 1
    assert tags["ft3_hi_slots"] >= 1
    assert tags["ft3_combo"] >= 1
    insulin = [r for r in rows if r.get("targeted") == "ft3_insulin"]
    gold = insulin[0]["gold"]
    assert gold["strength"] is None
    assert gold["form"] == "injection"
    assert gold["dose"]["unit"] == "unit"
    ask = next(r for r in rows if r.get("targeted") == "ft3_syrup_ask")
    assert "dose" in ask["gold"]["needs_check"]
    assert ask["gold"]["dose"] is None
    overlap = vs_eval([r["line"] for r in rows], extra_name="ft3_test")
    assert overlap["any_exact_eval"] is False
    assert overlap["any_near_eval"] is False
