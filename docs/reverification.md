# Reverification — 4 October 2026

This is agent-operated verification with synthetic browser/calendar input and
local public HMR handwriting. It is not caregiver feedback, consent, independent
human annotation, or clinical validation.

| Check | Actual result |
|---|---|
| Full pytest suite | 199 tests passed |
| Browser, Windows OCR → signoff → live hosted FT2 → confirmation → exports | Passed again with two synthetic medicine lines |
| Review navigation and editing | Confirmed values survived navigation; editing revoked confirmation and blocked Chart |
| Refill calculation | Blank initial stock; entered 10 tablets / 20 ml gave 10 October / 6 October |
| Actual downloaded chart and ICS | Four events; correct quantities, units, local times, recurrence counts, UTC DTSTAMP and alarms |
| Android calendar import | Four events persisted in Fossify Calendar 1.11.0 on an Android API 36 emulator |
| Android reminder delivery | Actual notifications appeared for both 21:00 events after advancing only the disposable emulator's clock |
| Intended caregiver's physical phone / audible alarm | Unverified |
| Caregiver feedback / independent human labels | Unverified; two annotation rounds remain empty |

The browser check used process-only Windows extraction and a $0.05 sampling
allocation per parser instance. Two live FT2 parse calls succeeded. No new
training was started and the saved active checkpoint was not changed. Current
verification did not save synthetic history into the user's SQLite database.

See [chart](../artifacts/acceptance/recheck-chart.png),
[stock](../artifacts/acceptance/recheck-stock.png), and
[device report](../artifacts/acceptance/phone-verification.json).
Fresh downloaded [chart HTML](../artifacts/acceptance/recheck/fridge-chart.html),
[calendar](../artifacts/acceptance/recheck/pillclerk.ics), and
[file validation](../artifacts/acceptance/recheck/export-verification.json)
are retained separately from the original run.
The earlier [recording](browser-acceptance.md) remains a separate browser run.
The export-validation script's `phone_import_verified: false` describes its own
file-only checks; the separate device report records the emulator import.

## Handwriting remains unreliable

Both engines were run on every page of the same frozen 20-page HMR queue. Raw
transcriptions and public images stay outside tracked source. Aggregate reports
contain only page IDs and counts.

| Local extractor | Pages attempted | Pages returning text | Failures | Full published labels found exactly after normalization |
|---|---:|---:|---:|---:|
| Windows installed OCR | 20 | 17 | 0 | 1/62 |
| Ollama 0.35.1, `gemma4:e4b-it-qat` | 20 | 20 | 0 | 1/62 |

Sources: [Windows probe](../eval/out/windows_handwriting_probe.json) and
[Gemma probe](../eval/out/gemma_handwriting_probe.json). This narrow label-presence
count includes full published medicine labels (sometimes strength/form), excludes
empty labels, and does not establish drug recognition accuracy, dose accuracy,
line alignment, or CER. The labels need not reproduce every literal character on
the image. Returning text is not evidence that it is correct: local Gemma made
medicine-name and dose errors on inspection. Manual transcription remains the
default and every extracted character must be compared with the source.

A larger visual-token budget was tested on one page using the installed runner's
`LLAMA_ARG_IMAGE_MIN_TOKENS=1120` / `LLAMA_ARG_IMAGE_MAX_TOKENS=1120` options. Logs
confirmed 1,147 image tokens instead of 378. The result was five `[?]` lines,
taking 55.45 seconds including model startup; it did not fix transcription and
was not adopted. This experiment is not an independent held-out evaluation.

OCR CER now requires finalized, matching independent human annotation rounds;
the existing AI/development references no longer qualify. Running
`python -m eval.ocr_cer --pages 20` reports `cer: null` and no finalized gold.
The published parser-only scores remain exploratory where their reference labels
are unverified. No new clinical accuracy percentage is claimed here.

## Fixes and local setup

Photo extraction now requires a loopback Ollama host, ignores HTTP proxy
environment settings, rejects cloud-tagged and remotely redirected model
aliases before image submission, bounds waits, and rejects truncated output.
Tests cover those paths. `OLLAMA_NO_CLOUD=1` must also be set on the **server**
process before starting it; setting it only in the app does not reconfigure an
already running daemon.

The local Gemma vision model was downloaded and tested outside the repo. No
fine-tuned Qwen weights were downloaded, merged, or converted. Ollama's portable
runtime and the model remain under
`%LOCALAPPDATA%\pillclerk-verification`; downloads and raw OCR are not committed.
To use this existing installation, start a separate PowerShell terminal:

```powershell
$env:OLLAMA_HOST='127.0.0.1:11434'
$env:OLLAMA_MODELS="$env:LOCALAPPDATA\pillclerk-verification\models"
$env:OLLAMA_NO_CLOUD='1'
& "$env:LOCALAPPDATA\pillclerk-verification\tools\ollama-0.35.1\ollama.exe" serve
```

Then start the app in another terminal with process-only overrides:

```powershell
$env:EXTRACT_BACKEND='ollama'
$env:OLLAMA_EXTRACT_MODEL='gemma4:e4b-it-qat'
uv run python -m scripts.run_local --sampling-budget-usd 0.05
```

No larger image-budget override is recommended from this experiment. The app
continues to start empty; fixtures and expected answers are used only in tests
and acceptance artifacts, not loaded by runtime code.

The T3 device helper needed a Windows executable-suffix repair (`adb.exe` /
`emulator.exe`) and a `cmd.exe` wrapper for `avdmanager.bat list avd`. The repair is
outside this repo, in the installed `expo-device-hub/0.12.0` bundle. Its original
file is backed up at
`%LOCALAPPDATA%\pillclerk-verification\device-hub-index-original.mjs`; upgrading
the helper may overwrite this temporary local repair. The fresh test emulator
needed host graphics, Vulkan disabled, and 4096 MB memory. Its clock was restored
and it was stopped after verification. The named verification AVD remains for
review with synthetic events only; its configuration now preserves host graphics
and 4096 MB memory. Restart it with the tested additional flags:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd pillclerk_verify_20261004 -no-snapshot -gpu host -feature -Vulkan -memory 4096
```

No Android system image was downloaded. Owned OCR server/runner processes were
stopped after testing, and the redundant 1.47 GB Ollama archive was removed.

## Remaining acceptance

On the intended phone, import a clearly synthetic test calendar, verify timezone
and end dates, and observe a reminder with the phone's actual notification settings.
For an account-free Android import, the tested path was Fossify Calendar:
Settings → Import events from an ICS file → choose the downloaded file → local
calendar → allow notifications. This path was verified only on the emulator.

The intended caregiver must still try the workflow and supply their own feedback
and sharing permission. Two distinct people must independently transcribe and
label the reserved pages before adjudication and CER scoring. An agent cannot
supply those human observations by pretending to be a friend.

Feature work stops 5 October at 10:00 IST; submission deadline is 12:29 IST.
