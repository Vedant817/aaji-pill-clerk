import copy
import hashlib
import json

import pytest

from pillclerk.render import to_chat_row
from pillclerk.schema import Dose, MedLine
from train.prepare_candidate import clean_rows, jsonl, prepare, write_frozen


def row(line, drug="SyntheticDrug"):
    gold = MedLine(drug=drug, dose=Dose(morning=1), duration_days=5)
    return {**to_chat_row(line, gold), "line": line, "gold": gold.model_dump(), "synthetic": True}


def test_cleaner_quarantines_conflicts_and_overlaps():
    rows = [row("duplicate."), row(" DUPLICATE "), row("conflict", "A"),
            row("conflict", "B"), row("held out"), row("kept")]
    kept, rejected = clean_rows(rows, {"held out"})
    assert [r["line"] for r in kept] == ["duplicate.", "kept"]
    assert [r["reason"] for r in rejected] == ["internal_duplicate",
        "conflicting_duplicate_labels", "conflicting_duplicate_labels", "held_out_overlap"]


def test_cleaner_refuses_real_and_quarantines_misaligned_targets():
    real = {**row("real"), "synthetic": False}
    with pytest.raises(ValueError, match="synthetic"):
        clean_rows([real], set())
    bad = copy.deepcopy(row("mismatch"))
    bad["gold"]["drug"] = "Other"
    kept, rejected = clean_rows([bad], set())
    assert not kept and rejected[0]["reason"] == "invalid_or_misaligned_target"


def test_prepare_preserves_sources_and_freezes_hashed_artifacts(tmp_path):
    train, val, held = [tmp_path / n for n in ("source.jsonl", "validation.jsonl", "held.jsonl")]
    train.write_text(jsonl([row("training"), row("validation"), row("test")]), encoding="utf-8")
    val.write_text(jsonl([row("validation")]), encoding="utf-8")
    held.write_text(jsonl([row("test")]), encoding="utf-8")
    original = {p: p.read_bytes() for p in (train, val, held)}
    output = tmp_path / "candidate"
    report = prepare(train, val, [held], output)
    assert report["train_rows"] == 1 and report["validation_rows"] == 1
    assert not any(report["overlap"].values())
    for name, meta in report["outputs"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == meta["sha256"]
    assert prepare(train, val, [held], output) == report
    assert all(p.read_bytes() == data for p, data in original.items())
    train.write_text(jsonl([row("changed")]), encoding="utf-8")
    with pytest.raises(FileExistsError):
        prepare(train, val, [held], output)
    assert json.loads((output / "train.jsonl").read_text(encoding="utf-8"))["line"] == "training"


def test_prepare_refuses_source_overwrite(tmp_path):
    train, val, held = [tmp_path / n for n in ("train.jsonl", "val.jsonl", "held.jsonl")]
    for p in (train, val, held):
        p.write_text(jsonl([row(p.name)]), encoding="utf-8")
    with pytest.raises(ValueError, match="overwrite"):
        prepare(train, val, [held], tmp_path)


def test_frozen_file_is_idempotent_and_refuses_replacement(tmp_path):
    path = tmp_path / "frozen"
    write_frozen(path, "one\n")
    write_frozen(path, "one\n")
    with pytest.raises(FileExistsError):
        write_frozen(path, "two\n")
