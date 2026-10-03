import copy

import pytest

from pillclerk.render import to_chat_row
from pillclerk.schema import Dose, MedLine, TaperStep
from train.review_candidate import audit, correct


def row(line, med):
    return {"line": line, "gold": med.model_dump(), "synthetic": True, **to_chat_row(line, med)}


def test_duration_correction_only_adds_ask_and_keeps_clinical_values():
    med = MedLine(drug="TestOnly", strength="5 mg", dose=Dose(morning=0.5))
    rows = [row("Tab TestOnly 5 mg half tablet morning", med)]
    original = copy.deepcopy(rows)
    out, changes = correct(rows)
    assert rows == original
    assert out[0]["gold"]["needs_check"] == ["duration_days"]
    assert {k: v for k, v in out[0]["gold"].items() if k != "needs_check"} == med.model_dump(exclude={"needs_check"})
    assert out[0]["line"] == rows[0]["line"]
    assert changes[0]["source_index"] == 0
    assert not correct(out)[1]


def test_written_duration_continuation_and_taper_are_preserved():
    daily = MedLine(drug="TestOnly", dose=Dose(morning=1))
    taper = MedLine(drug="TestOnly", kind="taper", taper=[TaperStep(dose=Dose(morning=1), days=3)])
    rows = [row("Tab TestOnly 1-0-0 CONTINUE", daily),
            row("Tab TestOnly 1-0-0 x5d", daily.model_copy(update={"duration_days": 5})),
            row("Tab TestOnly 1-0-0 x3d then stop", taper)]
    out, changes = correct(rows)
    assert out == rows and not changes


def test_review_refuses_public_gold_and_sample_is_reproducible():
    med = MedLine(drug="TestOnly", dose=Dose(morning=1), duration_days=5)
    rows = [row(f"Tab TestOnly {i} mg 1-0-0 x5d", med) for i in range(8)]
    first = audit(rows, 3, 100)
    assert first == audit(rows, 3, 100)
    assert len(first["sample_indexes"]) == 3
    assert first["coverage"]["kind:daily"] == 8
    with pytest.raises(ValueError, match="synthetic"):
        correct([{**rows[0], "synthetic": False}])
