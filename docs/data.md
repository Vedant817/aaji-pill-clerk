# Data

- `data/drugs.csv` — public drug names, forms, strengths (committed).
- `data/patterns.yaml` — schedule and style weights (committed).
- `data/synth/` — synthetic JSONL labelled as such (committed after generation). `train.jsonl` is 2000 mix + 500 FT2 targeted rows (`targeted_v2.jsonl`). `synth_test.jsonl` is 400 lines on held-out drug names.
- `data/demo/prescriptions/aaji_sample.txt` — synthetic Scan demo slip.
- `data/real/` — **gitignored**. Family photos and REAL test labels never enter git.
