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

## Fine-tune (Tinker hosted, no local GGUF)

```powershell
uv run python -m train.build_dataset --split --n-targeted 500
uv run python -m train.sft --name pillclerk-v2
uv run python -m eval.eval --system b0 --set data/synth/synth_test.jsonl
uv run python -m eval.eval --system ft1 --set data/synth/synth_test.jsonl
uv run python -m eval.eval --system ft2 --set data/synth/synth_test.jsonl
```

SFT is LoRA rank 32 on Qwen/Qwen3-8B, 3 epochs, batch 16, LR 4e-4. FT2 mixes 500 targeted rows (form/unit, food, half-tab, taper, PRN, ASK) into train. Sampler path is written to `train/checkpoint_v2.json` and `.env` `PILLCLERK_TINKER_PATH`.

## Results

Headline, SYNTH held-out drugs (n=400). Full table in `eval/results.md`. REAL photos are gitignored and not scored.

| System | JSON valid | Exact match [95% CI] | Dangerous errors | p50 s/line |
|---|---|---|---|---|
| B0 Qwen3-8B base | 0.0 | 0.00 | 1.0 | 2.15 |
| FT1 LoRA v1 | 0.97 | 0.91 [0.88, 0.94] | 0.065 | 2.18 |
| FT2 LoRA v2 | 1.0 | 0.945 [0.92, 0.97] | 0.0025 | 3.16 |

FT2 vs FT1 on the same 400 lines: 14 exact-match fixes, 0 regressions. Form/kind/taper/every_n_days/strength are 1.0 after v2. B0 emits JSON-shaped guesses that fail the MedLine schema (`dose` as `"1-0-1"`, `kind="regular"`).

## What is real

- Synthetic training data is generated in-repo (gold JSON first, then messy text).
- Real family prescriptions live in `data/real/` (gitignored) and are never used for training.
- Post-deadline commits, if any, will be listed here.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
