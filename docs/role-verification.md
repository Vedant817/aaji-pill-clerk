# Caregiver, QA, user and PM verification — 4 October 2026

All four reviewers are AI subagents. Their synthetic role tests and feedback are
not caregiver testimonials, independent human annotations, consent or clinical
validation. No hosted model calls or real prescription records were used.
The first attempts hit a provider usage limit and produced no reviews; after
retry, all four supplied evidence-backed findings.

## Findings and fixes

- QA reproduced a confirmed line remaining exportable after an invalid dose
  edit. Review now revokes confirmation before stopping on dose or taper errors.
- QA reproduced literal medicine markup being interpreted in the conflict
  banner. The complete conflict description is now escaped.
- Caregiver/PM found unknown duration labelled “continue,” producing unbounded
  reminders. Zero now means unrecorded. Unknown duration stays ASK and exports
  are blocked unless the reviewer explicitly verifies that the prescription
  says to continue without an end date. The attestation is stored separately and
  resets when the course changes; no end date is invented.
- QA/PM found copied eye/site instructions disappearing from outputs. Review
  now offers an editable written-instructions field; the checked copy survives
  HTML, calendar description, Google import payload and active/saved History.
- PM requested source/check provenance. Chart requires a source reference and
  checker initials before download/save. Prescription date starts blank and can
  remain “not recorded.” Checker date, chart start, reminder times and continuation
  attestations are retained in saved revisions. Legacy records gain empty context
  without invented attribution. Calendar/chart times use the recorded settings;
  conflicting explicit settings are rejected.
- User requested plain food labels and printing instructions. Both are present,
  while enum values remain unchanged. Marathi/Hindi operational instructions,
  source/check records and safety footers are localized.
- PM identified publication-draft omissions. The open-innovation answer and
  current test attribution are updated. Public video/publication remain pending;
  no online demo link was invented.

## Independent verification

- **Caregiver:** 14 targeted tests plus independent AppTest checks passed after
  the fixes. Missing duration/source/checker gates, written instructions,
  translated footers, History details and printing guidance were exercised.
- **QA:** full suite of 231 tests passed at its reviewed working-tree snapshot,
  plus independent checks for duration changes, note edits, clearing checker,
  escaping, actual calendar payloads and populated legacy database migration.
  One 12 KB synthetic temporary database remains outside the repository. After
  the harness exited, automatic approval review rejected exact-file,
  non-recursive cleanup as “blocked by policy.” No escalation or alternate
  deletion was attempted. This is not an app-store failure or a real record.
  Subsequent time-consistency regression is verified in the final suite.
- **User:** initial offline Scan → manual Review → Chart/refill/temporary History
  checks passed, including readable language/schedule values and no preset data.
  After the fixes, it repeated the journey with unknown-course and source/checker
  gates, copied notes, explicit continuation and invalid edits. No new practical
  blocker or page exception was reproduced; stored enums remained unchanged.
- **PM:** 26 targeted tests passed after the implementation fixes. It found no
  remaining blocking implementation defect in that pass; context localization
  and publication text identified during review were completed afterward.

The final parent-run suite passed **232 tests in 37.94 seconds**, including the
added regression that rejects export times conflicting with saved provenance.

## Simulated caregiver feedback after fixes

> “I can now check the written site, course length and maximum doses without
> losing them in the chart. The source and checker fields help me recognize which
> copy was checked. I understand that a missing course length needs clarification,
> and the printing instructions give me a clear next step.”

Source: `caregiver_verify`, **agent_test**, after reverification. Keep this label
if quoting it. Real caregiver use/permission, independent human gold, native
Google ICS import, physical-phone recurrence/timezone and audible alarms remain
unverified. Earlier emulator, Google API bridge and user-reported notification
evidence remain separate from these role tests.
