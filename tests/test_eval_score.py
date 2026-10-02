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
