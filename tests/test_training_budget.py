import pytest

from train import sft


def test_training_plan_counts_tail_batch_and_validation_forward_charges():
    plan = sft.training_plan(17, 80, 3, 16, 0.44)
    assert plan["steps"] == 6
    assert plan["validation_calls"] == 1
    assert plan["compute_token_upper_bound"] == (17 * 3 + 64) * sft.MAXLEN
    with pytest.raises(ValueError):
        sft.training_plan(17, 80, 3, 0, 0.44)


def test_oversize_target_is_refused_on_both_tokenizer_paths():
    class Tokenizer:
        def __init__(self, legacy):
            self.legacy = legacy

        def apply_chat_template(self, messages, **kwargs):
            if self.legacy and "enable_thinking" in kwargs:
                raise TypeError("legacy tokenizer")
            return list(range(sft.MAXLEN + 1))

    for legacy in (False, True):
        with pytest.raises(ValueError, match="truncated JSON target"):
            sft.to_datum(Tokenizer(legacy), {"messages": [{"role": "user", "content": "Test only"},
                {"role": "assistant", "content": "{}"}]})
