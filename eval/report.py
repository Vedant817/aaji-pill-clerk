"""Build paired stats from eval/out/*_preds.jsonl. Do not invent numbers."""

from __future__ import annotations

import json
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "out"


def load_preds(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def mcnemar_p_two_sided(n01: int, n10: int) -> float:
    """Exact two-sided McNemar p-value (binomial n01 vs n10, p=0.5)."""
    n = n01 + n10
    if n == 0:
        return 1.0
    tail = min(n01, n10)
    cdf = sum(comb(n, i) for i in range(tail + 1))
    p = 2.0 * cdf / (2**n)
    return min(1.0, p)


def mcnemar_exact(a: list[dict], b: list[dict], field: str = "exact") -> dict:
    """n01 = a wrong / b right; n10 = a right / b wrong (McNemar discordant pairs)."""
    if len(a) != len(b):
        raise ValueError(f"pred length mismatch {len(a)} vs {len(b)}")
    n01 = n10 = n11 = n00 = 0
    for x, y in zip(a, b, strict=True):
        ax, by = int(x.get(field) or 0), int(y.get(field) or 0)
        if ax == 0 and by == 1:
            n01 += 1
        elif ax == 1 and by == 0:
            n10 += 1
        elif ax == 1 and by == 1:
            n11 += 1
        else:
            n00 += 1
    return {
        "n": len(a),
        "n01_b_fixes": n01,
        "n10_b_regresses": n10,
        "both_right": n11,
        "both_wrong": n00,
        "p_two_sided": mcnemar_p_two_sided(n01, n10),
        "field": field,
    }


def danger_counts(preds: list[dict]) -> int:
    return sum(int(r.get("danger") or 0) for r in preds)


def ci_width_points(n: int) -> float:
    """Rough half-width in percentage points for a proportion near 0.5 (n≈100 → ±8–9)."""
    if n <= 0:
        return 0.0
    return 1.96 * (0.5 * 0.5 / n) ** 0.5 * 100


def public_set_name(n: int | None = None) -> str:
    if n is None:
        return "Public real-world set: HMR-100 (India)"
    return f"Public real-world set: HMR-100 (India), n={n}"


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="preds jsonl A (e.g. ft2)")
    ap.add_argument("--b", required=True, help="preds jsonl B (e.g. ft3 or gemma31)")
    ap.add_argument("--field", default="exact")
    args = ap.parse_args()
    a = load_preds(Path(args.a))
    b = load_preds(Path(args.b))
    print(json.dumps(mcnemar_exact(a, b, field=args.field), indent=2))
    print(
        json.dumps(
            {
                "danger_v2_count_a": sum(int(r.get("danger_v2") or 0) for r in a),
                "danger_v2_count_b": sum(int(r.get("danger_v2") or 0) for r in b),
                "n": len(a),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

