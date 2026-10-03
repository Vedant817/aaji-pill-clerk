"""Run the local app with explicit verification settings, without editing .env."""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import sys


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--windows-ocr", action="store_true")
    ap.add_argument("--sampling-budget-usd", type=float)
    ap.add_argument("--port", type=int, default=8501)
    args = ap.parse_args()
    if args.sampling_budget_usd is not None:
        if not math.isfinite(args.sampling_budget_usd) or args.sampling_budget_usd <= 0:
            ap.error("sampling budget must be positive and finite")
        os.environ["PILLCLERK_SAMPLING_BUDGET_USD"] = str(args.sampling_budget_usd)
    if args.windows_ocr:
        os.environ["EXTRACT_BACKEND"] = "windows"
    from streamlit.web import cli
    app = Path(__file__).resolve().parents[1] / "app/Home.py"
    sys.argv = ["streamlit", "run", str(app), "--server.port", str(args.port),
                "--server.address", "127.0.0.1", "--server.headless", "true", "--browser.gatherUsageStats", "false",
                "--server.fileWatcherType", "none"]
    cli.main()


if __name__ == "__main__":
    main()
