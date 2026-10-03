"""Freeze local AI-created reference labels without representing them as human gold."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pillclerk.acceptance import DEFAULT_DIR, load_manifest, page_path
from pillclerk.config import ROOT
from pillclerk.schema import MedLine
from train.prepare_candidate import digest, jsonl, write_frozen


def build(drafts: Path, output: Path, queue: Path = DEFAULT_DIR) -> dict:
    entries = json.loads(drafts.read_text(encoding="utf-8"))
    reserved = load_manifest(queue)
    if set(entries) != {p["image"] for p in reserved["pages"]}:
        raise ValueError("AI reference must account for every reserved page and no extra pages")
    rows = []
    for page in reserved["pages"]:
        image = page["image"]
        page_path(image, queue)
        if not entries[image]:
            raise ValueError(f"Empty medicine reference for {image}")
        for n, (line, fields) in enumerate(entries[image], 1):
            if not isinstance(line, str) or not line.strip() or "form" not in fields or "needs_check" not in fields:
                raise ValueError("Explicit transcription, form and ASK fields are required")
            med = MedLine.model_validate(fields)
            if med.drug is None and "drug" not in med.needs_check:
                raise ValueError("Unknown drug requires ASK")
            rows.append({"id": f"hmr_ai:{image}:{n}", "image": image, "line_no": n,
                "line": line, "gold": med.model_dump(), "synthetic": False, "held_out": True,
                "photographed": True, "source": "hmr100", "label_origin": "ai_single_agent",
                "human_verified": False, "double_checked": False,
                "evaluation_status": "exploratory; unverified AI reference"})
    manifest = {"kind": "AI-created exploratory references; not human acceptance gold",
                "annotator": "Codex gpt-6.1-sol, direct local image inspection",
                "pages": len(entries), "lines": len(rows),
                "drafts_sha256": digest(drafts), "page_manifest_sha256": digest(queue / "manifest.json"),
                "human_verified": False, "independent_annotation_rounds": 0,
                "transcription_limits": "Includes uncertainty markers and editorial block/context notes; not OCR CER gold",
                "gold_limits": "Schema conventions map OD/weekly to a default slot and months to 30 days; unsupported quantities/routes abstain",
                "training_use": "prohibited", "publication": "local only; no original image or derivative redistribution"}
    blobs = {"ai_reference.jsonl": jsonl(rows), "manifest.json": json.dumps(manifest, indent=2) + "\n"}
    for name, blob in blobs.items():
        p = output / name
        if p.exists() and p.read_text(encoding="utf-8") != blob:
            raise FileExistsError(f"AI reference is frozen: {p}")
    for name, blob in blobs.items():
        write_frozen(output / name, blob)
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drafts", type=Path, default=ROOT / "data/reference/hmr_ai_v1/drafts.json")
    ap.add_argument("--out", type=Path, default=ROOT / "data/reference/hmr_ai_v1")
    args = ap.parse_args()
    print(json.dumps(build(args.drafts, args.out), indent=2))


if __name__ == "__main__":
    main()
