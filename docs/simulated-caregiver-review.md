# Simulated caregiver review — 4 October 2026

Source: **AI subagent `caregiver_review`, agent_test**. Requested by the user.
This is a caregiver-role usability review, not personal use by the intended
caregiver, human consent, independent annotation, phone verification or clinical
validation. No human acceptance record or private prescription was created.

## Method and observed behavior

The reviewer inspected the actual local Scan screen through the collaborative
browser. It used Streamlit AppTest for the complete workflow with synthetic
fixtures and temporary/mocked storage, avoiding hosted calls. These methods are
reported separately; no new browser-completed workflow is claimed.

- Empty Scan shows an instruction rather than loading a regimen.
- ASK blocks confirmation; checking acknowledgments alone does not supply a
  missing drug or dose. Manual correction allows confirmation and exports.
- A half tablet prints as `½ tab`. Editing a confirmed field locks Chart again.
- Stock starts blank. The synthetic stock calculation for two tablets at 1½/day
  reports next-day depletion.
- Calendar instructions describe computer import, Android sync, notification
  settings and recurrence checks. The reviewer did not import a calendar or
  observe a physical-phone notification.

## Feedback and resulting fixes

The reviewer reproduced two display defects:

1. A PRN medicine with food after meals, a three-day course and maximum two/day
   lost food and course length in the printed chart. The chart now preserves
   those copied fields in all three languages. PRN still creates no timed events.
2. Active History cards omitted syrup units, alternate-day intervals, taper steps
   and PRN limits. Those saved fields now appear in the active summary. A missing
   end date displays as unrecorded, rather than being described as continuation.

The reviewer also judged raw language codes and schedule jargon confusing.
Chart now shows Marathi, Hindi and English names. Review shows “Schedule type,”
“Scheduled doses,” “When needed (PRN),” and “Taper (changing doses).” The repeat
interval includes an explanation. Stored schema values are unchanged.

## First-person feedback — simulated caregiver

> “I could follow Scan → Review → Chart, and the blocked confirmation made me
> check missing information. The half-tablet display and stock unit were clear.
> I would need help understanding PRN and the language abbreviations. For an
> as-needed medicine, I need the fridge chart to retain the prescribed food
> instruction and course length.”

This quote is from the AI subagent before the final fixes. It must remain labelled
as simulated feedback if reused; it is not a caregiver testimonial.

Regression checks are in `tests/test_role_workflows.py` and
`tests/test_chart_prn.py`. They exercise actual page output and exported HTML/ICS,
with synthetic data restricted to tests. The final full suite passed **220 tests
in 14.77 seconds**. This verifies the implementation, not human acceptance.
