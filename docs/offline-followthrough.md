# Offline safety follow-through — 4 October 2026

FT2 stays active. No hosted requests, training, key changes or model downloads
were made in this step. No model accuracy improvement is claimed.

## Parser changes

Tinker and Ollama now share `process_completion`. Field recovery retains
structurally valid values and replaces invalid fields with neutral values plus
ASK. Invalid dose units are not converted: dose stays null. Invalid taper,
interval or kind withholds the schedule. Malformed JSON, whole-object consistency
errors and invalid ASK lists still use the source stub. Raw schema failure stays
visible separately from the schema-valid recovered output.

Recovery preserves the former stub's ASK fields. Retained values that differ
from that conservative fallback also require review. A recognized form may be
copied from an explicit source token; recovery has no drug-specific lookups.
Source copying cannot overwrite withheld dose/schedule fields.

Even schema-valid completions now retain model ASK flags through source copying.
If the model left dose null and flagged it, it remains null until the caregiver
resolves it. Previously, source-copy heuristics could fill a slot pattern and
remove dose/schedule ASK before Review received it.

## Actual offline replay

`uv run python -m eval.replay_recovery` uses saved raw FT2-current/FT5 completions
and frozen cohorts. It records input/code hashes, recovery counts, paired changes,
ASK-field metrics and selective coverage in `eval/out/structural_recovery_replay.json`.
Hosted-run files are unchanged.

| FT2-current cohort | Exact, saved → replay | Unflagged danger count, saved → replay |
|---|---:|---:|
| SYNTH, 397 | 397 → 397 | 0 → 0 |
| Generated realistic, 102 | 100 → 100 | 0 → 0 |
| HMR typed text, 104 | 75 → 71 | 21 → 17 |
| Local AI reference, 85, exploratory | 22 → 28 | 37 → 28 |

HMR has one exact fix and five regressions: null/neutral fields replace some
previous predictions, so historical gold matches fall. Exact-and-ASK falls from
62/104 to 60/104; selective coverage falls from 73.1% to 71.2%. The danger reduction
includes abstention and is not higher model accuracy. The historical danger metric
excludes form, food and PRN-limit errors; separate counts are in the report. No
fresh inference, image reading or latency improvement is measured.

FT5 remains rejected: SYNTH 397 → 397 exact, generated text 79 → 79, HMR 69 → 65
and AI reference 22 → 28. HMR danger falls 27 → 23 and AI-reference danger 35 → 26.
AI labels are single-agent exploratory references, not independent human gold,
OCR transcriptions or clinical acceptance.

## Prepared synthetic candidate

`uv run python -m train.prepare_uncertainty` freezes
`data/candidates/uncertainty_v6_final/`: **3,279 train / 280 validation rows**.
It starts from safety_v5 and changes no published evaluation labels.

The conservative candidate policy is: omitted form with no remaining form cue
uses `other`, null dose and ASK dose/schedule; an unwritten liquid/device
administration unit uses null dose and ASK dose. A concentration denominator
such as `10 mg/5 ml` is not an administration-unit cue. The policy differs from
historical gold that assumes units; old labels remain frozen.

- 100 train / 20 validation missing-form examples derived from synthetic sources.
- 351 train / 21 validation unit-label corrections, retaining source and other
  fields. Deltas are in `curation_inputs/unit_changes.json`.
- 100 train / 11 validation explicit-unit positives, using quantities already
  present in synthetic gold. Existing solid-dose positives remain.

Ten actual samples were inspected by the assistant: five omitted-form negatives
and five explicit-unit positives. Every prepared target aligns with gold; every
clear daily liquid/device dose has a written administration unit. The cleaner
reports zero normalized-text train/validation overlaps or checked overlaps with
SYNTH, generated text, existing HMR/BD and local AI references. These checks share
code with preparation; they do not establish independent accuracy or eliminate
template similarity and prior exposure.

Initial preparation attempts remain ignored local scratch folders. Only the final
candidate is committed. It is **not trained or promoted**. The previously approved
single training run was completed; another paid run requires new authorization.
Avoid combining these label changes with multiple optimizer changes in that run.

## Verification and next step

The full suite passes: **180 tests**, including field salvage, invalid units,
taper fallback, malformed ASK, null-dose uncertainty, synthetic-source restrictions,
concentration handling and explicit-unit positive generation. The active sampler
still matches FT2. No runtime prescription/demo preload was introduced; public raw
text and AI labels stay local.

Next, review the unit policy and a larger candidate sample before a controlled
hosted experiment. Caregiver correction and real calendar-import acceptance remain
needed; neither is represented by replay.
