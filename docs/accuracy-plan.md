# Accuracy audit and implementation plan — 3 October 2026

The current measured model is FT2. FT3 failed its keep rule and remains a candidate.
The public set is doctor-written simulated records, manually transcribed; it is not
family data and does not measure handwriting extraction. The app uses hosted Tinker
sampling, so it requires a network. Scan now accepts a local reference photo while
the caregiver types its medicine lines. Automated photo extraction is not verified.

## Evidence from saved runs

| FT2 dataset | Lines | Saved whole-line exact | Saved unflagged dangerous errors | Saved ASK recall |
|---|---:|---:|---:|---:|
| Synthetic held-out drugs | 397 | 397/397 (100%) | 0 | 70.6% |
| Generated realistic text | 102 | 100/102 (98.0%) | 0 | 100% |
| Public HMR typed text | 104 | 75/104 (72.1%) | 23/104 (22.1%) | 60% |

Source: `eval/out/ft2_*_preds.jsonl`, re-scored by `python -m eval.audit`.
The synthetic result is template generalization, not real prescription accuracy.
The generated realistic set shares training vocabulary and is not independently
authored. The public set has no second labeller documented. Its labels and model
outputs have already informed parser development; future gains need a fresh test.

The existing `exact` metric excludes `needs_check` and note. On HMR, requiring
matching ASK fields as well gives only **67/104 (64.4%)**, both before and after this
change. JSON validity is measured after recovery/postprocessing, not necessarily
raw model schema success. Missing strength units can match under normalized scoring;
strict metrics must remain visible. `danger_v2_norm` excludes form, food and PRN-limit
errors, and cannot substitute for a clinical safety assessment. A statistical
non-significant difference between FT2 and the teacher does not prove equivalence.

## Implemented in this iteration

- Confirmation is revoked after any field edit. Parser ASK flags survive Review
  until explicitly checked against the prescription; invalid fields cannot export.
- Conflicting copies block outputs, including conflicts in strength, food, duration
  or taper. Unsupported clocks, exclusions, monthly schedules, hourly/QID schedules,
  ambiguous frequency ranges and multi-drug nebule instructions block export even
  if someone ticks confirmation. They must be clarified and re-entered on Scan.
- General copy rules support leading `T`, numeric `2/3 times a day`, after-meal food
  cues, and explicitly written weekly night dosing. No prescription-specific answer
  map was added. Explicit clock times remain blocked rather than replaced by a slot.
- Charts show actual units, course dates, sequential taper dates, intervals and
  reminder times. Taper steps can be reviewed and edited. Calendar intervals use
  ceiling division, so a 30-day weekly course has five events, not four. UIDs include
  prescription content to avoid collisions with unrelated schedules.
- Caregiver reminder times are editable. Stock is blank per medicine, in its dose
  unit. Refill calculations follow actual dosing days and respect course length.
  PRN and taper refill estimates remain unsupported and are not fabricated.
- Missing fine-tuned configuration cannot silently select the base model. Per-line
  provider failures retain the unresolved draft, and initialization failures are
  shown without printing secrets. Review honors both parser backend switches.
- Removed the unused demo prescription. Prompt examples and transliteration aliases
  are reference JSON in `pillclerk/resources`, separate from patient data. The app
  starts empty. All `data/real/` contents are now ignored recursively.
- Training checks for normalized train/validation/evaluation overlap before any
  paid client creation. Current files contain **six train/validation overlaps and
  three train/synthetic-test overlaps**; the published SYNTH score excluded the
  latter. Old weights and saved results are preserved. Future checkpoint metadata
  includes dataset SHA-256 hashes.
- Offline replay pairs by exact source line, rejects duplicate/missing evidence,
  hashes input files and scorer code, and writes a separate report without changing
  official results or making provider calls. Paired comparisons reject reordered
  lines instead of silently comparing unrelated prescriptions.

## Measured offline replay

Run `uv run python -m eval.audit`. Output: `eval/out/accuracy_audit.json`.

| FT2 replay | Exact before → after | Unflagged danger before → after | ASK recall before → after |
|---|---|---|---|
| SYNTH n=397 | 100% → 100% | 0 → 0 | 70.6% → 70.6% |
| Generated realistic n=102 | 98.0% → 98.0% | 0 → 0 | 100% → 100% |
| HMR n=104 | 72.1% → **79.8% (83/104)** | 23 → **14 (13.5%)** | 60% → **80%** |

HMR has eight exact fixes and zero exact regressions; paired McNemar p=0.0078125.
This is replay of **already postprocessed** saved predictions, not fresh inference,
an independent test, a new weight checkpoint, or an OCR measurement. An unchanged
joint exact-and-ASK score means the whole-line improvement does not imply that all
uncertainty flags improved. Existing official scores and latency remain unchanged.
Replay confidence intervals retain the existing line-level bootstrap convention;
lines share prescription pages, so a future independent test should bootstrap by
page/family rather than treat every line as independent.

Remaining replay misses: strength 8, drug 7, dose 7, duration 3, interval 3, PRN
limit 3, food 1, form 1, kind 1. Multiple fields can fail on one line.

## Ordered next work

1. **Clean candidate data, before another training run.** Keep published gold fixed.
   Deduplicate candidate training against validation and every evaluation set,
   including normalized text. Freeze manifests for data, prompt, copy rules and
   checkpoint. Run `uv run python -m train.sft --check-data` before spending; it
   currently refuses the leaky dataset. Do not rely on very low validation NLL
   while six validation examples occur in train.
2. **Independent acceptance set.** Reserve previously unlabelled prescription pages
   before developing against them; have two people transcribe and reconcile gold
   against images. Mark unsupported notation ASK rather than inventing an interval.
   Record page provenance, source text and adjudication. Do not move HMR error lines
   into training and then report the same set as held out.
3. **Improve training coverage.** Generate independent synthetic examples of generic
   names with brands in parentheses, combination strengths, tablet-prefix notation,
   numeric frequency phrases, fractional doses and food cues. Include hard negatives
   for missing form/quantity, unreadable text, exact clocks, complex weekly calendars,
   mixtures and hourly PRN. Avoid inferring PRN maxima from hourly spacing unless
   explicitly written. Balance these with the existing simple cases; FT3 regressed
   after targeted augmentation. Hand-check a reproducible sample before training.
4. **Separate model, recovery and human outcomes.** Capture raw Tinker completions
   and finish reasons, raw schema failures, recovered outputs, exact-and-ASK, field
   abstention precision/recall, and selective accuracy/coverage. Report form/food/PRN
   safety errors separately. Compare all models with the same frozen postprocessing
   and examples. Keep HTTP failures distinct from parsing failures.
5. **Hosted candidate training and fresh evaluation — costs require approval.** Use
   Tinker only; no local weights, merging or GGUF. Do not update `.env` automatically.
   Keep FT2 until the independent test improves without increased dangerous errors,
   and rerun all regression datasets with the same pipeline. Gemini teacher remains
   optional; approve its run separately. No new hosted calls were made in this audit.
6. **End-to-end acceptance before release.** Test a consented local photo → manually
   confirmed text → hosted parser → review correction → chart → real calendar import.
   Check half-dose, syrup, taper, weekly, PRN and conflicting-copy cases. Record human
   correction rate and caregiver feedback. OCR CER remains TODO until local vision
   is installed with enough disk and measured against confirmed transcriptions.
7. **Deadline discipline.** Finish correctness and acceptance on Sunday, reserve time
   for a truthful demo and write-up, and stop feature work Monday 5 October at 10:00
   IST. Submission deadline remains 12:29 IST. Do not claim a deployment, offline
   parser, automated OCR, family handover or clinical accuracy without evidence.

## Validation

3 October follow-through: [dataset decision and workflow](dataset-selection.md).
Clean candidate prepared at `data/candidates/clean_v4` (3,079 / 249 rows), offline
training checks passed, and 20 unused HMR pages reserved at
`data/acceptance/hmr_v1/manifest.json`. Two-person labels and synthetic sample
review remain pending. No new training, paid calls, or model accuracy results.

Use `uv run pytest` for schema, notation, scheduling, calendar, review and offline
evidence regressions. Streamlit AppTest exercises actual page widgets for edit
revocation, unresolved ASK flags, blank stock and conflict-blocked downloads.
It is local component execution, not authenticated browser or phone verification.
