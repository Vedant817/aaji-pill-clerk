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
The candidate also includes later synthetic form/dose/food and drug/strength
examples absent from FT2's original 2,500-row training set. This run does not
isolate ASK-label corrections from the effect of that additional coverage.

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

Results: **all eight hosted evaluations completed; FT5 rejected for promotion**.
The authorized training completed all 579 steps and saved the hosted sampler in
`train/checkpoint_pillclerk-v5.json`. FT2 remains active; `.env` was not changed.

| Frozen parser cohort | FT2-current exact | FT5 exact | Unflagged danger count, FT2 → FT5 | Raw schema failures, FT2 → FT5 |
|---|---:|---:|---:|---:|
| SYNTH, n=397 | 397/397 (100%) | 397/397 (100%) | 0 → 0 | 0 → 0 |
| Generated realistic, n=102 | 100/102 (98.0%) | 79/102 (77.5%) | 0 → 22 | 1 → 1 |
| Existing HMR text, n=104 | 75/104 (72.1%) | 69/104 (66.3%) | 21 → 27 | 14 → 13 |
| AI reference, n=85, exploratory | 22/85 (25.9%) | 22/85 (25.9%) | 37 → 35 | 9 → 15 |

These danger counts use the historical `danger_v2_norm` metric, which omits form,
food and PRN-limit errors. The aggregate `eval/out/ft5_comparison.json` reports
those errors separately, matched ASK fields and selective accuracy. Generated
realistic text has 21 unflagged form mismatches for FT5 versus two for FT2.
Existing HMR exact-and-ASK falls from 62/104 to 40/104. SYNTH ASK field recall
improves from 86.5% to 100%, with five new false ASK fields; exact-and-ASK ties.
The exploratory AI-reference ASK field recall improves from 42.0% to 55.8%, but
exact match ties and raw schema failures increase. This does not justify promotion.

The paired page bootstrap 95% interval for HMR exact-match delta is −12.0 to −0.8
percentage points; on generated text, resampling lines gives −28.4 to −11.8 points.
These are development comparisons with small, previously inspected datasets,
not independent clinical validation. Concurrent evaluation load differed, so
these runs do not establish a latency improvement.

Training compute has a conservative bound of $5.83430144 and the eight actual
sampling runs total $0.38554551 in reserved-token compute bounds: **$6.21984695**.
This excludes storage and is not an invoice. The billing endpoint did not yet
return this training session's usage when queried; billed spend remains unverified.

Fresh FT2-current baseline completed: SYNTH 397/397 exact, generated realistic
100/102, existing HMR 75/104, and AI reference 22/85 (exploratory). Raw schema
failures: 0, 1, 14 and 9 respectively. The HMR fresh result does not reproduce the
83/104 offline replay; original predictions had already been postprocessed.
Do not present replay as fresh inference. The new reference is deliberately
conservative about missing forms, quantities and durations, while historical
HMR gold has sparse ASK flags. Scores against those two label policies are not
directly comparable clinical accuracy measurements.

## Remaining accuracy work

The candidate training rows all contain an explicit form cue, while 27/102
generated evaluation lines omit it. Historical gold often presumes a tablet in
those cases. This is a coverage and label-policy gap: adding brand lookups or
guessing a form would conflict with the clerk's copy-only rule. The observed
association does not isolate the cause of the training regression.

1. Define a consistent source-faithfulness policy for omitted form, quantity and
   units; preserve the old benchmark and version any corrected labels separately.
2. Add synthetic hard negatives with omitted form/units and unreadable text,
   balanced with simple prescriptions. Keep neutral values and ASK rather than
   inferred clinical fields, and inspect a reproducible sample before training.
3. Investigate conservative structural recovery for unsupported enum values,
   retaining valid copied fields while flagging the invalid field. Verify against
   frozen raw outputs before any new provider calls. This repair is not implemented.
4. Test a controlled training change, such as fewer epochs or a lower learning
   rate, separately from dataset changes. A second paid training run needs new
   authorization; the approved single run has been completed.
5. Complete caregiver correction and calendar-import acceptance. The assistant's
   AI labels cannot replace independent human review or establish clinical accuracy.

## Verification — 4 October

The full pytest suite passed (168 tests). The paired comparison ran against all
four frozen cohorts and validated dataset hashes. Candidate train/validation
hashes match its saved checkpoint. The configured hosted sampler matches FT2's
checkpoint; no environment update occurred. Original synthetic and public gold
files have no diff. New AI reference labels/raw outputs remain gitignored, and
fresh artifacts contain none of the configured API key values.
Fresh HMR line-level predictions/raw text also stay local; only their aggregate
results are committed. Rebuilding the full comparison requires these local files.
