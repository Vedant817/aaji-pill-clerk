"""Offline page-level name presence against local AI references, never human gold.

This is diagnostic text overlap, not CER, line/dose accuracy or clinical safety.
Only aggregate counts and input hashes are emitted; no transcription is shared.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def words(value: str) -> list[str]:
    # Split letter/number boundaries so '5mg' and '5 mg' are comparable.
    return re.findall(r"[a-z]+|[0-9]+", value.casefold())


def contains_name(lines: list[str], name: str) -> bool:
    needle = words(name)
    if not needle:
        return False
    for line in lines:
        tokens = words(line)
        if any(tokens[i:i + len(needle)] == needle for i in range(len(tokens) - len(needle) + 1)):
            return True
    return False


def audit(records: list[dict], references: list[dict]) -> dict:
    if not references or any(r.get("label_origin") != "ai_single_agent" or
                             r.get("human_verified") is not False for r in references):
        raise ValueError("This diagnostic requires explicitly unverified AI references")
    pages = {r["image"] for r in references}
    if len(records) != len(pages) or {r["image"] for r in records} != pages:
        raise ValueError("OCR must cover each reference page exactly once")
    if any(not isinstance(r["lines"], list) or any(not isinstance(x, str) for x in r["lines"])
           or (r.get("error") and r["lines"]) for r in records):
        raise ValueError("OCR records must contain actual lines and explicit failures")
    output = {r["image"]: r["lines"] for r in records}
    # Distinct names per page; repeated prescriptions are not separate detections.
    expected = {(r["image"], tuple(words(r["gold"].get("drug") or "")))
                for r in references if words(r["gold"].get("drug") or "")}
    found = sum(contains_name(output[image], " ".join(name)) for image, name in expected)
    return {"reference_origin": "ai_single_agent", "human_verified": False,
            "pages": len(pages), "reference_lines": len(references),
            "pages_with_text": sum(bool(r["lines"]) for r in records),
            "pages_failed": sum(bool(r.get("error")) for r in records),
            "distinct_known_name_presence": {"found": found, "total": len(expected)},
            "unknown_drug_reference_lines": sum(not words(r["gold"].get("drug") or "") for r in references),
            "cer": None,
            "limits": "Case-insensitive contiguous ASCII letter/number token presence within any OCR line on the same page. Distinct names only; no alignment or extra-name penalty. AI references may be wrong. Does not score strength, dose, omissions of repeated orders, clinical accuracy or CER."}


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--windows", type=Path, required=True)
    parser.add_argument("--ollama", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    refs = read_rows(args.references)
    result = {"kind": "exploratory saved OCR name-presence audit; no model calls",
              "reference_sha256": hashlib.sha256(args.references.read_bytes()).hexdigest(),
              "results": {backend: dict(audit(read_rows(path), refs),
                                        raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                          for backend, path in (("windows", args.windows), ("ollama", args.ollama))}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
