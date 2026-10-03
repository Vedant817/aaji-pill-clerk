# Synthetic browser demo

The actual recording is [demo.mp4](../artifacts/acceptance/demo.mp4): 85 seconds, silent, played at 2.22x speed with a visible synthetic/AI-verification label. The [raw recording](../artifacts/acceptance/browser-workflow-raw.mp4) is retained. It is a real browser run, not a rendered mock UI or evidence of human acceptance.

The input is [synthetic-slip.png](../artifacts/acceptance/synthetic-slip.png), rendered from two existing template training-fixture lines recorded in [scenario.json](../artifacts/acceptance/scenario.json). It is not a real prescription and is never loaded automatically by the app.

## What it shows

1. Upload the synthetic printed reference on Scan and run the installed Windows OCR engine.
2. Remove the non-medicine header, check both copied lines against the image, and sign off.
3. Load lines and wait for live hosted FT2 parsing. The recording includes the real wait; speed-up applies to the entire recording.
4. Compare each field with the synthetic source. Confirm the tablet and syrup lines.
5. Show the Marathi chart, including the half-tablet night dose and course end dates.
6. Click the chart and calendar download controls. Actual export responses were retrieved and validated separately; no phone import is shown.

The agent operated the browser as a simulated caregiver. Do not describe these clicks as a real friend's signoff, independent human annotation, or clinical validation.

## Suggested spoken narration

“This is synthetic test input. Windows reads the printed text locally; handwriting accuracy is still unverified. I check the text before it reaches the hosted parser. Every line needs confirmation. The chart copies the written doses and dates. The calendar export contains recurring events and alarms, but the intended phone still needs an import and alarm check.”

## Further acceptance

Browser safety checks and artifacts are documented in [browser-acceptance.md](browser-acceptance.md). A real caregiver handover, independent human labels, phone import, publication links, and consented feedback remain TODO. Do not record private or public dataset photographs.
