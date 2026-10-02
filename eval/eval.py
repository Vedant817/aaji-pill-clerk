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
DANGER = ["dose", "taper", "duration_days", "every_n_days", "kind"]


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


def field_eq(p: MedLine, g: MedLine, f: str) -> bool:
    return canon(getattr(p, f)) == canon(getattr(g, f))


def score(pred: MedLine | None, gold: MedLine) -> dict:
    if pred is None:
        return {"valid": 0, "exact": 0, "danger": 1, **{f: 0 for f in FIELDS}}
    fs = {f: int(field_eq(pred, gold, f)) for f in FIELDS}
    danger = int(any(not fs[f] for f in DANGER) and not pred.needs_check)
    return {"valid": 1, "exact": int(all(fs.values())), "danger": danger, **fs}


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
        "gemma31": lambda: infer.make_gemini_parser(set_path),
    }[system]()


def summarize(system: str, set_path: str, scores: list[dict], lat: list[float] | None) -> dict:
    mean = lambda k: sum(s[k] for s in scores) / len(scores)
    out = {
        "system": system,
        "set": set_path,
        "n": len(scores),
        "json_valid": mean("valid"),
        "exact": mean("exact"),
        "exact_ci95": bootstrap_ci([s["exact"] for s in scores]),
        "danger": mean("danger"),
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
    if a.preds:
        pred_rows = [json.loads(l) for l in open(a.preds, encoding="utf-8")]
        if a.limit:
            pred_rows = pred_rows[: a.limit]
        for r, pr in zip(gold_rows, pred_rows, strict=True):
            gold = MedLine.model_validate(r["gold"])
            p = MedLine.model_validate(pr["pred"]) if pr.get("pred") else None
            s = score(p, gold)
            scores.append(s)
            preds.append({"line": r["line"], "pred": pr.get("pred"), **s})
        prev = json.loads((ROOT / "eval" / "out" / f"{a.system}_{Path(a.set).name.removesuffix('.jsonl')}.json").read_text(encoding="utf-8")) if (ROOT / "eval" / "out" / f"{a.system}_{Path(a.set).name.removesuffix('.jsonl')}.json").is_file() else {}
        out = summarize(a.system, a.set, scores, None)
        if "p50_s" in prev:
            out["p50_s"] = prev["p50_s"]
            out["p95_s"] = prev["p95_s"]
            out["rescored_from_preds"] = True
    else:
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
    print(json.dumps(out, indent=2))
    write_out(out, preds, a.set, a.system)


if __name__ == "__main__":
    main()
