# Public gold labels

Gold for the photographed public sets. Images stay in gitignored `data/public/`
and are **never committed**.

| File | Set | Key |
|---|---|---|
| `hmr100_gold.jsonl` | Public real-world set: HMR-100 (India) | `image` + `line_no` |
| `bd200_gold.jsonl` | Public real-world set: BD-200 (Bangladesh) | `image` + `line_no` |

Each row: transcribed `line` plus MedLine `gold` (drug, strength, form, dose,
frequency-as-slots, food, duration, ASK/`needs_check`). Illegible ⇒ ASK.

The MIRAGE paper (arXiv 2410.09729) describes HMR-100 as simulated records
written by doctors: the handwriting and notation are real; the patients are not.
Never call this family data.
