# Eval results

Numbers in this file come only from `eval/eval.py` runs. Values marked TODO have not been measured.

FT1 SYNTH (`data/synth/synth_test.jsonl`, n=400) was sampled once on Tinker, then **rescored** with `eval.eval --preds` after a `0` vs `0.0` JSON dump bug in `field_eq` (dose/taper). Same preds, no second Tinker pass. Raw first-pass dump (`exact` 0.12, `dose` 0.26) is not the score.

| System | JSON valid | Exact match (REAL) [95% CI] | Dangerous errors (REAL) | Exact match (SYNTH) [95% CI] | Dangerous errors (SYNTH) | p50 s/line (laptop) | ₹ / 1k lines |
|---|---|---|---|---|---|---|---|
| B0 Qwen3-8B base | TODO | TODO | TODO | TODO | TODO | TODO | TODO |
| B1 Gemma 4 E4B | TODO | TODO | TODO | TODO | TODO | TODO | 0 |
| FT1 Qwen3-8B + LoRA v1 | TODO | TODO | TODO | 0.80 [0.76, 0.84] | 0.105 | 2.17 | 0 (Tinker hosted) |
| FT2 Qwen3-8B + LoRA v2 | TODO | TODO | TODO | TODO | TODO | TODO | 0 (Tinker hosted) |
| T Gemma 4 31B (DO) | TODO | TODO | TODO | TODO | TODO | n/a (API) | TODO |

FT1 SYNTH per-field (n=400, json_valid 0.99): drug 0.9775 · strength 0.99 · form 0.8875 · kind 0.99 · dose 0.8925 · every_n_days 0.99 · taper 0.99 · food 0.9125 · duration_days 0.9875 · prn_max_per_day 0.985. p95 3.18 s/line.

Per-field accuracy (REAL), FT2 vs B0: drug `TODO` · strength `TODO` · dose `TODO` · food `TODO` · duration `TODO` · taper `TODO` · prn `TODO`.
