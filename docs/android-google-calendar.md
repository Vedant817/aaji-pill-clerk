# Android + Google Calendar acceptance

Target chosen by the user: Android with Google Calendar. No new service key or
paid integration is needed. Actual Google Calendar import and physical-phone
notification delivery are still pending. The T3 shared browser currently redirects
to the public Calendar page instead of a signed-in calendar. The earlier passing
emulator test used Fossify Calendar, not Google Calendar.
After the user reconnected, calendar listing still returned missing-permissions,
but primary-calendar event search, creation and read-back succeeded. No further
reconnection is needed for those actions. A single private, non-medical notification
test was created for 4 October 2026 at 15:01:12 IST with an at-start popup reminder.
The event is transparent (does not mark the user busy) and has no invited guests.
See [API read-back evidence](../artifacts/acceptance/google-calendar-api-verification.json).
Physical-phone delivery is awaiting the user's observation. This direct API check
does not verify ICS import. The event ID needed for later cleanup stays gitignored.

## Import and sync

Google documents ICS import **on a computer**, followed by account sync to Android.
Do not assume that tapping the download in the Android app imports the series.
See [Google's import instructions](https://support.google.com/calendar/answer/37118?co=GENIE.Platform%3DDesktop&hl=en)
and [Android sync instructions](https://support.google.com/calendar/answer/151674?co=GENIE.Platform%3DAndroid&hl=en).

1. On the computer, open Google Calendar and sign in to the account used on the
   caregiver's phone. Create a separate calendar named **Pill Clerk test — synthetic**
   under Settings → Add calendar → Create new calendar.
2. Check that the calendar and Android phone use India Standard Time. The medicine
   export uses floating local times; the 08:00 and 21:00 events should remain at
   those local times after import.
3. Settings → Import & export → Select file from your computer. Choose the actual
   [synthetic browser export](../artifacts/acceptance/recheck/pillclerk.ics), select
   the separate test calendar, then Import once. These are synthetic fixture
   medicines, not a regimen for anyone to take.
4. On Android, use the same account in Google Calendar, select the test calendar,
   enable its sync and visibility, and refresh. Check that four recurring series
   appear. This file starts 4 October 2026: tablet morning/night series have seven
   occurrences ending 10 October; syrup series have three ending 6 October.
5. Check the actual quantities, units, and times against the accompanying
   [scenario](../artifacts/acceptance/recheck/scenario.json) and chart. Inspect each
   event's notification setting; file alarms alone do not prove Google retained
   them. Google's [Android notification settings](https://support.google.com/calendar/answer/37242?co=GENIE.Platform%3DAndroid&hl=en)
   describe event/calendar notifications. Allow Calendar notifications in Android
   settings and inspect device-specific restrictions if no reminder appears.

## Check a reminder now

Generate a fresh **non-medical** test event immediately before importing it:

```powershell
uv run python -m scripts.make_notification_probe --minutes 10 --out data/real/phone-check.ics
```

The file is gitignored. If it already exists, use a new filename; the command
preserves earlier evidence. Import this file once into the same synthetic test
calendar and sync Android before the printed UTC deadline. The phone displays the
corresponding local time. Verify an at-event-time notification is configured,
lock the phone, and wait for an actual notification. Record whether it displayed,
made sound, or vibrated; these are separate observations. Do not advance the
physical phone's clock. If import/sync takes too long, generate a new event.

Record device model, Android version, app version, timezone, import result,
recurrence end dates, notification timestamp and observed sound/vibration. Avoid
account details or real medicine text in shared evidence. Delete the separate test
calendar afterward. A test event does not validate medical transcription or the
caregiver's ability to use the app.

## Human acceptance still required

The intended caregiver should complete Scan → Review → Chart while comparing each
line with the source, explain what an ASK field means, and identify any confusing
steps. Record their own feedback and whether they permit sharing it. Do not supply
quotes, identity, consent, or success on their behalf.

For independent labels, two distinct people use **Independent prescription labels**
in the local app. Each selects their own ID and round A or B, transcribes every
medicine line directly from each of the 20 original reserved images, explicitly
fills the schema fields, and marks each page complete. Do not show them OCR output,
AI references, or the other round's answers. Disagreements must be resolved from
the source by the actual annotators; do not force model answers to match.

After both complete rounds agree:

```powershell
uv run python -m scripts.prepare_acceptance --finalize
uv run python -m eval.ocr_cer --pages 20
```

Finalization refuses incomplete rounds, changed images, duplicate annotator IDs,
and disagreements. Until then, CER stays null. These pages have now informed
development diagnostics; human agreement can validate transcription but cannot
make them a fresh untouched model test set. Future improvement claims need newly
reserved, unseen pages and independent labels.
