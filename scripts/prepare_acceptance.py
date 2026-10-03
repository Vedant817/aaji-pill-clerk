"""Reserve unlabelled HMR pages, or finalize two-human gold. No downloads or models."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from pillclerk.acceptance import DEFAULT_DIR, final_gold, read_jsonl
from pillclerk.config import ROOT
from train.prepare_candidate import digest, jsonl, write_frozen


def reserve(images: Path, development: Path, output: Path, pages: int, seed: int, excluded: set[str] | None = None) -> dict:
    if pages < 1:
        raise ValueError("Reserve at least one page")
    photos = sorted(p for p in images.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    used = {r["image"] for r in read_jsonl(development)} | set(excluded or [])
    # First 30 pages were the development queue even where no line was labelled.
    used.update(p.name for p in photos[:30])
    used_hashes = {digest(p) for p in photos if p.name in used}
    pool = [p for p in photos if p.name not in used and digest(p) not in used_hashes]
    labels_path = images / "labels.csv"
    if labels_path.is_file():
        with labels_path.open(encoding="utf-8-sig", newline="") as fh:
            medicine_pages = {r["file"] for r in csv.DictReader(fh) if r.get("medicines", "").strip()}
        pool = [p for p in pool if p.name in medicine_pages]
    pool.sort(key=lambda p: hashlib.sha256(f"{seed}:{p.name}".encode()).hexdigest())
    chosen, hashes = [], set()
    for p in pool:
        sha = digest(p)
        if sha not in hashes:
            chosen.append({"image": p.name, "sha256": sha})
            hashes.add(sha)
        if len(chosen) == pages:
            break
    if len(chosen) < pages:
        raise ValueError(f"Only {len(chosen)} unexposed distinct pages available; requested {pages}")
    result = {"kind": "reserved human annotation queue; no gold or model results yet",
              "dataset": "chaithanyakota/100-handwritten-medical-records",
              "source_url": "https://huggingface.co/datasets/chaithanyakota/100-handwritten-medical-records",
              "license": "CC BY-ND 4.0; original images stay local and are not modified",
              "image_directory": str(images.relative_to(ROOT)).replace("\\", "/"), "seed": seed,
              "development_labels_sha256": digest(development), "development_page_names": sorted(used),
              "source_revision": "afcca9f163561af54fcd145003e550d2d320aafb",
              "selection": "Hash-ranked unseen pages with medicine-name metadata; names are not shown to annotators",
              "pages": chosen, "required_rounds": ["A", "B"], "gold_status": "pending human labels",
              "limits": "Separate pages from the same public source, not family data or an independent population"}
    write_frozen(output / "manifest.json", json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--pages", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20261003)
    ap.add_argument("--finalize", action="store_true")
    args = ap.parse_args()
    if args.finalize:
        rows = final_gold(args.out)
        write_frozen(args.out / "gold.jsonl", jsonl(rows))
        print(f"Finalized {len(rows)} two-human-checked lines. No model evaluation run.")
    else:
        used = {p["image"] for path in (ROOT / "data/acceptance").glob("*/manifest.json")
                if path.parent.resolve() != args.out.resolve()
                for p in json.loads(path.read_text(encoding="utf-8"))["pages"]}
        result = reserve(ROOT / "data/public/hmr100", ROOT / "data/public_labels/hmr100_gold.jsonl",
                         args.out, args.pages, args.seed, used)
        print(f"Reserved {len(result['pages'])} pages. Gold labels pending; no images copied.")


if __name__ == "__main__":
    main()
