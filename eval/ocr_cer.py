"""Character error rate of local gemma4:e4b vs confirmed Label REAL lines.

Only runs on gold the user confirmed while looking at the image.
Photos never leave the laptop (EXTRACT_BACKEND=ollama).

Usage: uv run python -m eval.ocr_cer --pages 20
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pillclerk.config import ROOT
from pillclerk.public_data import HMR_DIR, load_gold

OUT = ROOT / "eval" / "out" / "ocr_cer.json"


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins, delete, sub = cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def cer(ref: str, hyp: str) -> float:
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein(ref, hyp) / len(ref)


def e4b_available() -> bool:
    try:
        import ollama  # noqa: F401
    except ImportError:
        return False
    from shutil import which

    return which("ollama") is not None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=20)
    a = ap.parse_args()
    gold_rows = load_gold("hmr100")
    pages = sorted({r.get("image") for r in gold_rows if r.get("image")})[: a.pages]
    if not gold_rows or not pages:
        out = {"n_pages": 0, "n_lines": 0, "cer": None, "note": "no confirmed HMR gold yet"}
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        return 0
    if not e4b_available():
        out = {
            "n_pages": 0,
            "n_lines": 0,
            "cer": None,
            "note": "gemma4:e4b / ollama not on this laptop; local OCR not claimed",
        }
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        return 0

    from pillclerk.ocr import transcribe_local

    recs: list[dict] = []
    for image in pages:
        path = HMR_DIR / str(image)
        if not path.is_file():
            continue
        hyp_lines = transcribe_local(str(path))
        refs = [r["line"] for r in gold_rows if r.get("image") == image]
        for i, ref in enumerate(refs):
            hyp = hyp_lines[i] if i < len(hyp_lines) else " ".join(hyp_lines)
            recs.append({"image": image, "ref": ref, "hyp": hyp, "cer": cer(ref, hyp)})
    mean = sum(r["cer"] for r in recs) / len(recs) if recs else None
    out = {"n_pages": len(pages), "n_lines": len(recs), "cer": mean, "lines": recs}
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("n_pages", "n_lines", "cer")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
