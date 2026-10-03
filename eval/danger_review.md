# Danger review (normalised danger_v2)

A **dangerous error** (`danger_v2`, default = **normalised**) is drug, strength, dose, taper, duration_days, every_n_days, or kind wrong **and that field is not in `needs_check`**. Drug/strength use `pillclerk.normalize` (`BRAND_ALIASES`, number+unit). `danger_v2_strict` is the same fields without that normalisation. Invalid JSON is `parse_fail`. Gemini HTTP 500/503 after retries is `http_fail`. Neither is charted as danger.

`BRAND_ALIASES` includes Devanagari spellings with a halant (`टेल्मा`, `पैन`, …). **That table was written after seeing eval errors.**

Sources: `eval/out/ft2_*`, `eval/out/ft3_*`, `eval/out/gemma31_*`, `eval/out/danger_v2_review.json`. Official rows are `rescored_from_preds` through `extra_rules(copy_explicit)`. This is the hand-written realistic set plus corrected SYNTH. **Public real-world set: HMR-100 (India)** n=104 (`eval/out/ft2_hmr100_gold.json`): FT2 danger_v2_norm 0.2212, exact 0.7212.

## FT2

Hand-written realistic n=102 (`eval/out/ft2_handwritten_realistic.json`): danger_v2_norm **0.0** (0 lines), danger_v2_strict 0.0, parse_fail 0.0, http_fail 0.

Remaining inexact (not danger):

| Line | What happened | Bucket |
|---|---|---|
| `डोलो 650 जरूरत पर` | form `cap` vs gold `tab` | no form cue |
| `Duphalac 15ml subah 15ml raat khane ke baad 7 din` | stub recovered; form still misses | form |

Corrected SYNTH n=397 (`eval/out/ft2_synth_test.json`): danger_v2_norm **0.0**, exact **1.0**, parse_fail 0. Combo brand **Telma AM**, insulin units, Hindi three-slot, and missing-frequency ASK are copied from the line. LoRA weights are unchanged.

## FT3 (candidate, not applied)

Hand-written realistic n=102 (`eval/out/ft3_handwritten_realistic.json`): danger_v2_norm **0.0882** (9 lines), danger_v2_strict 0.0882, parse_fail 0.0, http_fail 0.

Dangerous lines vs FT2 (FT2 has 0):

| Line | What FT3 wrote | Bucket |
|---|---|---|
| `Ecosprin 75 raat ko ek khane ke baad` | night=1 **cap** (gold tab) | form/unit guess |
| `Pan 40 सकाळी एक जेवणाआधी 14 दिवस` | strength null, unit cap | dropped strength |
| `Wysolone 10 1-0-1 5 din then 0-0-1 5 din khane ke baad` | kind=taper, strength null | taper / strength |
| `पैन 40 सुबह एक खाने से पहले 14 दिन` | unit cap (gold tab) | form/unit |
| `Dolo 650 गरजेनुसार दिवसाला 3` | prn, empty needs_check vs gold | duration / PRN |

Parse fails (not danger): `aaji ki BP ki dawai Telma AM 40/5 subah khali pet 30 din`, `Duphalac 15ml subah 15ml raat khane ke baad 7 din`, `aaji ko Atorva 10 raat ko khane ke baad dena`.

Corrected SYNTH: exact 1.0, danger_v2_norm 0.0, tied with FT2.

## T Gemma 4 31B (no JSON mode)

Corrected SYNTH n=397 (`eval/out/gemma31_synth_test.json`): danger_v2_norm **0.1008**, parse_fail **0.0**, http_fail **0.0101** (4 HTTP 500 after retries). Valid JSON n=393 after stub recovery.

Hand-written realistic n=102 (`eval/out/gemma31_handwritten_realistic.json`): danger_v2_norm **0.2157**, parse_fail **0.0**, http_fail **0.0392** (3 HTTP 500 + 1 HTTP 503). Valid JSON n=98.

`gemma31_json` (responseMimeType + responseSchema) SYNTH danger_v2_norm **0.0126**, HW **0.0294**. Sources: `eval/out/gemma31_json_synth_test.json`, `eval/out/gemma31_json_handwritten_realistic.json`.

## Keep-rule

Keep FT3 only if exact is up on SYNTH **and** HMR with McNemar p<0.05 **and** normalised danger_v2 is not up. SYNTH exact is tied (0/0, p=1.0). HMR n=104: FT3 exact 0.6923 vs FT2 0.7212 (1/4, p=0.375); danger_v2_norm 0.2212 → 0.2596. On HW (dev) FT3 danger_v2_norm is up (0 → 0.0882). `.env` stays on FT2.

HMR FT2 vs B0-fair exact 22/5, p = 0.0015, gap ~16 points vs ±8–9 CI. Do not claim FT2 vs FT3 on HMR (CIs overlap).
