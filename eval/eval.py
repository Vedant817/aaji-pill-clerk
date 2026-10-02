"""Usage: uv run python -m eval.eval --system b0 --set data/synth/synth_test.jsonl

Results stay TODO until this script is actually run. Do not invent numbers.
"""

from __future__ import annotations

import argparse
import json
import random
import time
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


def dump(v):
    return json.dumps(v, default=lambda m: m.model_dump(), sort_keys=True)


def field_eq(p: MedLine, g: MedLine, f: str) -> bool:
    a, b = getattr(p, f), getattr(g, f)
    if hasattr(a, "model_dump") or hasattr(b, "model_dump") or isinstance(a, list):
        return dump(a) == dump(b)
    return norm(a) == norm(b)


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


def get_parser(system: str):
    from pillclerk import infer

    ck = lambda v: json.loads((ROOT / "train" / f"checkpoint_{v}.json").read_text())["sampler"]
    return {
        "b0": lambda: infer.make_tinker_parser(None),
        "ft1": lambda: infer.make_tinker_parser(ck("v1")),
        "ft2": lambda: infer.make_tinker_parser(ck("v2")),
    }[system]()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True)
    ap.add_argument("--set", required=True)
    a = ap.parse_args()
    parse = get_parser(a.system)
    rows = [json.loads(l) for l in open(a.set, encoding="utf-8")]
    scores, lat, preds = [], [], []
    for r in rows:
        t0 = time.time()
        p = parse(r["line"])
        lat.append(time.time() - t0)
        gold = MedLine.model_validate(r["gold"])
        scores.append(score(p, gold))
        preds.append({"line": r["line"], "pred": p.model_dump() if p else None, **scores[-1]})
    mean = lambda k: sum(s[k] for s in scores) / len(scores)
    out = {
        "system": a.system,
        "set": a.set,
        "n": len(rows),
        "json_valid": mean("valid"),
        "exact": mean("exact"),
        "exact_ci95": bootstrap_ci([s["exact"] for s in scores]),
        "danger": mean("danger"),
        "per_field": {f: mean(f) for f in FIELDS},
        "p50_s": median(lat),
        "p95_s": sorted(lat)[max(0, int(0.95 * len(lat)) - 1)],
    }
    print(json.dumps(out, indent=2))
    tag = Path(a.set).name.removesuffix(".jsonl")
    out_dir = ROOT / "eval" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{a.system}_{tag}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    with (out_dir / f"{a.system}_{tag}_preds.jsonl").open("w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in preds)


if __name__ == "__main__":
    main()
