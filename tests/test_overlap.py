from eval.overlap import NEAR, compare, load_lines, run
from pathlib import Path


def test_compare_exact_and_near() -> None:
    a = ["Tab Glycomet 500 1-0-1", "something unique aaa"]
    b = ["Tab Glycomet 500 1-0-1", "something unique aab"]
    out = compare("a", a, "b", b)
    assert out["exact"] == 1
    assert out["near_ratio_gt_90"] >= 1
    assert NEAR == 90


def test_overlap_json_lists_train_synth_dups() -> None:
    out = run()
    assert out["exact_train_synth_test"] == 3
    assert Path("eval/out/overlap.json").is_file()
    train = load_lines(Path("data/synth/train.jsonl"))
    test = load_lines(Path("data/synth/synth_test.jsonl"))
    assert len(train) == 3096
    assert len(test) == 400
