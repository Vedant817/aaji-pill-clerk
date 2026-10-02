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

## MVP line

photo → extracted lines → human confirm → fine-tuned parser → schedule → fridge chart + `.ics`

Nothing past that until the MVP runs end to end.

## This weekend's inference setup

The laptop has little free disk, so this repo **does not** download, merge, or convert the fine-tuned model locally, and it skips every GGUF/merge step. The fine-tuned Qwen3-8B is trained **and** served through **Tinker's hosted API**.

Every model call sits behind an env switch:

| Variable | Default | What it controls |
|---|---|---|
| `LLM_BACKEND` | `template` | Synthetic messy text (`template` is free). Optional: `backboard`, `tinker`, `digitalocean` |
| `EXTRACT_BACKEND` | `manual` | Paste/type lines. Optional: `ollama` local `gemma4:e4b`, or `hosted` Gemma (DO) |
| `PARSER_BACKEND` | `tinker` | Line → JSON (`tinker` hosted fine-tune) |

DigitalOcean is **optional**. The MVP does not need a DO card. Backboard is an optional drop-in with the same chat interface.

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
- `DO_MODEL_ACCESS_KEY` — optional. Skip if you do not want to add a card.
- `BACKBOARD_API_KEY` — optional. Only if `LLM_BACKEND=backboard`

## Demo (synthetic slip)

On Scan, tap **Load demo slip** (`data/demo/prescriptions/aaji_sample.txt`), then Review → Fill fields from Tinker parser → confirm every line → Chart. The chart stays locked until ASK cells are gone.

To add photographed family lines: transcribe on **Label REAL**, or `uv run python -m eval.family_real` then `uv run python -m eval.eval --system ft2 --set data/heldout/real_style.jsonl`.

## Fine-tune (Tinker hosted, no local GGUF)

```powershell
uv run python -m train.build_dataset --split --n-targeted 500
uv run python -m train.build_dataset --append-form-dose-food --n-form-dose-food 400
uv run python -m train.sft --name pillclerk-v2
uv run python -m eval.eval --system b0 --set data/synth/synth_test.jsonl
uv run python -m eval.eval --system ft1 --set data/synth/synth_test.jsonl
uv run python -m eval.eval --system ft2 --set data/synth/synth_test.jsonl
uv run python -m eval.eval --system ft2 --set data/heldout/real_style.jsonl
```

SFT is LoRA rank 32 on Qwen/Qwen3-8B, 3 epochs, batch 16, LR 4e-4. FT2 mixes 500 targeted rows (form/unit, food, half-tab, taper, PRN, ASK) into train. A later append added 396 unique form/dose/food stress rows (`train.jsonl` n=2896); those extras are not in the v2 weights. Sampler path is written to `train/checkpoint_v2.json` and `.env` `PILLCLERK_TINKER_PATH`.

## Results

Headline numbers: SYNTH held-out drugs (n=400) and REAL-style family slips (n=102, never used in training). Full table in `eval/results.md`. Raw family photos stay gitignored in `data/real/raw/`.

| System | Exact SYNTH [95% CI] | Danger SYNTH | Exact REAL [95% CI] | Danger REAL | p50 s/line |
|---|---|---|---|---|---|
| B0 Qwen3-8B base | 0.00 | 1.0 | 0.00 | 1.0 | 2.15 |
| FT1 LoRA v1 | 0.91 [0.88, 0.94] | 0.065 | 0.647 [0.559, 0.745] | 0.147 | 2.18 |
| FT2 LoRA v2 | 0.945 [0.92, 0.97] | 0.0025 | 0.863 [0.794, 0.931] | 0.049 | 3.16 |

FT2 vs FT1 on the same 400 SYNTH lines: 14 exact-match fixes, 0 regressions. On the same 102 REAL-style lines: 25 exact-match fixes, 3 regressions; danger 15 → 5. Form/kind/taper/every_n_days/strength are 1.0 on new SYNTH after v2. REAL food is 0.990, form 0.971, dose 0.951. B0 emits JSON-shaped guesses that fail the MedLine schema (`dose` as `"1-0-1"`, `kind="regular"`).

## What is real

- Synthetic training data is generated in-repo (gold JSON first, then messy text).
- Real family prescriptions live in `data/real/` (gitignored) and are never used for training.
- Post-deadline commits, if any, will be listed here.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
