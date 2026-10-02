# Data

- `data/drugs.csv` — public drug names, forms, strengths (committed).
- `data/patterns.yaml` — schedule and style weights (committed).
- `data/synth/` — synthetic JSONL labelled as such (committed after generation). `train.jsonl` is 2000 mix + 500 FT2 targeted rows (`targeted_v2.jsonl`) + 396 unique form/dose/food stress rows (`targeted_form_dose_food.jsonl`, 400 generated, 4 already in train). `synth_test.jsonl` is 400 lines on held-out drug names. FT2 LoRA was trained on the 2500-row mix.
- `data/demo/prescriptions/aaji_sample.txt` — synthetic Scan demo slip.
- `data/heldout/handwritten_realistic.jsonl` — Hand-written realistic (n=102), committed, never used in training. Not photographed.
- `data/public/` — **gitignored**. Public photographed images. HMR-100 is CC BY-ND 4.0 (never commit images or modified copies). BD-200 is CC BY 4.0. Download: `scripts/download_public.sh`.
- `data/public_labels/hmr100_gold.jsonl` — committed gold for **Public real-world set: HMR-100 (India)**, keyed by image file + line number. MIRAGE arXiv 2410.09729: simulated records written by doctors; handwriting/notation real, patients not. Never family data.
- `data/public_labels/bd200_gold.jsonl` — optional BD-200 notation stress labels.
- `data/real/` — **gitignored**. Unused this weekend (no family photos).
