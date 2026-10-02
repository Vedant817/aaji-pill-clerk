from pillclerk.schema import MedLine
from pillclerk.validate import all_confirmed, extra_rules


def test_missing_drug_is_flagged() -> None:
    med = extra_rules(MedLine(drug=None, kind="daily", dose=None, needs_check=["dose"]))
    assert "drug" in med.needs_check


def test_all_confirmed() -> None:
    ok = MedLine(drug="Pan", dose={"morning": 1, "unit": "tab"}, duration_days=5)
    ask = extra_rules(MedLine(drug=None, kind="daily", dose=None, needs_check=["dose"]))
    assert all_confirmed([ok])
    assert not all_confirmed([ok, ask])
