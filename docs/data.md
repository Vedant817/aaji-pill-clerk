# Data

- `data/drugs.csv` — public drug names, forms, strengths (committed).
- `data/patterns.yaml` — schedule and style weights (committed).
- `data/synth/` — synthetic JSONL labelled as such (committed after generation). `train.jsonl` is **3096** rows, all `renderer=template`: 2000 mix + 500 FT2 targeted rows (`targeted_v2.jsonl`) + 396 unique form/dose/food stress rows (`targeted_form_dose_food.jsonl`, 400 generated, 4 already in train) + 200 drug/strength rows (`targeted_drug_strength.jsonl`). `synth_test.jsonl` is 400 lines on held-out drug names. **FT2 LoRA was trained on the 2500-row version at git `5619cee`.** Gemma 31B did not write any training row. `targeted_ft3_danger.jsonl` is 200 FT3 rows (insulin units, syrup ml/ASK, Hindi-Marathi three-slot, combo suffixes). Overlap vs eval is clean (`eval/out/overlap_extra.json`). SFT mixes them via `train.sft --extra`; `train.jsonl` stays **3096** until a kept v3. `train.align_labels` later fixed leftover gold bugs without retraining: train 104/3096 (food 84, duration_days 7, prn_max_per_day 18), val 15/250 (`eval/out/train_label_bugs.json`).
- `data/demo/prescriptions/aaji_sample.txt` — synthetic Scan demo slip.
- `data/heldout/handwritten_realistic.jsonl` — Hand-written realistic (n=102), generated in code (`authored=code:eval/handwritten_realistic.py`), committed, never used in training. Not photographed, not Vedant's handwriting. Created after FT2 (`5619cee`). 67/102 lines use drug names seen in `train.jsonl`.
- `data/public/` — **gitignored**. Public photographed images. HMR-100 is CC BY-ND 4.0 (never commit images or modified copies). BD-200 is CC BY 4.0. Download: `scripts/download_public.sh`.
- `data/public_labels/hmr100_gold.jsonl` — committed gold for **Public real-world set: HMR-100 (India)**, keyed by image file + line number. MIRAGE arXiv 2410.09729: simulated records written by doctors; handwriting/notation real, patients not. Never family data.
- `data/public_labels/bd200_gold.jsonl` — optional BD-200 notation stress labels.
- `data/real/` — **gitignored**. Unused this weekend (no family photos).
