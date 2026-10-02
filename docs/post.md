# Aaji's Pill Clerk — post draft

**Status:** draft. Every number below is copied from `eval/out/` (see `eval/results.md`). The T (Gemma 4 31B) row stays TODO until `eval/out/gemma31_synth_test.json` and `eval/out/gemma31_handwritten_realistic.json` exist with full n. Local demo: http://localhost:8501. Public demo: **render.yaml provided; not deployed**.

## Problem and persona

Aaji is 74. She takes several tablets a day from more than one doctor. The prescriptions live in a plastic folder: clinic print, doctor shorthand, WhatsApp lines in Hindi, Marathi, and English. The family question is *which tablet when*, not *what should she take*.

Pill Clerk is a **clerk, not a clinician**. It copies what the slip says into a confirmed schedule, a big-font fridge chart, phone reminders (`.ics`), and refill dates. It does not suggest doses, check interactions, or interpret symptoms. Unclear fields are **ASK** in red. The chart stays locked until a human confirms every line.

## Demo

Local Streamlit: Scan → **Load demo slip** (`data/demo/prescriptions/aaji_sample.txt`) → Review (fill from Tinker, resolve ASK, confirm) → Chart (print HTML, download `.ics`). Script: `docs/demo_script.md`.

## Results

Headline sets: corrected SYNTH held-out drugs **n=397** (3 exact train duplicates dropped; gold aligned to the written line) and **Hand-written realistic n=102** (authored by Vedant after FT2 at `5619cee`; **67/102** lines use train drug names; not photographed).

Sources: `eval/out/b0_fair_synth_test.json`, `eval/out/ft1_synth_test.json`, `eval/out/ft2_synth_test.json`, `eval/out/b0_fair_handwritten_realistic.json`, `eval/out/ft1_handwritten_realistic.json`, `eval/out/ft2_handwritten_realistic.json`.

| System | Exact SYNTH n=397 [95% CI] | Danger_v1 SYNTH | Danger_v2 SYNTH | Exact HW n=102 [95% CI] | Danger_v1 HW | Danger_v2 HW |
|---|---|---|---|---|---|---|
| B0-fair Qwen3-8B | 0.4937 [0.4458, 0.5416] | 0.3778 | 0.3073 | 0.3529 [0.2549, 0.4510] | 0.4510 | 0.4020 |
| FT1 LoRA v1 | 0.9244 [0.8967, 0.9496] | 0.0605 | 0.0504 | 0.6471 [0.5588, 0.7451] | 0.1471 | 0.2843 |
| FT2 LoRA v2 | 0.9798 [0.9647, 0.9924] | 0.0025 | 0.0202 | 0.8627 [0.7941, 0.9314] | 0.0490 | 0.1275 |
| T Gemma 4 31B | TODO | TODO | TODO | TODO | TODO | TODO |
| FT3 LoRA v3 (candidate) | 0.9798 [0.9647, 0.9924] | 0.0025 | 0.0202 | 0.8824 [0.8235, 0.9412] | 0.0686 | 0.0686 |

McNemar exact two-sided (FT1 vs FT2): SYNTH 22 fixes / 0 regressions, p = 4.76837158203125e-07; HW 25 / 3, p = 2.744048833847046e-05 (`eval/report.py`). FT3 vs FT2 SYNTH 0/0 p=1.0; HW (dev) 8/6 p=0.79052734375. Keep-rule not met (SYNTH exact not up; HMR n=0); `.env` stays on v2. Sources: `eval/out/ft3_synth_test.json`, `eval/out/ft3_handwritten_realistic.json`.

**Public real-world set: HMR-100 (India)** is parser-only, gold from Label REAL while looking at the image. n=0 labelled lines so far. At n≈100, 95% CIs are about ±8–9 points; do not claim a winner unless the gap exceeds that interval.

Gemma 4 31B is the eval ceiling on de-identified text (`synth_test`, `handwritten_realistic`, public gold text). It did **not** write `train.jsonl` (all 3096 rows `renderer=template`). Local OCR (`gemma4:e4b`) is not claimed.

## Honest limits

- Training text is **template-rendered**, correct by construction. It is not doctor handwriting.
- One labeller typed the hand-written realistic gold.
- HMR scoring is parser-only (typed lines, not OCR of the photo).
- Hand-written realistic is **not drug-held-out**: 67/102 lines use names seen in train.
- FT2 was trained on the 2500-row mix at `5619cee`; later appends brought train to 3096 rows.
- Not a medical device. Always confirm with the doctor or pharmacist.

## Why open innovation matters

I could fine-tune at all because Qwen3-8B is Apache 2.0. A closed API would not let me teach Indian prescription shorthand and keep the result. Template gold trains an 8B the family can own. Gemma 4 31B (Apache 2.0) is the measured ceiling on the same schema, not a silent data writer. Prescription photos stay on the laptop. The clerk says ASK instead of guessing a dose.

## Safety

Clerk copy only. Red ASK means the field is missing or unreadable — fill it from the slip or ask the pharmacist. Conflicts between two copies of the same drug are shown, never resolved by the app. Fridge chart footer: not medical advice.
