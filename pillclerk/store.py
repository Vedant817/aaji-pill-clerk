"""SQLite store for active meds and change history."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from pillclerk.config import ROOT
from pillclerk.schema import MedLine

DEFAULT_DB = ROOT / "data" / "pillclerk.db"


def connect(path: Path = DEFAULT_DB) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS meds (
            id INTEGER PRIMARY KEY,
            saved_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY,
            saved_at TEXT NOT NULL,
            note TEXT,
            payload TEXT NOT NULL
        )"""
    )
    conn.commit()
    return conn


def save_meds(meds: list[MedLine], note: str = "", path: Path = DEFAULT_DB) -> None:
    payload = json.dumps([m.model_dump() for m in meds], ensure_ascii=False)
    now = datetime.now().isoformat(timespec="seconds")
    with closing(connect(path)) as conn, conn:
        conn.execute("DELETE FROM meds")
        conn.execute("INSERT INTO meds (saved_at, payload) VALUES (?, ?)", (now, payload))
        conn.execute(
            "INSERT INTO history (saved_at, note, payload) VALUES (?, ?, ?)",
            (now, note, payload),
        )
        conn.commit()


def load_meds(path: Path = DEFAULT_DB) -> list[MedLine]:
    with closing(connect(path)) as conn:
        row = conn.execute("SELECT payload FROM meds ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return []
    return [MedLine.model_validate(x) for x in json.loads(row[0])]


def load_history(path: Path = DEFAULT_DB, limit: int = 100) -> list[dict]:
    """Return saved copies newest first; never interpret or apply an old dose."""
    if not 1 <= limit <= 1000:
        raise ValueError("History limit must be between 1 and 1000")
    with closing(connect(path)) as conn:
        rows = conn.execute(
            "SELECT id, saved_at, note, payload FROM history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"id": row[0], "saved_at": row[1], "note": row[2] or "",
             "meds": [MedLine.model_validate(item) for item in json.loads(row[3])]}
            for row in rows]
