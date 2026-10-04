# Hosted V6 experiment - 4 October 2026

User approved up to $10 additional compute plus checkpoint storage. Existing
TINKER_API_KEY was used; no model weights were downloaded, merged or converted.
FT2 remains active. V6 is rejected; .env is unchanged.

The frozen uncertainty_v6_final candidate has 3,279 training and 280 validation
rows. Offline overlap and label consistency checks passed. A seeded 60-row AI
sample review is recorded in artifacts/acceptance/v6-audit.json; it is not human
or clinical validation. Rank 32, batch 16, three epochs, 615 steps, 1,024-token
maximum and the existing learning-rate schedule were retained. Hosted checkpoint:
train/checkpoint_pillclerk-v6.json. Training log: train/v6-run.log.

Fresh matched parser evaluation with the current recovery code:

| Cohort | FT2 exact | V6 exact | FT2 danger | V6 danger |
|---|---:|---:|---:|---:|
| Synthetic, 397 | 397 | 351 | 0 | 1 |
| Generated notation, 102 | 99 | 59 | 1 | 16 |
| HMR typed text, 104 | 71 | 50 | 17 | 22 |
| AI reference, 85, exploratory | 28 | 31 | 28 | 25 |

These counts use eval.compare_candidate exact clinical fields, excluding ASK.
Normalized evaluation differs on HMR (V6 51) and AI references (FT2 29/V6 32).
The AI reference improvement is small and exploratory; it does not outweigh the
regressions. No photographed handwriting accuracy, independent human gold,
caregiver benefit or clinical safety is established by these parser runs.

The synthetic set's 46 regressions include 45 dose errors, mostly abstention
under the candidate's changed unit policy. This policy differs from the frozen
historical evaluation labels, which assume some units. Schema validity remained
high but correctness fell. Very low validation loss did not predict generalization.
The results support retaining FT2 and revisiting label policy/coverage before any
future experiment. No additional paid run is started.

Training compute upper bound: $6.2199808. Eight sampling allocations were capped
at $0.30 each; recorded sampling upper bounds sum to $0.38554551. Combined compute
upper bound: $6.60552631, excluding checkpoint storage. Actual billed spend is
unverified. Current Tinker pricing: $0.44/M training tokens, $0.195/M input and
$0.60/M output; checkpoint storage $0.10/GB/month, verified on 4 October at
https://tinker-docs.thinkingmachines.ai/tinker/models/models_and_pricing/.

Source: eval/out/ft6_comparison.json, eight aggregate evaluation files, checkpoint
data hashes and saved raw outputs. Public prescription text and AI references
remain ignored. Runtime starts empty; synthetic fixtures stay in tests/artifacts.
