# Aaji's Pill Clerk — post draft

**Status:** draft. Every number below is copied from `eval/out/` (see `eval/results.md`). Local demo: http://localhost:8501. Public demo: **render.yaml provided; not deployed**. Demo video uses the **synthetic slip** (`data/demo/prescriptions/aaji_sample.txt`). HMR-100 is CC BY-ND 4.0: do not crop, blur, or publish those images.

## Problem and persona

Aaji is 74. She takes several tablets a day from more than one doctor. The prescriptions live in a plastic folder: clinic print, doctor shorthand, WhatsApp lines in Hindi, Marathi, and English. The family question is *which tablet when*, not *what should she take*.

Pill Clerk is a **clerk, not a clinician**. It copies what the slip says into a confirmed schedule, a big-font fridge chart, phone reminders (`.ics`), and refill dates. It does not suggest doses, check interactions, or interpret symptoms. Unclear fields are **ASK** in red. The chart stays locked until a human confirms every line.

## Demo

Local Streamlit: Scan → paste the lines from the slip → Review (fill from Tinker, resolve ASK, confirm) → Chart (print HTML, download `.ics`). Nothing is pre-loaded. Script: `docs/demo_script.md`.

## Results

Headline sets: corrected SYNTH held-out drugs **n=397** (3 exact train duplicates dropped; gold aligned to the written line) and **Hand-written realistic n=102** (generated in code in `eval/handwritten_realistic.py`, `authored=code:eval/handwritten_realistic.py`, after FT2 at `5619cee`; **67/102** lines use train drug names; not photographed, not Vedant's handwriting).

Sources: `eval/out/b0_fair_synth_test.json`, `eval/out/ft1_synth_test.json`, `eval/out/ft2_synth_test.json`, `eval/out/b0_fair_handwritten_realistic.json`, `eval/out/ft1_handwritten_realistic.json`, `eval/out/ft2_handwritten_realistic.json`, `eval/out/gemma31_synth_test.json`, `eval/out/gemma31_json_synth_test.json`, `eval/out/gemma31_json_handwritten_realistic.json`, `eval/out/t_valid.json`.

| System | Exact SYNTH n=397 [95% CI] | Danger_v2_norm SYNTH | parse_fail / http_fail | Exact HW n=102 [95% CI] | Danger_v2_norm HW |
|---|---|---|---|---|---|
| B0-fair Qwen3-8B | 0.5164 [0.4660, 0.5642] | 0.2846 | 0.1940 / 0 | 0.4412 [0.3431, 0.5392] | 0.3137 |
| FT1 LoRA v1 | 0.9421 [0.9169, 0.9622] | 0.0327 | 0.0252 / 0 | 0.8333 [0.7549, 0.9118] | 0.0980 |
| FT2 LoRA v2 | 1.0 [1.0, 1.0] | 0.0 | 0 / 0 | 0.9804 [0.9510, 1.0] | 0.0 |
| T Gemma 4 31B (no JSON mode) | 0.8715 [0.8363, 0.9043] | 0.0101 | 0.1083 / 0.0101 | 0.6471 [0.5490, 0.7451] | 0.0 |
| T JSON mode (`gemma31_json`) | 0.9622 [0.9421, 0.9798] | 0.0126 | 0 / 0.0050 | 0.9608 [0.9216, 0.9902] | 0.0098 |
| FT3 LoRA v3 (candidate) | 1.0 [1.0, 1.0] | 0.0 | 0 / 0 | 0.9020 [0.8431, 0.9608] | 0.0490 |

Official json files are `rescored_from_preds`: saved Tinker/Gemini preds run through `extra_rules(copy_explicit)`. LoRA and Gemini weights are unchanged.

McNemar exact two-sided (FT1 vs FT2): SYNTH 23 fixes / 0 regressions, p = 2.384185791015625e-07; HW 17 / 2, p = 0.000728607177734375 (`eval/report.py`). FT3 vs FT2 SYNTH 0/0 p=1.0; HW (dev) 1/9 p=0.021484375 (FT2 ahead; danger_v2_norm 0 → 0.0490). Keep-rule not met (SYNTH exact not up; HMR n=0; HW danger up); `.env` stays on v2.

Whole-set FT2 vs T (no JSON mode) SYNTH 0 T-fixes / 51 T-regresses, p = 8.881784197001252e-16 is a **schema-validity** win for FT2 (`parse_fail` 0.1083 plus `http_fail` 0.0101). On T-valid lines: **346/350** vs FT2 **350/350**, McNemar 0/4, p = 0.125. HW T-valid **66/70** vs **69/70**, p = 0.375. JSON mode closed the parse hole: SYNTH json_valid 0.9950, parse_fail 0, http_fail 0.0050, exact 0.9622 [0.9421, 0.9798], danger_v2_norm 0.0126; HW json_valid 1.0, parse_fail 0, http_fail 0, exact 0.9608 [0.9216, 0.9902], danger_v2_norm 0.0098. McNemar FT2 vs `gemma31_json`: SYNTH 0/15 p = 6.103515625e-05; HW 2/4 p = 0.6875 (tie). A fine-tuned 8B plus a copy-from-the-line parser beats JSON-mode 31B on corrected SYNTH and ties on hand-written realistic, at a quarter of the size, cheaper on Tinker. T p50 includes HTTP retries.

**Public real-world set: HMR-100 (India)** is parser-only, gold from Label REAL while looking at the image. Label REAL queues the first 30 HMR pages, pre-fills medicine names from `labels.csv`, and counts labelled/100 (shortcuts A/N/B/P). n=0 labelled lines so far. At n≈100, 95% CIs are about ±8–9 points; do not claim a winner unless the gap exceeds that interval. `scripts/run_hmr_eval_if_ready.py` then scores b0_fair, ft2, ft3, and gemma31_json. Do not publish cropped or blurred HMR photos (CC BY-ND).

Gemma 4 31B is the measured 31B teacher on de-identified text (`synth_test`, `handwritten_realistic`). Official T is **no JSON mode**; `gemma31_json` is the fairness rerun with responseMimeType + MedLine schema. It did **not** write `train.jsonl` (all 3096 rows `renderer=template`). Local OCR (`gemma4:e4b`) is not claimed.

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
