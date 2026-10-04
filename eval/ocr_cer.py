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
from pillclerk.acceptance import DEFAULT_DIR, final_gold, page_path

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
        from pillclerk import config
        from pillclerk.ocr import local_ocr_client
        client = local_ocr_client()
        models = client.list().models
        return any(m.model == config.OLLAMA_EXTRACT_MODEL for m in models)
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=20)
    ap.add_argument("--queue", type=Path, default=DEFAULT_DIR)
    a = ap.parse_args()
    if a.pages < 1:
        ap.error("pages must be positive")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        gold_rows = final_gold(a.queue)
    except ValueError:
        gold_rows = []
    pages = sorted({r.get("image") for r in gold_rows if r.get("image")})[: a.pages]
    if not gold_rows or not pages:
        out = {"n_pages": 0, "n_lines": 0, "cer": None, "note": "no finalized independent human transcription gold yet"}
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        return 0
    if not e4b_available():
        out = {
            "n_pages": 0,
            "n_lines": 0,
            "cer": None,
            "note": "configured local Ollama extraction model unavailable; local OCR not scored",
        }
        OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(json.dumps(out, indent=2))
        return 0

    from pillclerk.ocr import transcribe_local

    recs: list[dict] = []
    for image in pages:
        path = page_path(str(image), a.queue)
        hyp_lines = transcribe_local(str(path))
        rows = sorted([r for r in gold_rows if r.get("image") == image], key=lambda r: r["line_no"])
        ref, hyp = "\n".join(r["line"] for r in rows), "\n".join(hyp_lines)
        # Full-page medicine transcription catches omissions and extra lines;
        # never silently substitute the whole page for a missing indexed line.
        recs.append({"image": image, "n_lines": len(rows), "reference_characters": len(ref),
                     "edit_distance": levenshtein(ref, hyp), "output_lines": len(hyp_lines)})
    characters = sum(r["reference_characters"] for r in recs)
    mean = sum(r["edit_distance"] for r in recs) / characters if characters else None
    out = {"n_pages": len(recs), "n_lines": sum(r["n_lines"] for r in recs), "cer": mean,
           "method": "character-weighted full-page medicine transcription, including line breaks",
           "pages": recs}
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("n_pages", "n_lines", "cer")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
