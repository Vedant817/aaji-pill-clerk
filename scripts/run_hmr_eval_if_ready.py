"""Run HMR evals once gold has ≥100 lines. User approved gemma31_json for this set."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pillclerk.public_data import labelled_count

OUT = ROOT / "eval" / "out"
FLAG = OUT / "hmr_eval_started.json"
SET_PATH = "data/public_labels/hmr100_gold.jsonl"
SYSTEMS = ("b0_fair", "ft2", "ft3", "gemma31_json")


def n_gold() -> int:
    return labelled_count("hmr100")


def already_scored() -> bool:
    p = OUT / "ft2_hmr100_gold.json"
    if not p.is_file():
        return False
    try:
        return int(json.loads(p.read_text(encoding="utf-8")).get("n") or 0) >= 100
    except Exception:
        return False


def main() -> int:
    n = n_gold()
    print(json.dumps({"n_gold": n, "already_scored": already_scored()}))
    if n < 100:
        print("not ready")
        return 0
    if already_scored():
        print("already scored")
        return 0
    if FLAG.is_file():
        print("eval already started")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    FLAG.write_text(json.dumps({"n": n, "systems": list(SYSTEMS)}), encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    for system in SYSTEMS:
        cmd = [sys.executable, "-m", "eval.eval", "--system", system, "--set", SET_PATH]
        if system == "gemma31_json":
            cmd.extend(["--workers", "3"])
        print("RUN", " ".join(cmd), flush=True)
        rc = subprocess.call(cmd, cwd=ROOT, env=env)
        if rc != 0:
            print(f"FAILED {system} exit {rc}", flush=True)
            FLAG.unlink(missing_ok=True)
            return rc
    print("DONE hmr evals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
