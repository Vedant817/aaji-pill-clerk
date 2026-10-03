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
| Confirmed clerk parse in the app | Yes, after PII strip | Tinker hosted LoRA (`PARSER_BACKEND=tinker`). `make_tinker_parser` calls `strip_pii` before sampling. |

GEMINI_API_KEY is **text-only** for the 31B teacher on `data/synth/synth_test.jsonl`, `data/heldout/handwritten_realistic.jsonl`, and de-identified public gold jsonl. Images never leave the laptop. The code refuses `data/real/*` and `data/public/*` image paths. Synthetic training text was rendered with the Python template backend; it never went to Gemini. Tinker **eval and app** sampling now strip PII on the line; Tinker **SFT** still sends the synthetic `train.jsonl` rows as written (no patient PII in that file).

## MVP line

photo → extracted lines → human confirm → fine-tuned parser → schedule → fridge chart + `.ics`

Nothing past that until the MVP runs end to end.

## This weekend's inference setup

The laptop has little free disk, so this repo **does not** download, merge, or convert the fine-tuned model locally, and it skips every GGUF/merge step. The fine-tuned Qwen3-8B is trained **and** served through **Tinker's hosted API**.

Every model call sits behind an env switch:

| Variable | Default | What it controls |
|---|---|---|
| `LLM_BACKEND` | `template` | Synthetic messy text (`template` is free). Optional: `gemini` (AI Studio), `backboard`, `tinker` |
| `EXTRACT_BACKEND` | `manual` | Paste/type lines; optional `windows` uses installed local OCR, or `ollama` uses a locally installed vision model. Handwriting accuracy is unverified. |
| `PARSER_BACKEND` | `tinker` | Line → JSON (`tinker` hosted fine-tune) |

DigitalOcean is **dropped**. Gemma 4 31B is Google AI Studio (`GEMINI_API_KEY`, model `gemma-4-31b-it`). Backboard is an optional drop-in with the same chat interface. Public demo: **render.yaml provided; not deployed** (`$PORT`, synthetic data only).

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

## Use the clerk

On Scan, paste medicine lines, or upload a photo and use the configured local extractor. Windows OCR was exercised on one clean synthetic printed image; this does not establish handwriting accuracy. Check extracted text against the photo, remove non-medicine lines, then sign off before loading. Review fills from Tinker and asks you to confirm each line. Chart stays locked until every line is confirmed and ASK cells are resolved. Nothing is pre-loaded.

```powershell
# Uses process-only overrides; does not change .env or download a model.
uv run python -m scripts.run_local --windows-ocr --sampling-budget-usd 0.05
```

The optional sampling cap applies to each parser instance and excludes storage;
it is not an account-wide spending limit. Windows OCR uses installed language
support (`WINDOWS_OCR_LANGUAGE=en-US`). Other systems can use manual input or
an already installed Ollama model. Source changes require restarting the app;
file watching is disabled to avoid probing optional Transformers vision modules.

Browser acceptance uses an explicitly synthetic fixture outside runtime code.
See [verification evidence and remaining acceptance](docs/browser-acceptance.md).
Calendar event times are floating local times (08:00 remains 08:00 in the
importing calendar's timezone). Verify the intended phone's import and alarms.

Hand-written realistic (n=102, not photographed) lives in `data/heldout/handwritten_realistic.jsonl`.

The photographed test set is **Public real-world set: HMR-100 (India)** (optional **BD-200 (Bangladesh)** as a notation stress test). MIRAGE (arXiv 2410.09729) describes HMR-100 as simulated records written by doctors: the handwriting and notation are real; the patients are not. Never call it family data. Download with `scripts/download_public.sh` into gitignored `data/public/` (HMR is CC BY-ND 4.0 — never commit images or modified copies). Label on **Label REAL**: type the line while looking at the image; `labels.csv` pre-fills the medicine name; you correct gold. Target ~100 HMR lines (~30 pages), then ~40 BD-200 lines. At n≈100, 95% CIs are about ±8–9 points; only report model differences larger than that interval.

## Fine-tune (Tinker hosted, no local GGUF)

```powershell
uv run python -m train.build_dataset --split --n-targeted 500
uv run python -m train.build_dataset --append-form-dose-food --n-form-dose-food 400
uv run python -m train.sft --name pillclerk-v2
uv run python -m train.build_dataset --write-ft3-danger --n-ft3-danger 200
uv run python -m eval.overlap --extra data/synth/targeted_ft3_danger.jsonl
uv run python -m train.sft --name pillclerk-v3 --extra data/synth/targeted_ft3_danger.jsonl --log train/ft3_sft.log
uv run python -m eval.eval --system b0_fair --set data/synth/synth_test.jsonl
uv run python -m eval.eval --system ft1 --set data/synth/synth_test.jsonl
uv run python -m eval.eval --system ft2 --set data/synth/synth_test.jsonl
uv run python -m eval.eval --system ft2 --set data/heldout/handwritten_realistic.jsonl
```

SFT is LoRA rank 32 on Qwen/Qwen3-8B, 3 epochs, batch 16, LR 4e-4. FT2 mixes 500 targeted rows (form/unit, food, half-tab, taper, PRN, ASK) into train and was trained on the **2500-row** `train.jsonl` at git `5619cee`. Later appends added 396 unique form/dose/food stress rows then 200 drug/strength rows; **`data/synth/train.jsonl` is 3096 rows**, all `renderer=template`. Those extras are not in the v2 weights. Sampler path is written to `train/checkpoint_v2.json` and `.env` `PILLCLERK_TINKER_PATH`. FT3 mixes `targeted_ft3_danger.jsonl` (200 rows) at SFT time via `--extra`; it does **not** rewrite `train.jsonl`. v3 is not written to `.env` unless `--apply-env` after the keep-rule (exact up on SYNTH+HMR, McNemar p<0.05, normalised danger_v2 not up).

## Results

4 October offline follow-through: [recovery changes and prepared candidate](docs/offline-followthrough.md).
Invalid fields now require ASK while valid fields can survive schema recovery;
model ASK flags and unresolved null doses survive source copying. Saved FT2 HMR
raw-output replay is 71/104 exact with 17 unflagged danger cases (previously 75/104
and 21), partly through abstention. This is offline replay, not fresh accuracy.
The new 3,279/280-row synthetic candidate is prepared but untrained; FT2 stays active.

The authorized FT5 candidate run is complete: **3,079 synthetic training / 249
validation rows**, with corrected duration ASK labels and zero checked text
overlaps. **FT5 was rejected; FT2 remains active.** Fresh matched exact scores are
FT2 → FT5: SYNTH 100% → 100%, generated realistic 98.0% → 77.5%, and HMR typed text
72.1% → 66.3%. Unflagged dangerous errors also increased on both latter cohorts.
See [the candidate report and remaining accuracy work](docs/candidate-v5.md).
Twenty reserved HMR pages have 85 local AI reference labels; those results are
exploratory. Independent human labeling rounds remain empty. See
[dataset selection and labeling instructions](docs/dataset-selection.md).
Preparation is offline and does not change the active model:

```powershell
uv run python -m train.prepare_candidate
uv run python -m train.sft --train data/candidates/clean_v4/train.jsonl --val data/candidates/clean_v4/val.jsonl --check-data
uv run streamlit run app/Home.py  # Independent prescription labels page
```

3 October audit: see [accuracy issues and improvement plan](docs/accuracy-plan.md).
Offline replay of saved FT2 HMR predictions improves exact from **75/104 (72.1%)**
to **83/104 (79.8%)**, with unflagged dangerous errors **23 → 14**. This is development
replay of existing predictions, not new model inference or photo accuracy. Official
saved scores below remain unchanged. The `exact` metric excludes ASK flags; SYNTH
FT2 ASK recall is only **70.6%** despite its 100% exact score.

```powershell
uv run python -m eval.audit
uv run python -m train.sft --check-data  # offline; refuses current split leakage
```

Headline numbers: SYNTH held-out drugs (n=397) and **Hand-written realistic (n=102)** (never trained, not photographed). **Public real-world set: HMR-100 (India), n=104**: FT2 exact **0.7212** [0.6346, 0.8077], danger_v2_norm **0.2212**; T JSON **0.6442** [0.5577, 0.7308], danger_v2_norm **0.2596**, http_fail **0.0385** (`eval/out/ft2_hmr100_gold.json`, `eval/out/gemma31_json_hmr100_gold.json`). Full table in `eval/results.md`. Public images stay gitignored in `data/public/`.

| System | Exact SYNTH n=397 [95% CI] | Danger_v2_norm SYNTH | parse_fail / http_fail SYNTH | Exact HW n=102 [95% CI] | Danger_v2_norm HW | Files |
|---|---|---|---|---|---|---|
| B0-fair Qwen3-8B | 0.5365 [0.4887, 0.5869] | 0.4534 | 0 / 0 | 0.5294 [0.4314, 0.6275] | 0.4314 | `eval/out/b0_fair_synth_test.json` · `eval/out/b0_fair_handwritten_realistic.json` |
| FT1 LoRA v1 | 0.9446 [0.9194, 0.9647] | 0.0554 | 0 / 0 | 0.8333 [0.7549, 0.9118] | 0.1471 | `eval/out/ft1_synth_test.json` · `eval/out/ft1_handwritten_realistic.json` |
| FT2 LoRA v2 | 1.0 [1.0, 1.0] | 0.0 | 0 / 0 | 0.9804 [0.9510, 1.0] | 0.0 | `eval/out/ft2_synth_test.json` · `eval/out/ft2_handwritten_realistic.json` |
| FT3 LoRA v3 (candidate) | 1.0 [1.0, 1.0] | 0.0 | 0 / 0 | 0.9020 [0.8431, 0.9608] | 0.0882 | `eval/out/ft3_synth_test.json` · `eval/out/ft3_handwritten_realistic.json` |
| T Gemma 4 31B (no JSON mode) | 0.8816 [0.8463, 0.9118] | 0.1008 | 0 / 0.0101 | 0.7157 [0.6176, 0.8039] | 0.2157 | `eval/out/gemma31_synth_test.json` · `eval/out/gemma31_handwritten_realistic.json` |
| T JSON mode (`gemma31_json`) | 0.9824 [0.9673, 0.9924] | 0.0126 | 0 / 0.0050 | 0.9608 [0.9216, 0.9902] | 0.0294 | `eval/out/gemma31_json_synth_test.json` · `eval/out/gemma31_json_handwritten_realistic.json` |

Corrected SYNTH: gold aligned to the written line; 3 exact train duplicates dropped (n=397). Old n=400 scores live in `eval/out/*_synth_test_gold_v1.json`. Official rows are `rescored_from_preds` through `copy_explicit` (same LoRA/Gemini payloads). FT2 vs FT1 on the same 397 SYNTH lines: 22 exact-match fixes, 0 regressions, McNemar p = 4.76837158203125e-07. On the same 102 hand-written realistic lines (generated in code, not handwritten by Vedant): 17 exact-match fixes, 2 regressions, p = 0.000728607177734375. FT3 vs FT2 SYNTH: 0/0, p=1.0 (tied exact 1.0; ASK recall 0.7059 → 0.9412). FT3 vs FT2 HW (dev): 1/9, p=0.021484375 (FT2 ahead). Keep-rule not met (SYNTH exact not up; HMR FT3 0.6923 vs FT2 0.7212, p=0.375; HW danger_v2_norm 0 → 0.0882); v3 is not in `.env`. T-valid (non-HTTP after stub recovery): **350/393** vs FT2 **393/393** (`eval/out/t_valid.json`). HW T-valid **73/98** vs **96/98**. JSON mode SYNTH exact **0.9824** [0.9673, 0.9924]; HW exact **0.9608**. McNemar FT2 vs `gemma31_json`: SYNTH 0/7 p = 0.015625; HW 2/4 p = 0.6875 (tie). HMR n=104 FT2 exact **0.7212** vs B0 0.5577, p = 0.0015; vs `gemma31_json` 0.6442, 10/18, p = 0.185 (tie). T p50 includes HTTP retries; do not compare it to Tinker latency. Full table in `eval/results.md`. Old B0 (no few-shot) scored json_valid 0.0 because it emitted `dose="1-0-1"` and `kind="regular"`; B0-fair is the comparable baseline.

## What is real

- Synthetic training data is generated in-repo (gold JSON first, then messy text).
- **Public real-world set: HMR-100 (India)** is photographed doctor handwriting from MIRAGE (simulated patients). Gold text is in `data/public_labels/hmr100_gold.jsonl`. Images are gitignored and never used for training. Label on **Label REAL** (`uv run streamlit run app/Home.py --server.port 8501`): first 30 pages by default, medicine names pre-filled from `labels.csv`, shortcuts A/N/B/P, labelled/100 counter. At n≥100, `scripts/run_hmr_eval_if_ready.py` scores b0_fair, ft2, ft3, and gemma31_json.
- Optional **Public real-world set: BD-200 (Bangladesh)** is a notation stress test (`1+0+1`, Bangla durations).
- Family photos are not part of this weekend's test set.

## License

Apache-2.0 for this repository. See `LICENSE` and `NOTICE`.

Third-party public sets (not redistributed as images in git):

- HMR-100 — CC BY-ND 4.0, MIRAGE arXiv 2410.09729, Hugging Face `chaithanyakota/100-handwritten-medical-records`. Do not commit images or derivatives.
- BD-200 — CC BY 4.0, Mendeley DOI [10.17632/k62rfd23kz](https://doi.org/10.17632/k62rfd23kz).
