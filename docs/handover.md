# Handover: using Pill Clerk at home

This is a **clerk**. It copies the prescription into a chart. It does not decide doses. **Always confirm with the doctor or pharmacist** if anything looks different from the paper slip.

## How to photograph (public HMR labelling, or a family slip later)

1. Daylight. Fill the frame with the medicine lines. One slip per photo.
2. Cover faces, letterhead, and phone numbers.
3. Hindi / Marathi / Hinglish lines are useful. Type what you see, including `[?]` for unreadable letters.
4. Keep the photo local. On **Scan**, type the line or use a configured local extractor. Check every character against the photo and remove headings before signing off the extracted text. Windows OCR has only been tested on one synthetic printed slip; handwriting accuracy is unverified.

## What a red ASK means

A red **ASK** cell means the clerk is not sure about that field (drug, dose, schedule, duration, …). It refused to guess.

- Look at the original line.
- Fill the field from what is written, or leave it empty and ask the pharmacist before you confirm.
- The fridge chart stays locked until every ASK is resolved and you confirm each line.

## Printing the chart

1. Scan (or paste) the lines → Review → confirm every line.
2. Open **Chart**.
3. Pick the start date and language (Marathi / Hindi / English).
4. Download **fridge-chart.html** and print it. Stick it on the fridge.
5. The footer says it is a clerk copy, not medical advice.

## Importing the `.ics`

1. On Chart, download **reminders.ics**.
2. Open it on the caregiver's phone and add it to the calendar.
3. Alarms follow the slot times on the chart (morning / afternoon / night).
4. SOS / PRN medicines are listed as “when needed”, not as timed alarms.
5. Reminder times are local wall-clock times in the importing calendar. Check the calendar's timezone, the first and last date, the dose/unit, and whether alarms are enabled. Imported files do not prove that a phone will display an alarm.

## Actual handover checklist (not completed by agent simulation)

Use a separate test calendar and an explicitly synthetic source before entering a real prescription. Record device/calendar app, timezone, import result, recurrence end dates, and whether a test alarm appeared. Delete the test calendar afterward.

Then let the intended caregiver use Scan → Review → Chart themselves. Ask them to compare every line and explain an ASK field. Record their own feedback and permission before sharing it. No caregiver identity, quote, consent, independent label, or alarm delivery can be supplied by an AI pretending to be that person.

Current evidence is in `docs/browser-acceptance.md`; real caregiver handover and phone calendar acceptance remain TODO.

## Always confirm with the doctor or pharmacist

- If two slips name the same tablet with different times, the clerk shows both. Ask which one to follow.
- If the chart disagrees with the paper, trust the paper and the pharmacist.
- Pill Clerk never recommends a substitute or a new dose.
