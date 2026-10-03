"""Local, blind human annotation of reserved public prescription pages. No models."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from pillclerk.config import ROOT
from pillclerk.schema import MedLine

DEFAULT_DIR = ROOT / "data/acceptance/hmr_v1"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.is_file() else []


def load_manifest(folder: Path = DEFAULT_DIR) -> dict:
    return json.loads((folder / "manifest.json").read_text(encoding="utf-8"))


def reserved_names() -> set[str]:
    return {p["image"] for path in (ROOT / "data/acceptance").glob("*/manifest.json")
            for p in json.loads(path.read_text(encoding="utf-8")).get("pages", [])}


def page_path(image: str, folder: Path = DEFAULT_DIR) -> Path:
    manifest = load_manifest(folder)
    page = next((p for p in manifest["pages"] if p["image"] == image), None)
    if page is None or Path(image).name != image:
        raise ValueError("Image is not in the reserved page manifest")
    path = ROOT / manifest["image_directory"] / image
    if hashlib.sha256(path.read_bytes()).hexdigest() != page["sha256"]:
        raise ValueError("Reserved image changed since the page set was frozen")
    return path


def latest_annotations(folder: Path = DEFAULT_DIR) -> dict[tuple[str, int, str], dict]:
    return {(r["image"], r["line_no"], r["round"]): r for r in read_jsonl(folder / "annotations.jsonl")}


def validate_gold(blob: dict) -> MedLine:
    if not isinstance(blob, dict):
        raise ValueError("Gold must be a JSON object")
    required = set(MedLine.model_fields) - {"note"}
    if required - blob.keys():
        raise ValueError(f"Explicitly enter all gold fields, including nulls: {sorted(required - blob.keys())}")
    doses = [blob.get("dose")] + [step.get("dose") for step in blob.get("taper", []) if isinstance(step, dict)]
    for dose in doses:
        if dose is not None and (not isinstance(dose, dict) or set(dose) != {"morning", "afternoon", "night", "unit"}):
            raise ValueError("Every dose must explicitly include morning, afternoon, night, and unit")
    return MedLine.model_validate(blob)


def save_annotation(*, image: str, line_no: int, round_name: str, annotator: str,
                    line: str, gold: dict, folder: Path = DEFAULT_DIR) -> None:
    page_path(image, folder)
    if (folder / "gold.jsonl").exists():
        raise ValueError("Finalized labels are frozen; create a new annotation set to revise them")
    if round_name not in {"A", "B"} or line_no < 1 or not annotator.strip() or not line.strip():
        raise ValueError("Enter a round, annotator ID, positive line number, and actual transcription")
    records = latest_annotations(folder)
    other = "B" if round_name == "A" else "A"
    if any(r["annotator"].casefold() == annotator.strip().casefold() and r["round"] == other
           for r in records.values()):
        raise ValueError("A and B must be completed by different human annotators")
    med = validate_gold(gold)
    row = {"image": image, "line_no": line_no, "round": round_name, "annotator": annotator.strip(),
           "line": line.strip(), "gold": med.model_dump(), "ts": datetime.now(timezone.utc).isoformat()}
    with (folder / "annotations.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def mark_page_complete(image: str, round_name: str, annotator: str, folder: Path = DEFAULT_DIR) -> None:
    page_path(image, folder)
    if (folder / "gold.jsonl").exists() or round_name not in {"A", "B"}:
        raise ValueError("Use an unfinalized set and annotation round A or B")
    records = [r for r in latest_annotations(folder).values() if r["image"] == image and r["round"] == round_name]
    if not records or any(r["annotator"] != annotator.strip() for r in records):
        raise ValueError("Complete a page only after this annotator has entered all its medicine lines")
    digest = hashlib.sha256(json.dumps(sorted(records, key=lambda r: r["line_no"]), sort_keys=True).encode()).hexdigest()
    row = {"image": image, "round": round_name, "annotator": annotator.strip(), "annotations_sha256": digest}
    with (folder / "completed_pages.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def final_gold(folder: Path = DEFAULT_DIR) -> list[dict]:
    """No gold until both people attest complete pages and agree on every line."""
    annotations = latest_annotations(folder)
    complete = {(r["image"], r["round"]): r for r in read_jsonl(folder / "completed_pages.jsonl")}
    out = []
    for page in load_manifest(folder)["pages"]:
        image = page["image"]
        page_path(image, folder)
        rounds = {}
        for name in ("A", "B"):
            records = sorted([r for r in annotations.values() if r["image"] == image and r["round"] == name], key=lambda r: r["line_no"])
            attestation = complete.get((image, name))
            digest = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
            if not records or not attestation or attestation["annotations_sha256"] != digest:
                raise ValueError(f"{image}: both complete, unchanged annotation rounds are required")
            rounds[name] = records
        a, b = rounds["A"], rounds["B"]
        if [r["line_no"] for r in a] != list(range(1, len(a) + 1)):
            raise ValueError(f"{image}: line numbers must run consecutively from 1")
        if len(a) != len(b) or [r["line_no"] for r in a] != [r["line_no"] for r in b]:
            raise ValueError(f"{image}: annotators disagree on medicine-line coverage")
        for x, y in zip(a, b, strict=True):
            gx = MedLine.model_validate(x["gold"])
            gy = MedLine.model_validate(y["gold"])
            # Ignore non-scored notes; preserve every actual clinical field and ASK.
            px, py = gx.model_dump(exclude={"note"}), gy.model_dump(exclude={"note"})
            px["needs_check"], py["needs_check"] = sorted(set(gx.needs_check)), sorted(set(gy.needs_check))
            if x["annotator"].casefold() == y["annotator"].casefold() or x["line"] != y["line"] or px != py:
                raise ValueError(f"{image} line {x['line_no']}: human disagreement must be resolved against the image")
            out.append({"id": f"hmr_acceptance:{image}:{x['line_no']}", "image": image, "line_no": x["line_no"],
                        "line": x["line"], "gold": gx.model_dump(), "synthetic": False, "held_out": True,
                        "photographed": True, "source": "hmr100", "double_checked": True})
    return out
