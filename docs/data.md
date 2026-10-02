# Data

- `data/drugs.csv` — public drug names, forms, strengths (committed).
- `data/patterns.yaml` — schedule and style weights (committed).
- `data/synth/` — synthetic JSONL labelled as such (committed after generation). `train.jsonl` is 2000 mix + 500 FT2 targeted rows (`targeted_v2.jsonl`) + 396 unique form/dose/food stress rows (`targeted_form_dose_food.jsonl`, 400 generated, 4 already in train). `synth_test.jsonl` is 400 lines on held-out drug names. FT2 LoRA was trained on the 2500-row mix.
- `data/demo/prescriptions/aaji_sample.txt` — synthetic Scan demo slip.
- `data/heldout/handwritten_realistic.jsonl` — Hand-written realistic (n=102), committed, never used in training. Not photographed. Must not be reported as REAL.
- `data/real/` — **gitignored**. Family photos (`raw/`) and photographed ground truth `gt.jsonl`. Write photographed labels only after photos exist.
