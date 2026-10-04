*This is a submission for the [Hacktoberfest Weekend Challenge: Build for a Friend](https://dev.to/challenges/hacktoberfest-weekend-2026-10-01).*

## What I Built

Aaji's Pill Clerk is a prescription-copying tool for my grandparent and the family member who helps manage their medicines. It turns checked prescription text into a large-font fridge chart, calendar reminders and stock-based refill dates.

The difficult part is getting the copy right. A half tablet, a syrup concentration and a three-day course must survive the move from a slip to a schedule. The app copies written instructions; it never chooses or changes a dose. Anything unclear becomes **ASK**, and every line needs confirmation before export.

Scan accepts a local photo as a reference and manual transcription. Optional Windows OCR and local Gemma extraction are available, but handwriting probes made errors, so manual transcription remains the default. Review puts the source beside editable fields. Editing a confirmed line revokes its signoff. Chart produces Marathi, Hindi or English HTML and an `.ics` file, with the source and check record included in the copy. The app starts empty.

## Demo

[Watch the 85-second synthetic MVP demo](https://github.com/Vedant817/aaji-pill-clerk/blob/master/artifacts/acceptance/demo.mp4) or [download the MP4](https://raw.githubusercontent.com/Vedant817/aaji-pill-clerk/master/artifacts/acceptance/demo.mp4).

This recording uses a clearly marked synthetic slip and shows the earlier working MVP. A fresh check of the final code also uploaded that slip, used live hosted FT2 parsing, confirmed both lines and verified the actual chart and ICS bytes. [Final export evidence](https://github.com/Vedant817/aaji-pill-clerk/blob/master/artifacts/acceptance/final/export-verification.json).

There is no public app deployment. The repository contains local setup instructions.

## Code

{% github https://github.com/Vedant817/aaji-pill-clerk %}

The code is Apache-2.0. Training examples are synthetic; private prescriptions and public dataset photos stay out of git.

## How I Built It

The parser is a fine-tuned **Qwen3-8B**, trained and served through **Tinker**. No fine-tuned weights were downloaded, merged or converted on the laptop. Environment switches keep extraction and parsing backends replaceable. Optional local extraction uses **Gemma 4** through Ollama. Streamlit handles review, SQLite stores checked copies, and deterministic code expands the confirmed schedule and calculates refill dates from entered stock.

Training more did not automatically make it better. The newest candidate, V6, completed 615 steps, but fresh matched evaluations showed these exact clinical-field counts:

| Text cohort | Active FT2 | Candidate V6 |
|---|---:|---:|
| Synthetic, 397 lines | 397 | 351 |
| Generated notation, 102 lines | 99 | 59 |
| HMR typed text, 104 lines | 71 | 50 |

V6 also increased the HMR unflagged danger metric from 17 to 22 cases, so it was rejected. FT2 remains active. These are parser-only measurements, not handwriting accuracy or clinical validation. Exact match excludes ASK fields. The frozen historical labels also assume some units that the new candidate deliberately withholds; the comparison records that policy difference. [Training report and paired results](https://github.com/Vedant817/aaji-pill-clerk/blob/master/docs/candidate-v6.md).

Earlier saved evaluations showed the few-shot base Qwen3-8B at 53.65% exact on the synthetic set and FT2 at 100%, under that earlier evaluation pipeline. Those historical runs are distinct from the fresh comparison above. [Original results and limitations](https://github.com/Vedant817/aaji-pill-clerk/blob/master/eval/results.md).

The final suite passed **232 tests**. Four AI role reviewers checked caregiver, QA, first-time-user and PM scenarios. Their feedback led to fixes for lost written instructions, invalid edits retaining confirmation, and unknown course lengths becoming indefinite reminders. These simulations are labelled as agent tests; they are not human testimonials.

Google Calendar's actual web file import accepted all four synthetic recurring series. Read-back verified 20 occurrences, IST times, course limits and zero-minute popup reminders. The separate test calendar was then deleted. An Android emulator previously displayed reminders, and the user reported one notification on a physical Android phone for a separate non-medical test. Physical-phone recurrence and audible alarms remain unverified.

The real caregiver has not yet supplied personal-use feedback. Two independent human annotation rounds are also pending, so OCR CER remains unscored. Those gaps are reported openly; AI reference labels do not fill them.

## Why Does Open Innovation Matter?

Open weights let this project specialize a parser, retain an earlier checkpoint when a new one regresses, and swap extraction backends. Open code lets another family inspect the confirmation rules and schedule calculations, adapt the languages, and reproduce the synthetic tests without publishing a private prescription.

The photo can stay on the laptop. The configured Tinker parser receives medicine text after PII stripping, so the app is not fully offline and stripping is not guaranteed anonymisation. The value of the open approach here is control over the model, copying rules and evidence, including the freedom to reject a training run that looked promising.

## Prize Categories

- **Tinker:** hosted task-specific Qwen3-8B fine-tuning, saved baseline comparisons and explicit rejection of regressing candidates.
- **Gemma:** optional local Gemma 4 photo extraction and documented handwriting probes.

No Render or DigitalOcean deployment is claimed.

This post and implementation were prepared with an AI coding agent under the builder's instructions. All reported numbers come from saved runs; no caregiver quote, consent or clinical outcome has been invented.
