"""Turn pasted prescription text into Review drafts (ASK until a human confirms)."""

from __future__ import annotations

from pillclerk.ocr import lines_from_text
from pillclerk.schema import Dose, MedLine


def drafts_from_text(raw: str) -> list[dict]:
    drafts: list[dict] = []
    for line in lines_from_text(raw):
        drafts.append(
            {
                "line": line,
                "gold": MedLine(
                    drug=None,
                    kind="daily",
                    dose=Dose(),
                    needs_check=["drug", "dose", "schedule"],
                    note=line,
                ).model_dump(),
                "confirmed": False,
            }
        )
    return drafts
