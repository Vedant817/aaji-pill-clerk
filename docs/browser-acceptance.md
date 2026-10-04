# Browser acceptance evidence — 4 October 2026

This is AI-operated verification of an explicitly synthetic caregiver scenario. It is not independent human annotation, family consent, a friend's review, or medical validation. The original browser run below did not import a calendar. A later recheck verified actual import and notifications on an Android emulator: see [reverification.md](reverification.md).

## Changes verified

- Scan now connects the configured extractor to the actual upload. `EXTRACT_BACKEND=windows` invokes Windows' installed OCR engine locally; `ollama` invokes the existing local vision backend. Manual input remains the default. No model weights were downloaded.
- OCR text needs a separate signoff before loading. Editing the text revokes that signoff. Errors leave manual input available.
- Returning from Chart to Review previously cleared widget values while a separate “seeded” flag survived. Review now restores missing fields from the saved draft. Resolved parser ASK checks also survive page navigation.
- Clear previously raised a widget-state exception after OCR. It now resets Scan in a callback, before Streamlit instantiates its widgets. The final browser check extracted text and then cleared it successfully.
- Calendar events now include the required UTC `DTSTAMP`. Reminder start times remain floating local wall-clock times. See [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545.html).
- File watching is disabled: Streamlit's watcher probed lazy Transformers vision imports and produced missing-`torchvision` errors. No unused vision dependency was installed.

## Actual run

The [scenario](../artifacts/acceptance/scenario.json) selects two existing synthetic training-fixture lines. The [printed slip](../artifacts/acceptance/synthetic-slip.png) explicitly says it is synthetic. Neither artifact is imported or preloaded by runtime code.

Windows OCR read all three printed lines exactly, including the non-medicine header. The agent removed that header, checked the two medicine lines, and signed off through the actual Scan UI. This is one clean printed-image smoke test, not an estimate of handwritten OCR accuracy.

The live hosted FT2 parser filled both lines. The browser displayed:
- Doxy, 100 mg, tablet, 1 morning / 0 afternoon / 0.5 night, before food, 7 days.
- Ambrolite, 30 mg/5 ml, syrup, 5 ml morning / 0 afternoon / 5 ml night, 3 days.

The agent compared those values with the synthetic source and clicked confirmation for each. Chart was blocked before confirmation. The actual Marathi chart showed the half-tablet symbol and course end dates. Returning to Review preserved both confirmed copies. Editing the syrup night dose revoked confirmation and blocked Chart again; the source value was restored and reconfirmed.

Stock started blank. Entering 10 tablets and 20 ml produced run-out dates 2026-10-10 and 2026-10-06. Saving to SQLite and opening History showed the two copied lines. Synthetic session/history data is cleaned after verification; no demo regimen is bundled or loaded automatically.

The actual chart and calendar download controls were clicked. Their server-generated media URLs returned HTTP 200 and the actual bodies were saved as [fridge-chart.html](../artifacts/acceptance/fridge-chart.html) and [pillclerk.ics](../artifacts/acceptance/pillclerk.ics). Final calendar verification found four unique recurring events, UTC DTSTAMP, counts 7/7/3/3, correct dose units, local 08:00/21:00 times, and display alarms at event start. No actual phone alarm delivery is claimed.

Reproduce file validation without hosted calls:

```powershell
uv run python -m scripts.verify_acceptance_exports
uv run pytest
```

[Export verification](../artifacts/acceptance/export-verification.json) records the checks. The final pytest run passed **189 tests**.

## Recording and screenshots

- [85-second labelled demo](../artifacts/acceptance/demo.mp4), silent, 2.22x speed. Only playback speed and the synthetic-verification notice were added.
- [Raw complete browser recording](../artifacts/acceptance/browser-workflow-raw.mp4).
- [OCR signoff](../artifacts/acceptance/scan-ocr.png).
- [Actual chart](../artifacts/acceptance/chart.png).
- [Export lock after editing](../artifacts/acceptance/edit-revokes-export.png).

The recording uses synthetic printed input and live parsing. It does not demonstrate handwritten extraction, a caregiver's own use, printing on a physical printer, or importing into a phone calendar.

## Costs and remaining acceptance

Verification used the existing approved Tinker allowance and a $0.05 **per-parser-instance** cap. Three successful two-line parse batches were exercised, including a retry after the navigation bug. This cap resets for a new parser instance and excludes storage; it is not billed-spend evidence or an account-wide limit. No additional training was started, and FT2 remains active. No fresh accuracy benchmark was inferred from these six synthetic calls.

During this original run, Android device opening failed. The installed emulator's normal boot crashed with exit 3221225477 (0xC0000005). A software-emulation retry stayed offline and was stopped. A later recheck repaired the Windows device helper and verified calendar import and displayed reminders in a fresh Android emulator. See [device evidence](../artifacts/acceptance/phone-verification.json). No system image was downloaded. iOS is unavailable on this Windows environment.

Still required:
- Import into the intended phone calendar; check timezone, recurrence end dates, and an actual alarm.
- Let the intended caregiver complete the workflow and record their own feedback and permission to share it.
- Complete two independent human annotation rounds. Single-agent AI references stay exploratory.
- Add publication links and real feedback to the corrected submission draft, then publish with the user's authorization.

The feature stop remains Monday 5 October at 10:00 IST; submission deadline 12:29 IST.
