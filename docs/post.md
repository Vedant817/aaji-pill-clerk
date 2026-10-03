# Aaji's Pill Clerk: copying a prescription into a confirmed chart

**Submission draft, 4 October 2026. Not published.** Add publication links and genuine caregiver feedback before submitting. Family handover and independent human validation remain unverified. Do not invent a quote, age, medical history, consent, or outcome.

## Who this is for

I am building this for a grandparent and the family member who helps keep track of their medicines. A prescription can contain several languages and shorthand such as `1-0-1` or a half tablet at night. The goal is to copy the written instructions into something easier to check and use.

Pill Clerk only copies the prescription. It never chooses or changes a dose. Unclear fields show **ASK**, and every medicine line must be confirmed before the chart or reminders can be exported. Clarification comes from the doctor or pharmacist.

## What the app does

Scan accepts a local photo or pasted text. Optional Windows OCR uses the installed engine without downloading a model or uploading an image; local Ollama is another extraction option. Extracted text must be checked against the photo before loading it. Windows OCR has only been exercised on a clean, explicitly synthetic printed slip; handwriting accuracy is unverified.

The checked text goes to a Qwen3-8B parser served through Tinker. Review shows the original line beside editable fields. Chart produces a large-font printable HTML chart in Marathi, Hindi, or English and an `.ics` file with reminder alarms. Refill dates use stock entered by the caregiver. The app starts empty; no patient or demo regimen is loaded automatically.

Tinker parsing is hosted, so this is not a fully offline app. Photos stay local, while medicine text is sent to the configured parser after the app's PII stripping. That stripping is a precaution, not a guarantee of anonymisation.

## What the measurements actually show

The fresh FT2 parser runs saved on 3 October used the pipeline at that time:

| Text evaluation | Exact clinical fields | Unflagged danger metric |
|---|---:|---:|
| Corrected held-out synthetic lines | 397/397 | 0/397 |
| Code-generated realistic notation | 100/102 | 0/102 |
| Public HMR text labels | 75/104 | 21/104 |

Sources: `eval/out/ft2_current_synth_test.json`, `ft2_current_handwritten_realistic.json`, and `ft2_current_hmr100_gold.json`. Exact match excludes ASK fields. The generated set is not photographed handwriting and is not fully drug-held-out. HMR contains simulated records written by doctors; it is not family data. These are parser-only measurements, not end-to-end OCR accuracy or proof of clinical safety.

Later safety changes were replayed against those saved raw outputs: HMR exact became **71/104**, while unflagged danger cases fell to **17/104**, partly through more abstention. This is offline development replay, not a fresh benchmark of the latest code. Source: `eval/out/structural_recovery_replay.json`.

One corrected candidate, FT5, was trained within the approved budget. It regressed on generated text and HMR, so FT2 remains active. A further synthetic candidate is prepared but untrained. AI reference labels for reserved pages are exploratory and do not replace two independent human annotation rounds.

## What building it taught me

High synthetic accuracy can hide problems in real notation. Template generation does not guarantee correct labels: the audit found missing uncertainty flags and dose-unit errors, and the corrected candidate records those fixes. General schema recovery now preserves uncertainty instead of converting an invalid dose into a guessed value.

Browser testing also found that returning to Review could lose widget values. Review now restores its fields and resolved ASK checks from the saved draft. A confirmed line must still be confirmed again after an edit.

## Before publication

- Add the real repository URL and verified synthetic-demo video link.
- Record actual caregiver use, their permission to share feedback, and their own words. **TODO: real handover.**
- Verify importing the exported `.ics` in the intended phone calendar and check recurrence, timezone, and alarm behaviour. **TODO: device acceptance.**
- Keep private prescription files and public dataset photos out of screenshots and recordings.

The repository uses Apache-2.0. The fine-tuned model is trained and served through Tinker; no local weight download, merge, or GGUF conversion is required. Google AI Studio teacher comparisons are historical text-only experiments, not the source of the template training data. Public deployment is not claimed.
