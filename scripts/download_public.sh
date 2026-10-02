#!/usr/bin/env bash
# Download public photographed sets into gitignored data/public/.
# HMR-100 (India): Hugging Face chaithanyakota/100-handwritten-medical-records
#   CC BY-ND 4.0 — originals only; never commit images or modified copies.
#   Paper: MIRAGE, arXiv 2410.09729 (simulated records written by doctors).
# BD-200 (Bangladesh): Mendeley DOI 10.17632/k62rfd23kz
#   CC BY 4.0 — "1+0+1" schedules and Bangla durations.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p data/public/hmr100 data/public/bd200 data/public_labels
# pyarrow unpacks the HF parquet; huggingface_hub is optional.
uv run --with pyarrow --with huggingface_hub python scripts/download_public.py "$@"
