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

## Results

Eval numbers live in `eval/results.md`. Values marked `TODO` have not been measured yet. Do not invent them.

## What is real

- Synthetic training data is generated in-repo (gold JSON first, then messy text).
- Real family prescriptions live in `data/real/` (gitignored) and are never used for training.
- Post-deadline commits, if any, will be listed here.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
