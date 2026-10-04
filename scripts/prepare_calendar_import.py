"""Validate a clerk ICS export and prepare private Google Calendar tool payloads.

This writes a local file only. Native Google Calendar ICS import remains supported
through its web interface. No key, automatic hosted call, or regimen is bundled.
"""
import argparse
import hashlib
import json
from pathlib import Path

from pillclerk.calendar_import import google_events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ics", required=True, type=Path)
    parser.add_argument("--timezone", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Choose a new output file; existing evidence is preserved")
    raw = args.ics.read_bytes()
    rows = google_events(raw, args.timezone, synthetic=args.synthetic)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"ics_sha256": hashlib.sha256(raw).hexdigest(),
        "synthetic": args.synthetic, "events": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Validated {len(rows)} events; wrote local payloads. No calendar write or phone verification performed.")


if __name__ == "__main__":
    main()
