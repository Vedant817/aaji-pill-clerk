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
| Photographed prescriptions (`data/real/raw/`) | **No** | Local Ollama `gemma4:e4b`, or you type the line |
| Photographed gold lines (`data/real/gt.jsonl`) | **No** | Never Gemini, never any teacher API |
| Hand-written realistic text (n=102, not photos) | Yes, after PII strip | Gemma 4 31B teacher (`gemma-4-31b-it`), logged in `eval/out/sent_payload_log.jsonl` |
| Synthetic eval/train text | Yes, after PII strip | Same 31B teacher log; Tinker SFT/sampling for the clerk |
| Confirmed clerk parse in the app | Yes, the medicine line only | Tinker hosted LoRA (`PARSER_BACKEND=tinker`) |

GEMINI_API_KEY is **text-only** for the 31B teacher on `data/synth/synth_test.jsonl` and `data/heldout/handwritten_realistic.jsonl`. The code refuses `data/real/*`.

## MVP line

photo → extracted lines → human confirm → fine-tuned parser → schedule → fridge chart + `.ics`

Nothing past that until the MVP runs end to end.

## This weekend's inference setup

The laptop has little free disk, so this repo **does not** download, merge, or convert the fine-tuned model locally, and it skips every GGUF/merge step. The fine-tuned Qwen3-8B is trained **and** served through **Tinker's hosted API**.

Every model call sits behind an env switch:

| Variable | Default | What it controls |
|---|---|---|
| `LLM_BACKEND` | `template` | Synthetic messy text (`template` is free). Optional: `gemini` (AI Studio), `backboard`, `tinker` |
| `EXTRACT_BACKEND` | `manual` | Paste/type lines. Optional: `ollama` local `gemma4:e4b`. Photos never leave the laptop. |
| `PARSER_BACKEND` | `tinker` | Line → JSON (`tinker` hosted fine-tune) |

DigitalOcean is **dropped**. Gemma 4 31B is Google AI Studio (`GEMINI_API_KEY`, model `gemma-4-31b-it`). Backboard is an optional drop-in with the same chat interface. The public demo is Render free (`render.yaml`, `$PORT`, synthetic data only).

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

Hand-written realistic (n=102, not photographed) lives in `data/heldout/handwritten_realistic.jsonl`. Photographed family lines: put photos in `data/real/raw/` (gitignored) and label on **Label REAL**. Target ≥80 medicine lines from whatever slips the family has. WhatsApp screenshots are optional. If n < 50, report it as a **small real set** with 95% CIs shown prominently.

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

SFT is LoRA rank 32 on Qwen/Qwen3-8B, 3 epochs, batch 16, LR 4e-4. FT2 mixes 500 targeted rows (form/unit, food, half-tab, taper, PRN, ASK) into train. A later append added 396 unique form/dose/food stress rows (`train.jsonl` n=2896); those extras are not in the v2 weights. Sampler path is written to `train/checkpoint_v2.json` and `.env` `PILLCLERK_TINKER_PATH`.

## Results

Headline numbers: SYNTH held-out drugs (n=400) and **Hand-written realistic (n=102)** (never trained, not photographed). Full table and file paths in `eval/results.md`. Raw family photos stay gitignored in `data/real/raw/`.

| System | Exact SYNTH [95% CI] | Danger SYNTH | Exact hand-written realistic [95% CI] | Danger hand-written realistic | p50 s/line | Files |
|---|---|---|---|---|---|---|
| B0-fair Qwen3-8B | 0.475 [0.428, 0.525] | 0.38 | 0.353 [0.255, 0.451] | 0.451 | 3.20 | `eval/out/b0_fair_synth_test.json` · `eval/out/b0_fair_handwritten_realistic.json` |
| FT1 LoRA v1 | 0.91 [0.88, 0.94] | 0.065 | 0.647 [0.559, 0.745] | 0.147 | 2.18 | `eval/out/ft1_synth_test.json` · `eval/out/ft1_handwritten_realistic.json` |
| FT2 LoRA v2 | 0.945 [0.92, 0.97] | 0.0025 | 0.863 [0.794, 0.931] | 0.049 | 3.16 | `eval/out/ft2_synth_test.json` · `eval/out/ft2_handwritten_realistic.json` |

FT2 vs FT1 on the same 400 SYNTH lines: 14 exact-match fixes, 0 regressions. On the same 102 hand-written realistic lines: 25 exact-match fixes, 3 regressions; danger 15 → 5. Form/kind/taper/every_n_days/strength are 1.0 on new SYNTH after v2. Hand-written realistic food is 0.990, form 0.971, dose 0.951. Old B0 (no few-shot) scored json_valid 0.0 because it emitted `dose="1-0-1"` and `kind="regular"`; B0-fair is the comparable baseline.

## What is real

- Synthetic training data is generated in-repo (gold JSON first, then messy text).
- Real family prescriptions live in `data/real/` (gitignored) and are never used for training.
- Post-deadline commits, if any, will be listed here.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
