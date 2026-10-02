"""Usage: uv run python -m eval.eval --system b0 --set data/synth/synth_test.jsonl

Results stay TODO until this script is actually run. Do not invent numbers.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median

from pillclerk.normalize import drug_eq, strength_eq
from pillclerk.schema import MedLine

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "drug",
    "strength",
    "form",
    "kind",
    "dose",
    "every_n_days",
    "taper",
    "food",
    "duration_days",
    "prn_max_per_day",
]
DANGER_V1 = ["dose", "taper", "duration_days", "every_n_days", "kind"]
DANGER_V2 = ["drug", "strength", "dose", "taper", "duration_days", "every_n_days", "kind"]
# schema needs_check uses "schedule" for kind / taper / every_n_days
NEEDS_FOR = {
    "drug": "drug",
    "strength": "strength",
    "dose": "dose",
    "duration_days": "duration_days",
    "taper": "schedule",
    "every_n_days": "schedule",
    "kind": "schedule",
}
DANGER = DANGER_V1  # alias kept for older tests
TRAIN_JSONL = ROOT / "data" / "synth" / "train.jsonl"


def norm(v):
    return v.lower().replace(" ", "").replace(".", "") if isinstance(v, str) else v


def canon(v):
    """0 and 0.0 compare equal; nested Dose/taper dicts are compared by value."""
    if v is None:
        return None
    if hasattr(v, "model_dump"):
        return canon(v.model_dump())
    if isinstance(v, dict):
        return {k: canon(x) for k, x in v.items()}
    if isinstance(v, list):
        return [canon(x) for x in v]
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        return norm(v)
    return v


def field_eq(p: MedLine, g: MedLine, f: str, *, normalize: bool = False) -> bool:
    pv, gv = getattr(p, f), getattr(g, f)
    if normalize and f == "strength":
        return strength_eq(pv, gv)
    if normalize and f == "drug":
        return drug_eq(pv, gv)
    return canon(pv) == canon(gv)


def train_lines() -> set[str]:
    if not TRAIN_JSONL.is_file():
        return set()
    return {
        json.loads(l)["line"]
        for l in TRAIN_JSONL.read_text(encoding="utf-8").splitlines()
        if l.strip()
    }


def drop_train_duplicates(gold_rows: list[dict], pred_rows: list[dict] | None = None) -> tuple[list[dict], list[dict] | None, int]:
    """Drop exact train/eval line duplicates from scoring (3 synth_test ASK stubs)."""
    banned = train_lines()
    keep = [i for i, r in enumerate(gold_rows) if r.get("line") not in banned]
    dropped = len(gold_rows) - len(keep)
    gold_kept = [gold_rows[i] for i in keep]
    pred_kept = [pred_rows[i] for i in keep] if pred_rows is not None else None
    return gold_kept, pred_kept, dropped


def score(pred: MedLine | None, gold: MedLine) -> dict:
    gold_ask = int(bool(gold.needs_check))
    if pred is None:
        return {
            "valid": 0,
            "parse_fail": 1,
            "exact": 0,
            "exact_norm": 0,
            "danger": 1,
            "danger_v1": 1,
            "danger_v2": 0,
            "ask_gold": gold_ask,
            "ask_pred": 0,
            **{f: 0 for f in FIELDS},
        }
    fs = {f: int(field_eq(pred, gold, f, normalize=False)) for f in FIELDS}
    fs_norm = {f: int(field_eq(pred, gold, f, normalize=True)) for f in FIELDS}
    flagged = set(pred.needs_check or [])
    danger_v1 = int(any(not fs[f] for f in DANGER_V1) and not flagged)
    danger_v2 = int(
        any(not fs[f] and NEEDS_FOR[f] not in flagged for f in DANGER_V2)
    )
    return {
        "valid": 1,
        "parse_fail": 0,
        "exact": int(all(fs.values())),
        "exact_norm": int(all(fs_norm.values())),
        "danger": danger_v1,
        "danger_v1": danger_v1,
        "danger_v2": danger_v2,
        "ask_gold": gold_ask,
        "ask_pred": int(bool(flagged)),
        **fs,
    }


def bootstrap_ci(xs, n=1000, seed=0):
    rng, k = random.Random(seed), len(xs)
    means = sorted(sum(rng.choices(xs, k=k)) / k for _ in range(n))
    return means[int(0.025 * n)], means[int(0.975 * n)]


def get_parser(system: str, set_path: str = ""):
    from pillclerk import infer

    ck = lambda v: json.loads((ROOT / "train" / f"checkpoint_{v}.json").read_text())["sampler"]
    return {
        "b0": lambda: infer.make_tinker_parser(None),
        "b0_fair": lambda: infer.make_tinker_parser(None, few_shot=True),
        "ft1": lambda: infer.make_tinker_parser(ck("v1")),
        "ft2": lambda: infer.make_tinker_parser(ck("v2")),
        "ft3": lambda: infer.make_tinker_parser(ck("v3")),
        "gemma31": lambda: infer.make_gemini_parser(set_path),
    }[system]()


def summarize(system: str, set_path: str, scores: list[dict], lat: list[float] | None) -> dict:
    mean = lambda k: sum(s[k] for s in scores) / len(scores)
    gold_ask = [s for s in scores if s.get("ask_gold")]
    gold_clear = [s for s in scores if not s.get("ask_gold")]
    ask_recall = (sum(s["ask_pred"] for s in gold_ask) / len(gold_ask)) if gold_ask else None
    false_ask = (sum(s["ask_pred"] for s in gold_clear) / len(gold_clear)) if gold_clear else None
    out = {
        "system": system,
        "set": set_path,
        "n": len(scores),
        "json_valid": mean("valid"),
        "parse_fail": mean("parse_fail"),
        "exact": mean("exact"),
        "exact_ci95": bootstrap_ci([s["exact"] for s in scores]),
        "exact_norm": mean("exact_norm"),
        "exact_norm_ci95": bootstrap_ci([s["exact_norm"] for s in scores]),
        "norm_rule": "strength: number+unit; drug: Devanagari→Latin BRAND_ALIASES",
        "danger": mean("danger"),
        "danger_v1": mean("danger_v1"),
        "danger_v2": mean("danger_v2"),
        "ask_recall": ask_recall,
        "false_ask_rate": false_ask,
        "n_gold_ask": len(gold_ask),
        "per_field": {f: mean(f) for f in FIELDS},
    }
    if lat:
        out["p50_s"] = median(lat)
        out["p95_s"] = sorted(lat)[max(0, int(0.95 * len(lat)) - 1)]
    misses = Counter()
    for s in scores:
        if s["exact"]:
            continue
        for f in FIELDS:
            if not s[f]:
                misses[f] += 1
    out["error_fields"] = dict(misses)
    return out


def write_out(out: dict, preds: list[dict], set_path: str, system: str) -> None:
    tag = Path(set_path).name.removesuffix(".jsonl")
    out_dir = ROOT / "eval" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{system}_{tag}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    with (out_dir / f"{system}_{tag}_preds.jsonl").open("w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in preds)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True)
    ap.add_argument("--set", required=True)
    ap.add_argument("--limit", type=int, default=0, help="cap rows (0 = all)")
    ap.add_argument("--preds", default="", help="rescore an existing preds jsonl; skip Tinker")
    ap.add_argument("--workers", type=int, default=0, help="parallel parsers (gemma31 default 3)")
    a = ap.parse_args()
    gold_rows = [json.loads(l) for l in open(a.set, encoding="utf-8")]
    if a.limit:
        gold_rows = gold_rows[: a.limit]
    if a.system == "gemma31":
        from pillclerk.privacy import assert_gemini_eval_set

        assert_gemini_eval_set(Path(a.set))
    scores, lat, preds = [], [], []
    dropped_train = 0
    if a.preds:
        pred_rows = [json.loads(l) for l in open(a.preds, encoding="utf-8")]
        if a.limit:
            pred_rows = pred_rows[: a.limit]
        gold_rows, pred_rows, dropped_train = drop_train_duplicates(gold_rows, pred_rows)
        for r, pr in zip(gold_rows, pred_rows, strict=True):
            gold = MedLine.model_validate(r["gold"])
            p = MedLine.model_validate(pr["pred"]) if pr.get("pred") else None
            s = score(p, gold)
            scores.append(s)
            preds.append({"line": r["line"], "pred": pr.get("pred"), **s})
        prev = json.loads((ROOT / "eval" / "out" / f"{a.system}_{Path(a.set).name.removesuffix('.jsonl')}.json").read_text(encoding="utf-8")) if (ROOT / "eval" / "out" / f"{a.system}_{Path(a.set).name.removesuffix('.jsonl')}.json").is_file() else {}
        out = summarize(a.system, a.set, scores, None)
        out["dropped_train_duplicates"] = dropped_train
        if "p50_s" in prev:
            out["p50_s"] = prev["p50_s"]
            out["p95_s"] = prev["p95_s"]
            out["rescored_from_preds"] = True
    else:
        gold_rows, _, dropped_train = drop_train_duplicates(gold_rows, None)
        parse = get_parser(a.system, a.set)
        workers = a.workers or (3 if a.system == "gemma31" else 1)
        parsed: list[tuple[MedLine | None, float]] = [(None, 0.0)] * len(gold_rows)

        def _one(i: int, row: dict) -> tuple[int, MedLine | None, float]:
            t0 = time.time()
            pred = parse(row["line"])
            return i, pred, time.time() - t0

        if workers <= 1:
            for i, row in enumerate(gold_rows):
                _, pred, sec = _one(i, row)
                parsed[i] = (pred, sec)
                if (i + 1) % 20 == 0 or i + 1 == len(gold_rows):
                    print(f"{a.system} {i + 1}/{len(gold_rows)}", flush=True)
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = [pool.submit(_one, i, row) for i, row in enumerate(gold_rows)]
                done = 0
                for fut in as_completed(futs):
                    i, pred, sec = fut.result()
                    parsed[i] = (pred, sec)
                    done += 1
                    if done % 20 == 0 or done == len(gold_rows):
                        print(f"{a.system} {done}/{len(gold_rows)}", flush=True)
        for row, (p, sec) in zip(gold_rows, parsed, strict=True):
            lat.append(sec)
            gold = MedLine.model_validate(row["gold"])
            scores.append(score(p, gold))
            preds.append({"line": row["line"], "pred": p.model_dump() if p else None, **scores[-1]})
        out = summarize(a.system, a.set, scores, lat)
        out["dropped_train_duplicates"] = dropped_train
    if a.system == "gemma31":
        from pillclerk.privacy import write_payload_summary

        out["payload_summary"] = write_payload_summary()
    print(json.dumps(out, indent=2))
    write_out(out, preds, a.set, a.system)


if __name__ == "__main__":
    main()
