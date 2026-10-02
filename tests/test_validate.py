from pillclerk.schema import Dose, MedLine
from pillclerk.validate import all_confirmed, extra_rules, schedule_conflicts


def test_missing_drug_is_flagged() -> None:
    med = extra_rules(MedLine(drug=None, kind="daily", dose=None, needs_check=["dose"]))
    assert "drug" in med.needs_check


def test_all_confirmed() -> None:
    ok = MedLine(drug="Pan", dose={"morning": 1, "unit": "tab"}, duration_days=5)
    ask = extra_rules(MedLine(drug=None, kind="daily", dose=None, needs_check=["dose"]))
    assert all_confirmed([ok])
    assert not all_confirmed([ok, ask])


def test_schedule_conflicts_by_kind() -> None:
    daily = MedLine(drug="Dolo", dose=Dose(morning=1, unit="tab"), duration_days=3)
    prn = MedLine(drug="Dolo", kind="prn", prn_max_per_day=3)
    found = schedule_conflicts([daily, prn])
    assert len(found) == 1
