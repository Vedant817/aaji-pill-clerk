# Aaji's Pill Clerk

A local-first clerk that turns photos of a grandparent's handwritten (or printed) prescriptions into a **confirmed** medicine schedule, a **big-font fridge chart**, phone reminders (`.ics`), and refill dates.

This is a DEV Hacktoberfest 2026 Weekend Challenge entry ("Build for a Friend").

## Safety

**It's a clerk, not a clinician.** It copies what the prescription says into a schedule. It does **not** suggest doses, check interactions, recommend substitutes, or interpret symptoms. This README and the UI never use the words "advice" or "recommend" about medicine.

- **"ASK" is a feature.** Uncertain fields go in `needs_check` and show as **ASK** in red. They are never filled with a guess.
- **A human signs off on every line.** The chart cannot be printed until every red cell is resolved.
- **Deterministic maths.** Slot expansion, tapers, durations and refill dates are plain, unit-tested Python, never the LLM.
- **Not a medical device.** A personal family tool built in a weekend, not validated for clinical use.
- Real prescription photos and labels stay on the laptop and are gitignored. The public demo uses synthetic prescriptions only.

## What leaves the laptop

| Data | Leaves the laptop? | Where |
|---|---|---|
| Public HMR-100 / BD-200 images (`data/public/`, gitignored) | **No** | Type the line on Label REAL while looking at the image |
| Photographed family files (`data/real/`, unused this weekend) | **No** | Type the line |
| Synthetic **training** text (`data/synth/train.jsonl`, all 3096 rows `renderer=template`) | Yes | Tinker SFT only. This text never went to Gemini. |
| Synthetic eval lines (`data/synth/synth_test.jsonl`) | Yes, after PII strip | Tinker (FT eval). Gemma 4 31B teacher only when we run `--system gemma31` |
| Hand-written realistic text (n=102, not photos) | Yes, after PII strip | Tinker (FT eval); 31B teacher on the same allowlist |
| Public gold text (`data/public_labels/*.jsonl`, once labelled) | Yes, after PII strip | Tinker (FT eval) and 31B teacher. Logged in `eval/out/sent_payload_log.jsonl` |
| Confirmed clerk parse in the app | Yes, the medicine line only | Tinker hosted LoRA (`PARSER_BACKEND=tinker`) |

GEMINI_API_KEY is **text-only** for the 31B teacher on `data/synth/synth_test.jsonl`, `data/heldout/handwritten_realistic.jsonl`, and de-identified public gold jsonl. Images never leave the laptop. The code refuses `data/real/*` and `data/public/*` image paths. Synthetic training text was rendered with the Python template backend; it never went to Gemini.

## MVP line

photo → extracted lines → human confirm → fine-tuned parser → schedule → fridge chart + `.ics`

Nothing past that until the MVP runs end to end.

## This weekend's inference setup

The laptop has little free disk, so this repo **does not** download, merge, or convert the fine-tuned model locally, and it skips every GGUF/merge step. The fine-tuned Qwen3-8B is trained **and** served through **Tinker's hosted API**.

Every model call sits behind an env switch:

| Variable | Default | What it controls |
|---|---|---|
| `LLM_BACKEND` | `template` | Synthetic messy text (`template` is free). Optional: `gemini` (AI Studio), `backboard`, `tinker` |
| `EXTRACT_BACKEND` | `manual` | Paste/type lines. Photos never leave the laptop. Local `gemma4:e4b` OCR is not installed and is not claimed. |
| `PARSER_BACKEND` | `tinker` | Line → JSON (`tinker` hosted fine-tune) |

DigitalOcean is **dropped**. Gemma 4 31B is Google AI Studio (`GEMINI_API_KEY`, model `gemma-4-31b-it`). Backboard is an optional drop-in with the same chat interface. The public demo is Render free: **render.yaml provided; not deployed** (`$PORT`, synthetic data only).

## Setup

Python 3.12, package manager `uv`.

```powershell
copy .env.example .env
# fill keys only after you have them; do not commit .env
uv sync --group dev
uv run pytest
```

Keys needed (ask before spending):

- `TINKER_API_KEY` — required. Tinker Console; claim Hacktoberfest credits at https://hacktoberfest.com/my
- `GEMINI_API_KEY` — 31B teacher on synthetic + hand-written realistic **text** only. Model id `gemma-4-31b-it`. Never used for photos.
- `BACKBOARD_API_KEY` — optional. Only if `LLM_BACKEND=backboard`

## Demo (synthetic slip)

On Scan, tap **Load demo slip** (`data/demo/prescriptions/aaji_sample.txt`), then Review → Fill fields from Tinker parser → confirm every line → Chart. The chart stays locked until ASK cells are gone.

Hand-written realistic (n=102, not photographed) lives in `data/heldout/handwritten_realistic.jsonl`.

The photographed test set is **Public real-world set: HMR-100 (India)** (optional **BD-200 (Bangladesh)** as a notation stress test). MIRAGE (arXiv 2410.09729) describes HMR-100 as simulated records written by doctors: the handwriting and notation are real; the patients are not. Never call it family data. Download with `scripts/download_public.sh` into gitignored `data/public/` (HMR is CC BY-ND 4.0 — never commit images or modified copies). Label on **Label REAL**: type the line while looking at the image; `labels.csv` pre-fills the medicine name; you correct gold. Target ~100 HMR lines (~30 pages), then ~40 BD-200 lines. At n≈100, 95% CIs are about ±8–9 points; only report model differences larger than that interval.

## Fine-tune (Tinker hosted, no local GGUF)

```powershell
uv run python -m train.build_dataset --split --n-targeted 500
uv run python -m train.build_dataset --append-form-dose-food --n-form-dose-food 400
uv run python -m train.sft --name pillclerk-v2
uv run python -m eval.eval --system b0_fair --set data/synth/synth_test.jsonl
uv run python -m eval.eval --system ft1 --set data/synth/synth_test.jsonl
uv run python -m eval.eval --system ft2 --set data/synth/synth_test.jsonl
uv run python -m eval.eval --system ft2 --set data/heldout/handwritten_realistic.jsonl
```

SFT is LoRA rank 32 on Qwen/Qwen3-8B, 3 epochs, batch 16, LR 4e-4. FT2 mixes 500 targeted rows (form/unit, food, half-tab, taper, PRN, ASK) into train and was trained on the **2500-row** `train.jsonl` at git `5619cee`. Later appends added 396 unique form/dose/food stress rows then 200 drug/strength rows; **`data/synth/train.jsonl` is 3096 rows**, all `renderer=template`. Those extras are not in the v2 weights. Sampler path is written to `train/checkpoint_v2.json` and `.env` `PILLCLERK_TINKER_PATH`.

## Results

Headline numbers: SYNTH held-out drugs (n=400) and **Hand-written realistic (n=102)** (never trained, not photographed). **Public real-world set: HMR-100 (India), n=…** is scored after labelling; numbers stay TODO until `eval/out/` has a run. Full table and file paths in `eval/results.md`. Public images stay gitignored in `data/public/`.

| System | Exact SYNTH n=397 [95% CI] | Danger_v1 SYNTH | Exact hand-written realistic [95% CI] | Danger_v1 hand-written realistic | p50 s/line | Files |
|---|---|---|---|---|---|---|
| B0-fair Qwen3-8B | 0.4937 [0.4458, 0.5416] | 0.3778 | 0.3529 [0.2549, 0.4510] | 0.4510 | 3.20 | `eval/out/b0_fair_synth_test.json` · `eval/out/b0_fair_handwritten_realistic.json` |
| FT1 LoRA v1 | 0.9244 [0.8967, 0.9496] | 0.0605 | 0.6471 [0.5588, 0.7451] | 0.1471 | 2.18 | `eval/out/ft1_synth_test.json` · `eval/out/ft1_handwritten_realistic.json` |
| FT2 LoRA v2 | 0.9798 [0.9647, 0.9924] | 0.0025 | 0.8627 [0.7941, 0.9314] | 0.0490 | 3.16 | `eval/out/ft2_synth_test.json` · `eval/out/ft2_handwritten_realistic.json` |

Corrected SYNTH: gold aligned to the written line; 3 exact train duplicates dropped (n=397). Old n=400 scores live in `eval/out/*_synth_test_gold_v1.json`. FT2 vs FT1 on the same 397 SYNTH lines: 22 exact-match fixes, 0 regressions, McNemar p = 4.76837158203125e-07. On the same 102 hand-written realistic lines: 25 exact-match fixes, 3 regressions, p = 2.744048833847046e-05. Full table, danger_v2, ASK metrics, and exact_norm in `eval/results.md`. Old B0 (no few-shot) scored json_valid 0.0 because it emitted `dose="1-0-1"` and `kind="regular"`; B0-fair is the comparable baseline.

## What is real

- Synthetic training data is generated in-repo (gold JSON first, then messy text).
- **Public real-world set: HMR-100 (India)** is photographed doctor handwriting from MIRAGE (simulated patients). Gold text is in `data/public_labels/hmr100_gold.jsonl`. Images are gitignored and never used for training.
- Optional **Public real-world set: BD-200 (Bangladesh)** is a notation stress test (`1+0+1`, Bangla durations).
- Family photos are not part of this weekend's test set.

## License

Apache-2.0 for this repository. See `LICENSE` and `NOTICE`.

Third-party public sets (not redistributed as images in git):

- HMR-100 — CC BY-ND 4.0, MIRAGE arXiv 2410.09729, Hugging Face `chaithanyakota/100-handwritten-medical-records`. Do not commit images or derivatives.
- BD-200 — CC BY 4.0, Mendeley DOI [10.17632/k62rfd23kz](https://doi.org/10.17632/k62rfd23kz).
