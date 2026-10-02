"""Download public photographed sets into gitignored data/public/.

HMR-100 images are CC BY-ND 4.0: store originals only. Do not resize, crop,
or otherwise modify them. Never commit the images.

BD-200 is CC BY 4.0. Prefer the user's existing unpack under data/public/bd200/.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data" / "public"
HMR = PUBLIC / "hmr100"
BD = PUBLIC / "bd200"

HMR_HF = "chaithanyakota/100-handwritten-medical-records"
HMR_PARQUET = "https://huggingface.co/datasets/chaithanyakota/100-handwritten-medical-records/resolve/main/data/train-00000-of-00001.parquet"
# Mendeley "A Curated Bangladesh-Based Dataset of Handwritten and Printed Prescription Images"
# DOI 10.17632/k62rfd23kz (v2 zip). This repo calls the folder bd200.
BD_ZIP = "https://data.mendeley.com/public-api/zip/k62rfd23kz/download/2"
HF_TIMEOUT_S = 120


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"GET {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "aaji-pill-clerk/0.1"})
    with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as fh:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            fh.write(chunk)


def extract_hmr() -> int:
    HMR.mkdir(parents=True, exist_ok=True)
    existing = list(HMR.glob("hmr_*.jpg")) + list(HMR.glob("hmr_*.png"))
    if len(existing) >= 100 and (HMR / "labels.csv").is_file():
        print(f"HMR-100 already present ({len(existing)} images). Skip.")
        return len(existing)

    parquet_path = HMR / "_source.parquet"
    if not parquet_path.is_file():
        try:
            _download(HMR_PARQUET, parquet_path)
        except Exception as exc:
            print(f"direct HF URL failed ({exc}); trying hf_hub_download", flush=True)
            os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", str(HF_TIMEOUT_S))
            from huggingface_hub import hf_hub_download

            got = hf_hub_download(
                repo_id=HMR_HF,
                filename="data/train-00000-of-00001.parquet",
                repo_type="dataset",
                local_dir=str(HMR / "_hf"),
                etag_timeout=HF_TIMEOUT_S,
            )
            parquet_path = Path(got)

    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("pandas is required to unpack HMR parquet") from exc

    df = pd.read_parquet(parquet_path)
    rows: list[tuple[str, str]] = []
    for i, rec in df.iterrows():
        img = rec.get("image") if hasattr(rec, "get") else rec["image"]
        suffix = ".jpg"
        payload = None
        src_path = None
        if isinstance(img, dict):
            payload = img.get("bytes")
            src_path = img.get("path")
            if src_path:
                suffix = Path(str(src_path)).suffix or ".jpg"
        elif isinstance(img, (bytes, bytearray)):
            payload = bytes(img)
        name = f"hmr_{int(i):03d}{suffix.lower()}"
        dest = HMR / name
        # Write original bytes only (CC BY-ND: no re-encode / resize / crop).
        if isinstance(payload, (bytes, bytearray)) and not dest.is_file():
            dest.write_bytes(bytes(payload))
        elif src_path and Path(str(src_path)).is_file() and not dest.is_file():
            dest.write_bytes(Path(str(src_path)).read_bytes())
        meds = rec.get("medicines") if hasattr(rec, "get") else rec["medicines"]
        if meds is None or (isinstance(meds, float) and str(meds) == "nan"):
            meds = ""
        rows.append((name, str(meds)))

    with (HMR / "labels.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "medicines"])
        w.writerows(rows)

    n = len(list(HMR.glob("hmr_*.jpg")) + list(HMR.glob("hmr_*.png")))
    print(f"HMR-100: {n} images + labels.csv in {HMR}")
    print("License: CC BY-ND 4.0. Do not modify or commit these images.")
    return n


def extract_bd() -> int:
    BD.mkdir(parents=True, exist_ok=True)
    photos = [
        p
        for p in BD.rglob("*")
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    ]
    if photos:
        print(f"BD-200 already present ({len(photos)} images). Skip.")
        return len(photos)
    zip_path = BD / "_source.zip"
    try:
        _download(BD_ZIP, zip_path)
    except Exception as exc:
        print(
            f"BD-200 download failed ({exc}). Place original images in {BD} "
            "(CC BY 4.0, Mendeley DOI 10.17632/k62rfd23kz).",
            file=sys.stderr,
        )
        return 0
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(BD)
    except zipfile.BadZipFile:
        print("BD-200 zip was not a zip file. Place images in data/public/bd200/ yourself.", file=sys.stderr)
        return 0
    photos = [
        p
        for p in BD.rglob("*")
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    ]
    print(f"BD-200: {len(photos)} images in {BD} (CC BY 4.0). Do not commit the images.")
    return len(photos)


def main() -> int:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    n_h = extract_hmr()
    n_b = extract_bd()
    print(json.dumps({"hmr100": n_h, "bd200": n_b, "dir": str(PUBLIC)}, indent=2))
    return 0 if n_h else 1


if __name__ == "__main__":
    raise SystemExit(main())
