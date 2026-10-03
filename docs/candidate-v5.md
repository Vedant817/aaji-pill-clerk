# Candidate v5 — 3 October 2026

The user authorized the assistant to do the labeling work and up to **$10** in
Tinker credits for one hosted Qwen3-8B training run plus fresh parser evaluation.
The active FT2 sampler remains unchanged. No model weights are downloaded,
merged or converted. Tinker's client may fetch its public tokenizer files.

## Data review

The read-only candidate audit found zero schema/copy-rule disagreements and zero
rule-filter failures. Those checks share code with the generator and do not prove
label accuracy. Thirty training lines were inspected by the assistant using seed
20261003, including fractions, multilingual text, taper, PRN and injection lines.
This is AI inspection, not clinical or independent human signoff.

All 3,079 train / 249 validation rows were audited for duration uncertainty.
**92 train and 10 validation** examples had null duration, no explicit continuation
and no duration ASK. They contradicted the system prompt's missing-duration rule.
`train.review_candidate` adds only `duration_days` to `needs_check`, rebuilds the
assistant target, and prepares `data/candidates/safety_v5/`. Source v4, published
gold and clinical fields stay fixed. Review samples, coverage and per-row deltas
are in `safety_v5/curation_inputs/{review,changes}.json`.

```powershell
uv run python -m train.review_candidate
uv run python -m train.sft --train data/candidates/safety_v5/train.jsonl --val data/candidates/safety_v5/val.jsonl --name pillclerk-v5 --plan --max-compute-usd 6.1
```

## Local AI references

The assistant inspected every original image in the 20-page reserved manifest,
without medicine-name metadata or model predictions, and entered 85 medicine-line
drafts. `scripts.prepare_ai_reference` validates image hashes and freezes local
`data/reference/hmr_ai_v1/ai_reference.jsonl`. Labels record `ai_single_agent`,
`human_verified=false`, `double_checked=false`, and exploratory status.
Unclear drug names and unsupported schedules/quantities abstain. Drafts include
editorial context and uncertainty markers, so they are not exact OCR transcriptions.
References have zero normalized-text overlap with candidate training.

These are not two independent annotation rounds. Both rounds of the separate
human acceptance workflow remain empty. Public source images and new derivative
texts stay gitignored; the page manifest and code are committed. AI reference
gold is not used for training, model-generated clinical advice or caregiver exports.

## Budget and trainer changes

The verified [Qwen3-8B pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/models_and_pricing/)
is $0.44/M train/forward tokens, $0.195/M prefill and $0.60/M sample tokens.
The training plan bounds 579 steps across three epochs, with 58 validation calls
on 64 rows and a maximum of 1,024 tokens/example: **13,259,776 tokens / $5.834302**
compute. The trainer refuses above a $6.10 compute allocation before paid calls.
Each of eight evaluation runs has a $0.30 sampling allocation; maximum requested
training plus sampling compute is $8.234302. These are compute bounds, not a
provider invoice; checkpoint storage is excluded.

The trainer now includes the final partial batch. Both tokenizer paths reject
oversized examples instead of silently cutting a JSON target. Evaluations use an
explicit checkpoint file with a separate experiment name, preserving `.env`.
Tinker raw JSON, stop reason, token counts and schema-recovery events are saved;
raw schema failure is reported separately from recovered-output validity.

## Comparison

Fresh FT2-current and FT5 runs use the same pipeline and cohorts: SYNTH (397 after
the existing original-train exclusion), generated realistic (102), existing HMR
(104, development data), and AI reference (85, exploratory). SYNTH still uses the
historical 397-row reporting cohort even though the new candidate excludes those
original overlaps. No original scores are overwritten.

`eval.compare_candidate` reports whole-line exact, exact with matching ASK flags,
ASK field precision/recall, selective coverage/accuracy, danger counts and separate
unflagged form/food/PRN errors. HMR confidence intervals resample pages, not isolated
lines. McNemar remains a line-level exploratory statistic. No score measures image
reading, independent clinical accuracy or caregiver acceptance.

Results: **pending completion of the actual hosted runs**. FT2 stays active until
results are available and a candidate's behavior justifies a separate promotion.
