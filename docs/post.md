# Aaji's Pill Clerk — post draft

**Status:** draft. Every number below is copied from `eval/out/` (see `eval/results.md`). Local demo: http://localhost:8501. Public demo: **render.yaml provided; not deployed**. Demo video uses the **synthetic slip** (`data/demo/prescriptions/aaji_sample.txt`). HMR-100 is CC BY-ND 4.0: do not crop, blur, or publish those images.

## Problem and persona

Aaji is 74. She takes several tablets a day from more than one doctor. The prescriptions live in a plastic folder: clinic print, doctor shorthand, WhatsApp lines in Hindi, Marathi, and English. The family question is *which tablet when*, not *what should she take*.

Pill Clerk is a **clerk, not a clinician**. It copies what the slip says into a confirmed schedule, a big-font fridge chart, phone reminders (`.ics`), and refill dates. It does not suggest doses, check interactions, or interpret symptoms. Unclear fields are **ASK** in red. The chart stays locked until a human confirms every line.

## Demo

Local Streamlit: Scan → **Load demo slip** (`data/demo/prescriptions/aaji_sample.txt`) → Review (fill from Tinker, resolve ASK, confirm) → Chart (print HTML, download `.ics`). Script: `docs/demo_script.md`.

## Results

Headline sets: corrected SYNTH held-out drugs **n=397** (3 exact train duplicates dropped; gold aligned to the written line) and **Hand-written realistic n=102** (generated in code in `eval/handwritten_realistic.py`, `authored=code:eval/handwritten_realistic.py`, after FT2 at `5619cee`; **67/102** lines use train drug names; not photographed, not Vedant's handwriting).

Sources: `eval/out/b0_fair_synth_test.json`, `eval/out/ft1_synth_test.json`, `eval/out/ft2_synth_test.json`, `eval/out/b0_fair_handwritten_realistic.json`, `eval/out/ft1_handwritten_realistic.json`, `eval/out/ft2_handwritten_realistic.json`, `eval/out/gemma31_synth_test.json`, `eval/out/t_valid.json`.

| System | Exact SYNTH n=397 [95% CI] | Danger_v2_norm SYNTH | parse_fail / http_fail | Exact HW n=102 [95% CI] | Danger_v2_norm HW |
|---|---|---|---|---|---|
| B0-fair Qwen3-8B | 0.4937 [0.4458, 0.5416] | 0.3073 | 0.1940 / 0 | 0.3529 [0.2549, 0.4510] | 0.3431 |
| FT1 LoRA v1 | 0.9244 [0.8967, 0.9496] | 0.0504 | 0.0252 / 0 | 0.6471 [0.5588, 0.7451] | 0.1078 |
| FT2 LoRA v2 | 0.9798 [0.9647, 0.9924] | 0.0202 | 0 / 0 | 0.8627 [0.7941, 0.9314] | 0.0588 |
| T Gemma 4 31B (no JSON mode) | 0.8715 [0.8363, 0.9043] | 0.0101 | 0.1083 / 0.0101 | 0.6275 [0.5196, 0.7255] | 0.0098 |
| FT3 LoRA v3 (candidate) | 0.9798 [0.9647, 0.9924] | 0.0202 | 0 / 0 | 0.8824 [0.8235, 0.9412] | 0.0588 |

McNemar exact two-sided (FT1 vs FT2): SYNTH 22 fixes / 0 regressions, p = 4.76837158203125e-07; HW 25 / 3, p = 2.744048833847046e-05 (`eval/report.py`). FT3 vs FT2 SYNTH 0/0 p=1.0; HW (dev) 8/6 p=0.79052734375. Keep-rule not met (SYNTH exact not up; HMR n=0; normalised danger_v2); `.env` stays on v2.

Whole-set FT2 vs T SYNTH 8 T-fixes / 51 T-regresses, p = 9.052391166525231e-09 is a **schema-validity** win for FT2 (`parse_fail` 0.1083 plus `http_fail` 0.0101). On T-valid lines: **346/350** vs FT2 **342/350**, McNemar 8/4, p = 0.3876953125. HW T-valid **64/70** vs **64/70**, p = 1.0. `gemma31_json` (JSON mime + MedLine responseSchema) is the fairness rerun and has **not** been started. T p50 includes HTTP retries.

**Public real-world set: HMR-100 (India)** is parser-only, gold from Label REAL while looking at the image. n=0 labelled lines so far. At n≈100, 95% CIs are about ±8–9 points; do not claim a winner unless the gap exceeds that interval. Do not publish cropped or blurred HMR photos (CC BY-ND).

Gemma 4 31B is the measured 31B teacher on de-identified text (`synth_test`, `handwritten_realistic`), **no JSON mode** in the saved run. It did **not** write `train.jsonl` (all 3096 rows `renderer=template`). Local OCR (`gemma4:e4b`) is not claimed.

## Honest limits

- Training text is **template-rendered**, correct by construction. It is not doctor handwriting.
- Hand-written realistic lines were **generated in code**, not handwritten by Vedant.
- HMR scoring is parser-only (typed lines, not OCR of the photo).
- Hand-written realistic is **not drug-held-out**: 67/102 lines use names seen in train.
- FT2 was trained on the 2500-row mix at `5619cee`; later appends brought train to 3096 rows.
- `align_gold` later fixed leftover train/val labels (food without a food word, missing duration, prn_max without "max"): train 104/3096, val 15/250 (`eval/out/train_label_bugs.json`). Weights were not retrained.
- `BRAND_ALIASES` Devanagari spellings with a halant (`टेल्मा`, `पैन`) were added after seeing errors.
- Not a medical device. Always confirm with the doctor or pharmacist.

## Why open innovation matters

I could fine-tune at all because Qwen3-8B is Apache 2.0. A closed API would not let me teach Indian prescription shorthand and keep the result. Template gold trains an 8B the family can own. Gemma 4 31B (Apache 2.0) is the measured 31B teacher on the same schema, not a silent data writer. Prescription photos stay on the laptop. The clerk says ASK instead of guessing a dose.

## Safety

Clerk copy only. Red ASK means the field is missing or unreadable — fill it from the slip or ask the pharmacist. Conflicts between two copies of the same drug are shown, never resolved by the app. Fridge chart footer: not medical advice.
