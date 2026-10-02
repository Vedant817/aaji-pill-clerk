# Danger review (normalised danger_v2)

A **dangerous error** (`danger_v2`, default = **normalised**) is drug, strength, dose, taper, duration_days, every_n_days, or kind wrong **and that field is not in `needs_check`**. Drug/strength use `pillclerk.normalize` (`BRAND_ALIASES`, number+unit). `danger_v2_strict` is the same fields without that normalisation. Invalid JSON is `parse_fail`. Gemini HTTP 500/503 after retries is `http_fail`. Neither is charted as danger.

`BRAND_ALIASES` includes Devanagari spellings with a halant (`टेल्मा`, `पैन`, …). **That table was written after seeing eval errors.**

Sources: `eval/out/ft2_*`, `eval/out/ft3_*`, `eval/out/gemma31_*`, `eval/out/danger_v2_review.json`. This is the hand-written realistic set plus corrected SYNTH. **Public real-world set: HMR-100 (India)** gold is empty (n=0).

## FT2

Hand-written realistic n=102 (`eval/out/ft2_handwritten_realistic.json`): danger_v2_norm **0.0588** (6 lines), danger_v2_strict 0.1275, parse_fail 0.0098, http_fail 0.

| Line | What happened | Bucket |
|---|---|---|
| `Tab Telma AM 40mg/5mg OD ES 1/12` | pred drug `Telma` | combo brand |
| `Lantus 12 unit raat ko` | night=1, strength=`12 unit` | insulin units eaten by strength |
| `SYR. Ascoril LS AFTER FOOD x 5 DAYS` | invented morning=1 ml, empty needs_check | guessed a missing dose |
| `aaji ki BP ki dawai Telma AM 40/5 subah khali pet 30 din` | pred drug `Telma` | combo brand |
| `Refresh Tears drops subah dopahar raat 15 din` | 1-0-0 drop | Hindi three-slot collapsed to OD |
| `Novorapid 6 unit subah dopahar raat khane se pehle` | 1-0-0 tab, strength=`6 unit` | insulin units + form |

Parse fail (not danger): `Duphalac 15ml subah 15ml raat khane ke baad 7 din`.

Corrected SYNTH n=397 (`eval/out/ft2_synth_test.json`): danger_v2_norm **0.0202** (8 lines), all held-out combo brand **Telma AM** copied as `Telma`. parse_fail 0.

## FT3 (candidate, not applied)

Hand-written realistic n=102 (`eval/out/ft3_handwritten_realistic.json`): danger_v2_norm **0.0588** (6 lines), danger_v2_strict 0.0686, parse_fail 0.0294, http_fail 0.

New dangerous lines vs FT2 (same 6-count, different rows):

| Line | What FT3 wrote | Bucket |
|---|---|---|
| `Ecosprin 75 raat ko ek khane ke baad` | night=1 **cap** (gold tab) | form/unit guess |
| `Pan 40 सकाळी एक जेवणाआधी 14 दिवस` | strength null, unit cap | dropped strength |
| `Wysolone 10 1-0-1 5 din then 0-0-1 5 din khane ke baad` | kind=taper, strength null | taper / strength |
| `पैन 40 सुबह एक खाने से पहले 14 दिन` | unit cap (gold tab) | form/unit |
| `Tab Telma AM 40mg/5mg OD ES 1/12` | pred drug `Telma` | combo brand (still) |
| `Dolo 650 गरजेनुसार दिवसाला 3` | prn, empty needs_check vs gold prn_max | PRN max |

Parse fails (not danger): `aaji ki BP ki dawai Telma AM 40/5 subah khali pet 30 din`, `Duphalac 15ml subah 15ml raat khane ke baad 7 din`, `aaji ko Atorva 10 raat ko khane ke baad dena`.

Corrected SYNTH: same 8 Telma AM lines as FT2 (danger_v2_norm 0.0202). Exact tied with FT2.

## T Gemma 4 31B (no JSON mode)

Corrected SYNTH n=397 (`eval/out/gemma31_synth_test.json`): danger_v2_norm **0.0101** (4 lines), parse_fail **0.1083**, http_fail **0.0101** (4 HTTP 500 after retries). Valid JSON n=350.

Hand-written realistic n=102 (`eval/out/gemma31_handwritten_realistic.json`): danger_v2_norm **0.0098** (1 line: `Novorapid 6 unit subah dopahar raat khane se pehle` → 1-1-1 unit), parse_fail **0.2745**, http_fail **0.0392** (3 HTTP 500 + 1 HTTP 503). Valid JSON n=70.

`gemma31_json` (responseMimeType + responseSchema) has not been run. Ask before that paid/quota eval.

## Keep-rule

Keep FT3 only if exact is up on SYNTH **and** HMR with McNemar p<0.05 **and** normalised danger_v2 is not up. SYNTH exact is tied (0/0, p=1.0). HMR gold n=0. `.env` stays on FT2.

Do not claim a public-set winner until n is labelled and the gap is larger than the 95% CI (about ±8–9 points at n≈100).
