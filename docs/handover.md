# Handover: using Pill Clerk at home

This is a **clerk**. It copies the prescription into a chart. It does not decide doses. **Always confirm with the doctor or pharmacist** if anything looks different from the paper slip.

## How to photograph (public HMR labelling, or a family slip later)

1. Daylight. Fill the frame with the medicine lines. One slip per photo.
2. Cover faces, letterhead, and phone numbers.
3. Hindi / Marathi / Hinglish lines are useful. Type what you see, including `[?]` for unreadable letters.
4. Keep the photo local. On **Scan**, type the line or use a configured local extractor. Check every character against the photo and remove headings before signing off the extracted text. Windows OCR and local Gemma made transcription errors on a 20-page handwriting probe; use manual transcription whenever the copy is unclear.

## What a red ASK means

A red **ASK** cell means the clerk is not sure about that field (drug, dose, schedule, duration, …). It refused to guess.

- Look at the original line.
- Fill the field from what is written, or leave it empty and ask the pharmacist before you confirm.
- The fridge chart stays locked until every ASK is resolved and you confirm each line.

## Printing the chart

1. Scan (or paste) the lines → Review → confirm every line.
2. Open **Chart**.
3. Enter a prescription reference and checker initials in **Source and check record**.
   Leave prescription date blank if it is not recorded; do not invent it.
4. Pick the start date and language (Marathi / Hindi / English).
5. Download **fridge-chart.html**, open it in your browser and choose Print with landscape orientation.
6. The footer includes the source/check record and says it is a clerk copy, not medical advice.

Copy other written instructions, such as an eye/site, on Review. A course length
of zero means no end date was recorded; it does not mean continue. If the
prescription explicitly instructs continuation without an end date, verify that
instruction using the separate checkbox. Otherwise leave ASK and seek clarification.

## Importing the `.ics`

1. On Chart, download **reminders.ics**.
2. For Google Calendar, import it on a computer into the same account used on the Android phone, then sync the phone. Follow [the Google Calendar acceptance steps](android-google-calendar.md). Other calendar apps may support direct phone import.
3. Alarms follow the slot times on the chart (morning / afternoon / night).
4. SOS / PRN medicines are listed as “when needed”, not as timed alarms.
5. Reminder times are local wall-clock times in the importing calendar. Check the calendar's timezone, the first and last date, the dose/unit, and whether alarms are enabled. Imported files do not prove that a phone will display an alarm.

The tested account-free Android path is Fossify Calendar: **Settings → Import events from an ICS file** → select the download → local calendar → allow notifications. Four synthetic events and actual reminder notifications were verified on an emulator. The intended phone, audible alarms, and its battery/notification settings still need checking. See [device evidence](../artifacts/acceptance/phone-verification.json).

## Actual handover checklist (not completed by agent simulation)

Use a separate test calendar and an explicitly synthetic source before entering a real prescription. Record device/calendar app, timezone, import result, recurrence end dates, and whether a test alarm appeared. Delete the test calendar afterward.

Then let the intended caregiver use Scan → Review → Chart themselves. Ask them to compare every line and explain an ASK field. Record their own feedback and permission before sharing it. No caregiver identity, quote, consent, independent label, or alarm delivery can be supplied by an AI pretending to be that person.

Use **Acceptance Feedback** to save those actual observations locally. Select the
actual evidence source and permission; leave anything unobserved as `not_checked`.
The downloadable summary omits identities and private words and includes only
explicitly consented counts. **Label Acceptance** has a separate blank-field form
for the two independent annotation rounds.

Current evidence is in [reverification.md](reverification.md). The user confirmed
an Android Google Calendar notification for a directly created synthetic event;
that event was removed afterward. Real caregiver handover, exported ICS import,
phone recurrence/end dates, and alarm sound remain TODO.

## Always confirm with the doctor or pharmacist

On Chart, optionally enter a **History note** describing the source of a change,
then select **Save to local history**. History shows the active copy and up to 100
saved revisions, newest first. Expand a revision to compare its exact recorded
fields with the slip. Viewing an old copy does not make it the active schedule.

- If two slips name the same tablet with different times, the clerk shows both. Ask which one to follow.
- If the chart disagrees with the paper, trust the paper and the pharmacist.
- Pill Clerk never recommends a substitute or a new dose.
