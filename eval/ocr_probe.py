"""Exploratory local OCR probe; published drug names are not transcription gold.

Raw output stays in gitignored data/real by default. Only aggregate counts may
be shared. This probe cannot establish CER, dose accuracy, or human acceptance.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
from pathlib import Path

from pillclerk import config
from pillclerk.acceptance import DEFAULT_DIR, load_manifest, page_path
from pillclerk.ocr import extract_from_image


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.casefold())


def summarize(records: list[dict], labels: dict[str, list[str]], *, backend: str, model: str | None) -> dict:
    pages = []
    for record in records:
        names = [normalize(x) for x in labels.get(record["image"], []) if normalize(x)]
        text = normalize(" ".join(record["lines"]))
        pages.append({"image": record["image"], "output_lines": len(record["lines"]),
                      "failed": bool(record.get("error")),
                      "exact_published_labels_found": sum(name in text for name in names),
                      "published_labels": len(names)})
    return {"backend": backend, "model": model, "pages_attempted": len(pages),
            "pages_with_text": sum(p["output_lines"] > 0 for p in pages),
            "pages_without_text": sum(p["output_lines"] == 0 for p in pages),
            "pages_failed": sum(p["failed"] for p in pages),
            "published_label_exact_presence": {
                "found": sum(p["exact_published_labels_found"] for p in pages),
                "total": sum(p["published_labels"] for p in pages)},
            "cer": None, "human_verified": False,
            "note": "Exploratory normalized exact presence of nonempty full published medicine labels in page OCR output. Not medicine-line alignment, dose accuracy, or OCR CER. AI references are not CER gold.",
            "pages": pages}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--backend", choices=["windows", "ollama"], required=True)
    parser.add_argument("--raw", type=Path, default=config.ROOT / "data/real/ocr-probe/raw.jsonl")
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--reuse-raw", action="store_true")
    args = parser.parse_args()
    import os
    os.environ["EXTRACT_BACKEND"] = args.backend
    manifest = load_manifest(args.queue)
    paths = {p["image"]: page_path(p["image"], args.queue) for p in manifest["pages"]}
    if args.reuse_raw:
        records = [json.loads(line) for line in args.raw.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(records) != len(paths) or {r["image"] for r in records} != set(paths):
            raise ValueError("Raw output must cover every frozen page exactly once")
        if any(not isinstance(r["lines"], list) or any(not isinstance(x, str) for x in r["lines"]) for r in records):
            raise ValueError("Raw output must contain actual text lines")
    else:
        records = []
        args.raw.parent.mkdir(parents=True, exist_ok=True)
        with args.raw.open("w", encoding="utf-8") as stream:
            for image, path in paths.items():
                start = time.monotonic()
                try:
                    lines, error = extract_from_image(str(path)), None
                except Exception as exc:
                    lines, error = [], type(exc).__name__
                record = {"image": image, "lines": lines, "error": error,
                          "seconds": round(time.monotonic() - start, 3)}
                records.append(record)
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                print(json.dumps({"image": image, "output_lines": len(lines), "error": error, "seconds": record["seconds"]}), flush=True)
    labels_path = config.ROOT / manifest["image_directory"] / "labels.csv"
    with labels_path.open(encoding="utf-8", newline="") as stream:
        labels = {r["file"]: r["medicines"].split(",") for r in csv.DictReader(stream)}
    result = summarize(records, labels, backend=args.backend,
                       model=config.OLLAMA_EXTRACT_MODEL if args.backend == "ollama" else None)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "pages"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
