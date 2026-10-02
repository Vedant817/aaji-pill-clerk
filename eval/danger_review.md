# Danger review (FT2)

A **dangerous error** is dose, taper, duration, every_n_days, or kind wrong **and** `needs_check` empty. The clerk copied a schedule a human would not have flagged as ASK.

Source: `eval/out/ft2_handwritten_realistic.json` (n=102, danger 0.049 → 5 lines) and `eval/out/ft2_handwritten_realistic_preds.jsonl`. SYNTH danger is 1/400 (`eval/out/ft2_synth_test.json`).

This is the hand-written realistic set, not **Public real-world set: HMR-100 (India)**. Public gold is not scored yet.

## The five handwritten misses

| Line | What gold says | What FT2 wrote | Bucket |
|---|---|---|---|
| `Lantus 12 unit raat ko` | night=12 unit | night=1, strength="12 unit" | insulin units eaten by strength |
| `SYR. Ascoril LS AFTER FOOD x 5 DAYS` | dose null, needs_check dose/schedule | invented morning=1 ml, empty needs_check | guessed a missing dose |
| `Refresh Tears drops subah dopahar raat 15 din` | 1-1-1 drop | 1-0-0 drop | Hindi three-slot collapsed to OD |
| `Duphalac 15ml subah 15ml raat khane ke baad 7 din` | 15-0-15 ml | invalid JSON (pred null) | parse fail |
| `Novorapid 6 unit subah dopahar raat khane se pehle` | 6-6-6 unit, injection | 1-0-0 tab, strength="6 unit" | insulin units + form |

## Pattern

Insulin/unit lines and missing-dose ASK are the remaining danger. FT3 extras target combo brands and odd strengths (`train.build_dataset --append-drug-strength`). Keep FT3 only if exact match rises and this danger count does not rise, on handwritten realistic **and** on Public real-world set: HMR-100 (India) once labelled, with McNemar vs FT2.

Do not claim a public-set winner until n is labelled and the gap is larger than the 95% CI (about ±8–9 points at n≈100).
