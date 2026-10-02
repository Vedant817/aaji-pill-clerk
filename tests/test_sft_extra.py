import json
from pathlib import Path

from train.sft import load_train_rows


def test_load_train_rows_concatenates_extra(tmp_path: Path) -> None:
    train = tmp_path / "train.jsonl"
    extra = tmp_path / "extra.jsonl"
    train.write_text(
        json.dumps({"line": "a", "messages": []}) + "\n" + json.dumps({"line": "b", "messages": []}) + "\n",
        encoding="utf-8",
    )
    extra.write_text(json.dumps({"line": "c", "messages": []}) + "\n", encoding="utf-8")
    rows = load_train_rows(train, [extra])
    assert [r["line"] for r in rows] == ["a", "b", "c"]
    limited = load_train_rows(train, [extra], limit=2)
    assert [r["line"] for r in limited] == ["a", "b"]
