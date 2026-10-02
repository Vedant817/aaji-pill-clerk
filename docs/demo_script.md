# 90-second demo (synthetic slip)

Local app: http://localhost:8501. Slip: `data/demo/prescriptions/aaji_sample.txt`. Do not use family photos.

**0:00–0:15 Scan.** Open Scan. Tap **Load demo slip**. Ten synthetic lines appear (Glycomet 1-0-1, Telma empty stomach, Pan BD, Wysolone taper, Combiflam SOS, Ambrodil LS syrup, Ecosprin HS, Asthalin puff, Calcirol weekly, Hinglish Glycomet). Tap **Go to Review**.

**0:15–0:50 Review with ASK.** Tap **Fill fields from Tinker parser**. Walk one line: show the original text next to JSON fields. If a cell is **red ASK**, say: the clerk will not guess; we copy from the slip or leave it for the pharmacist. Confirm each line (human sign-off). Chart stays locked until ASK is gone.

**0:50–1:15 Chart.** Open Chart. Start date today, language Marathi. Scroll the big-font fridge table (☀️ / 🌤️ / 🌙). Point at the footer: clerk copy, not medical advice. Download **fridge-chart.html**.

**1:15–1:30 .ics.** Download **reminders.ics**. Say: import on the caregiver phone; SOS stays “when needed”. Close on: always confirm with the doctor or pharmacist.

If Tinker is down, still demo the lock: unconfirmed lines block Chart.
