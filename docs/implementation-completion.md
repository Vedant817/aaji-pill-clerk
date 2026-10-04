# Remaining implementation completed — 4 October 2026

The MVP remains photo/text → checked transcription → hosted FT2 → confirmed
schedule → chart, ICS and refill dates. This follow-through completed the calendar
verification and human-evidence collection tools. It did not create human labels,
invent caregiver feedback, start another training run, or publish a deployment.

## Calendar export bridge

`pillclerk/calendar_import.py` validates the clerk's actual ICS and prepares Google
Calendar event payloads. It preserves local time, quantities in titles, daily
interval/count recurrence, private visibility and at-start reminders. It refuses
duplicate UIDs, attendees, exception rules, unsupported recurrence, ambiguous DST
times and missing alarms instead of silently dropping them. It makes no API call.

```powershell
uv run python -m scripts.prepare_calendar_import --ics path/to/pillclerk.ics --timezone Asia/Kolkata --out data/real/calendar-payloads.json
```

The output includes medicine text: keep it private. The optional `--synthetic`
flag labels test titles; no regimen or expected answers are embedded in the tool.
It does not automatically connect the app to Google or bypass Google permissions.
Native Google web import remains the simplest user route and is now explained
beside the Chart download controls.

The agent applied payloads from the actual synthetic browser ICS through the
connected Calendar tools. All four created series matched titles, local times,
counts 7/7/3/3, intervals and popup settings on read-back. All four were then
deleted and their cancelled status verified. See
[live Google ICS bridge evidence](../artifacts/acceptance/google-ics-bridge-verification.json).
This establishes the ICS-to-API path, not Google's native file-import interface
or recurrence inspection on a physical phone. The separate non-medical Android
notification was confirmed by the user earlier.

## Independent labeling

**Label Acceptance** now offers a structured form alongside Advanced JSON.
Clinical fields start blank, including every dose slot and unit. Missing drug,
daily dose and duration become null/ASK; there is no model call or prefilled gold.
Each annotator/round/page/line has separate widget state, and other annotators'
answers remain hidden. Taper steps and PRN limits can be entered explicitly.

Both different people must still label all 20 reserved images independently,
attest page completeness and resolve disagreements against the image. Existing
freeze/image-hash/agreement checks remain in force. The new form makes this
possible without writing JSON; it does not supply those people's answers.

## Caregiver and phone evidence

**Acceptance Feedback** records actual workflow and device observations locally.
The observer must choose the source (human self-report, human observer or agent
test), identify the input context, attest the observation and record sharing
permission. Every check starts `not_checked`. Phone observations require device,
calendar and timezone. Failures remain failures; agent tests remain distinct from
human reports.

Records stay in gitignored `data/real/acceptance-feedback.jsonl`. The download
contains only explicitly consented aggregate counts, divided by evidence source;
it excludes observer IDs, device details and feedback words. Nothing is sent to a
model or published automatically. These attestations cannot verify identity or
clinical correctness.

## Verification

- Full suite after role-workflow fixes: **215 tests passed** (22.78 seconds on the final run). New tests exercise rejected/ambiguous calendar
  input, actual export recurrence mapping, explicit annotation fields, consent
  filtering, attribution, and failed/successful local form submission.
  An empty record with every check unobserved cannot inflate acceptance counts.
- Actual Playwright browser: both new pages loaded; structured annotation mode
  was selected; text fields and consent/attestation were blank; saving blank forms
  failed visibly. Neither real annotation nor feedback storage was created.
- Direct feedback-page navigation also loaded after Streamlit's initial host-config
  retries. Two initial HTTP console errors occurred, but no application exception
  appeared. T3 preview was unavailable, so the authorized fallback browser was used.
- Actual Google create/read/delete checks are recorded separately from local tests.

The active parser remains FT2. The prepared next candidate is untrained; another
paid training run needs new authorization because the prior single run is complete.
Handwriting reliability remains poor and CER stays null without finalized human
gold. The existing public pages have informed development, so future improvement
claims need fresh unseen pages and independent labels.

Implementation is ready for the remaining real observations. Human participation,
native Google ICS import and physical-phone recurrence checks, alarm sound, and
publication/consented caregiver feedback cannot be replaced with simulated success.

## Agent role follow-through

### Caregiver subagent review

The user subsequently requested a caregiver-role subagent. Its observed feedback
and labelled simulated quote are saved in [simulated-caregiver-review.md](simulated-caregiver-review.md).
It reproduced omitted active History units/intervals/taper steps/PRN limits and
omitted food/course length in the PRN fridge chart. Both displays now preserve
these copied instructions; missing end dates remain described as unrecorded.
Language names and schedule labels are clearer. No clinical values were changed,
no PRN timed alarms were added, and no human acceptance record was created.

The full suite after these fixes: **220 tests passed in 14.77 seconds**. Regression
tests check PRN food/duration in English, Hindi and Marathi, absence of PRN timed
events, unknown fields staying unwritten, and active History details.

The user requested agent-operated role checks. The added tests exercise empty Scan,
ASK corrections, confirmation revocation and blocked exports, a failed parser,
new input clearing old signoffs, stock calculation, and saved history revisions.
They use synthetic inputs and temporary databases, with no paid model calls.
Existing annotation tests exercise separate rounds, disagreement, re-attestation,
changed images and frozen gold; they create no labels in the real acceptance queue.

This exposed a real implementation gap: History stored earlier copies but showed
only the active copy. It now displays the latest 100 saved revisions, their exact
fields and optional user-entered notes. Older copies do not alter the active chart.
Drug/strength HTML is escaped; notes and recorded fields display as literal text.
SQLite connections close after each operation. No patient or demo record is added.

An authenticated native Google Calendar page was reached, but the collaborative
browser host disconnected before file import. No imported series or successful
native-import result was observed; the API-bridge evidence remains separate.

The fallback browser loaded the synthetic reference image and both transcribed
lines. Live FT2 filled both copies correctly (Doxy 1/0/0.5 tab for 7 days, before
food; Ambrolite 5/0/5 ml for 3 days). The first line was confirmed and the second
reviewed. Hosted parsing took several minutes; the browser process closed before
the second confirmation/export. This repeat is partial, not a newly completed
browser acceptance. The earlier completed browser export evidence remains valid
for its recorded version, and the current complete workflow passed AppTest.

The updated server was restarted and its health endpoint returned `ok`. A fresh
fallback browser reached the History heading before its process also closed.
Direct History navigation produced two initial framework 404s for route-relative
health/host-config requests, then loaded. The cause of the browser process closure
was not established; no final screenshot or new end-to-end recording is claimed.

The current local app is running at `http://127.0.0.1:8502` with manual extraction
and a $0.05 cap per parser instance (not an account-wide limit; storage excluded).
Its health endpoint returned HTTP 200 after the final restart. For another session:

```powershell
uv run python -m scripts.run_local --port 8502 --sampling-budget-usd 0.05
```
