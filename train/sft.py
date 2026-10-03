"""Tinker LoRA SFT on Qwen/Qwen3-8B. Cookbook-free so it runs on Windows.

Uses TINKER_API_KEY. Spends Tinker credits (~$0.66 IDEA.md budget for 2k rows).
Do not start until data/synth/train.jsonl exists.
"""

from __future__ import annotations

import json
import hashlib
import random
import time
from pathlib import Path

import tinker

from pillclerk.config import BASE_MODEL, ROOT, apply_tinker_checkpoint, load_dotenv, require_env
from pillclerk.infer import as_token_ids

load_dotenv()

RANK, BATCH, EPOCHS, MAXLEN = 32, 16, 3, 1024
# Smaller batch than IDEA's 64 so Windows + hosted API is less likely to time out.
LR = 4e-4  # cookbook get_lr(Qwen3-8B) is typically this order; confirm in run logs


def _load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_train_rows(train_path: Path, extra_paths: list[Path] | None = None, limit: int = 0) -> list[dict]:
    """Load train jsonl plus optional extra jsonl files. Limit applies after concat."""
    if not train_path.is_file():
        raise FileNotFoundError(train_path)
    rows = _load(train_path)
    for extra in extra_paths or []:
        if not extra.is_file():
            raise FileNotFoundError(extra)
        rows.extend(_load(extra))
    if limit:
        rows = rows[:limit]
    return rows


def validate_split(train_rows: list[dict], validation_rows: list[dict], eval_paths: list[Path]) -> dict:
    """Fail before creating a paid client when evaluation text leaks into training."""
    from pillclerk.filters import normalised_text

    def lines(rows):
        return {normalised_text(r["line"]) for r in rows}

    train = lines(train_rows)
    overlaps = {"validation": len(train & lines(validation_rows))}
    for path in eval_paths:
        if path.is_file():
            overlaps[str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name] = len(train & lines(_load(path)))
    if any(overlaps.values()):
        raise ValueError(f"Training/evaluation leakage: {overlaps}. Create a clean candidate split; do not rewrite published gold.")
    return overlaps


def _conversation_ids(tokenizer, messages: list[dict]) -> tuple[list[int], list[int]]:
    prompt = tokenizer.apply_chat_template(
        messages[:-1],
        tokenize=True,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    full = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=False,
        enable_thinking=False,
    )
    return as_token_ids(prompt), as_token_ids(full)


def to_datum(tokenizer, row: dict) -> tinker.Datum:
    prompt, full = _conversation_ids(tokenizer, row["messages"])
    if len(full) > MAXLEN:
        full = full[:MAXLEN]
        prompt = prompt[: min(len(prompt), MAXLEN - 1)]
    if len(full) < 2:
        raise ValueError("conversation too short")
    n_prefix = max(0, len(prompt) - 1)
    n_targets = len(full) - 1
    weights = [0.0] * n_prefix + [1.0] * max(0, n_targets - n_prefix)
    weights = weights[:n_targets]
    if len(weights) < n_targets:
        weights += [0.0] * (n_targets - len(weights))
    return tinker.Datum(
        model_input=tinker.ModelInput.from_ints(full[:-1]),
        loss_fn_inputs={
            "target_tokens": tinker.TensorData(data=full[1:], dtype="int64"),
            "weights": tinker.TensorData(data=weights, dtype="float32"),
        },
    )


def mean_nll(loss_fn_outputs, batch: list[tinker.Datum]) -> float:
    total = 0.0
    mass = 0.0
    for out, datum in zip(loss_fn_outputs, batch, strict=False):
        logprobs = out["logprobs"].tolist() if hasattr(out["logprobs"], "tolist") else out["logprobs"]
        weights = datum.loss_fn_inputs["weights"].tolist()
        for lp, w in zip(logprobs, weights, strict=False):
            total += -float(lp) * float(w)
            mass += float(w)
    return total / mass if mass else float("nan")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="cap train rows (50 = smoke)")
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--name", default="pillclerk-v1")
    ap.add_argument("--train", default="", help="override train jsonl path")
    ap.add_argument("--val", default="", help="override validation jsonl path for a frozen candidate")
    ap.add_argument(
        "--extra",
        action="append",
        default=[],
        help="extra jsonl mixed after --train (repeatable). Does not rewrite train.jsonl",
    )
    ap.add_argument(
        "--apply-env",
        action="store_true",
        help="write sampler path to .env (v1/v2 always do; v3 only with this flag)",
    )
    ap.add_argument("--log", default="", help="append train_nll lines to this path")
    ap.add_argument("--check-data", action="store_true", help="check split leakage offline and exit without provider calls")
    args = ap.parse_args()

    train_path = Path(args.train) if args.train else ROOT / "data" / "synth" / "train.jsonl"
    val_path = Path(args.val) if args.val else ROOT / "data" / "synth" / "val.jsonl"
    extra_paths = [Path(p) for p in args.extra]
    if not train_path.is_file():
        raise SystemExit("missing data/synth/train.jsonl — run: uv run python -m train.build_dataset --split")

    train_rows = load_train_rows(train_path, extra_paths, limit=args.limit)
    val_rows = _load(val_path)
    validate_split(train_rows, val_rows, [ROOT / "data/synth/synth_test.jsonl",
                  ROOT / "data/heldout/handwritten_realistic.jsonl", ROOT / "data/public_labels/hmr100_gold.jsonl",
                  ROOT / "data/public_labels/bd200_gold.jsonl",
                  *sorted((ROOT / "data/acceptance").glob("*/gold.jsonl"))])
    if args.check_data:
        print("Training split passed offline checks; no provider calls made.")
        return
    require_env("TINKER_API_KEY")
    print(f"train_rows {len(train_rows)} extras {[str(p) for p in extra_paths]}", flush=True)
    service = tinker.ServiceClient()
    tc = service.create_lora_training_client(base_model=BASE_MODEL, rank=RANK)
    tokenizer = tc.get_tokenizer()

    def safe_datum(row: dict) -> tinker.Datum | None:
        try:
            return to_datum(tokenizer, row)
        except TypeError:
            prompt = as_token_ids(
                tokenizer.apply_chat_template(
                    row["messages"][:-1], tokenize=True, add_generation_prompt=True
                )
            )
            full = as_token_ids(
                tokenizer.apply_chat_template(row["messages"], tokenize=True, add_generation_prompt=False)
            )
            n_prefix = max(0, len(prompt) - 1)
            n_targets = len(full) - 1
            weights = ([0.0] * n_prefix + [1.0] * max(0, n_targets - n_prefix))[:n_targets]
            return tinker.Datum(
                model_input=tinker.ModelInput.from_ints(full[:-1]),
                loss_fn_inputs={
                    "target_tokens": tinker.TensorData(data=full[1:], dtype="int64"),
                    "weights": tinker.TensorData(data=weights, dtype="float32"),
                },
            )

    train_data = [d for d in (safe_datum(r) for r in train_rows) if d]
    val_batch = [d for d in (safe_datum(r) for r in val_rows[:64]) if d]
    steps_per_epoch = max(1, len(train_data) // args.batch)
    total = steps_per_epoch * args.epochs
    step = 0
    for epoch in range(args.epochs):
        random.Random(epoch).shuffle(train_data)
        for b in range(steps_per_epoch):
            t0 = time.time()
            batch = train_data[b * args.batch : (b + 1) * args.batch]
            lr = LR * max(0.0, 1 - step / total)
            fb = tc.forward_backward(batch, loss_fn="cross_entropy")
            op = tc.optim_step(tinker.AdamParams(learning_rate=lr, beta1=0.9, beta2=0.95, eps=1e-8))
            out = fb.result()
            op.result()
            nll = mean_nll(out.loss_fn_outputs, batch)
            msg = f"ep {epoch} step {step}/{total} lr {lr:.2e} train_nll {nll:.4f} {time.time() - t0:.1f}s"
            if step % 10 == 0 and val_batch:
                v = tc.forward(val_batch, loss_fn="cross_entropy").result()
                vnll = mean_nll(v.loss_fn_outputs, val_batch)
                msg += f" val_nll {vnll:.4f}"
            print(msg, flush=True)
            if args.log:
                log_path = Path(args.log)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                with log_path.open("a", encoding="utf-8") as fh:
                    fh.write(msg + "\n")
            step += 1

    state = tc.save_state(args.name).result().path
    sampler = tc.save_weights_for_sampler(args.name).result().path
    if args.name in ("pillclerk-v1", "v1"):
        ck_name = "checkpoint_v1.json"
    elif args.name in ("pillclerk-v2", "v2"):
        ck_name = "checkpoint_v2.json"
    elif args.name in ("pillclerk-v3", "v3"):
        ck_name = "checkpoint_v3.json"
    else:
        ck_name = f"checkpoint_{args.name}.json"
    ck = ROOT / "train" / ck_name
    ck.write_text(
        json.dumps(
            {
                "state": state,
                "sampler": sampler,
                "model": BASE_MODEL,
                "name": args.name,
                "n_train": len(train_rows),
                "extras": [str(p) for p in extra_paths],
                "data_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in [train_path, val_path, *extra_paths]},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    if args.apply_env or args.name in ("pillclerk-v1", "v1", "pillclerk-v2", "v2"):
        apply_tinker_checkpoint(ck)
    print("saved", sampler)
    print("wrote", ck)


if __name__ == "__main__":
    main()
