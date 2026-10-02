"""One medicine line, copied (never inferred) from a prescription."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Form = Literal[
    "tab", "cap", "syrup", "drops", "inhaler", "injection", "cream", "sachet", "other"
]
Unit = Literal["tab", "cap", "ml", "drop", "puff", "unit", "sachet", "apply"]
Food = Literal["before", "after", "with", "empty_stomach", "any"]
Kind = Literal["daily", "prn", "taper"]
CheckField = Literal["drug", "strength", "dose", "food", "duration_days", "schedule"]

SYSTEM_PROMPT = (
    "You are Pill Clerk. Convert ONE prescription line into JSON matching the MedLine schema. "
    "Copy only what is written. Form (Tab/Cap/Syr/Inh/Inj/Drops/Cream/Sachet) and food "
    "(before/after/with/empty stomach; AC/PC/WF/ES; Hindi/Marathi food phrases) come from "
    "tokens on the line. If no food token is written, food is any. 1/12 means duration_days=30. "
    "SOS/PRN/zarurat/जरूरत/गरजेनुसार is kind=prn with dose null (no morning/afternoon/night slots). "
    "Never guess a missing dose, drug, or duration: leave it null and add it to needs_check. "
    "Output JSON only."
)


class Dose(BaseModel):
    morning: float = Field(0, ge=0, le=20)
    afternoon: float = Field(0, ge=0, le=20)
    night: float = Field(0, ge=0, le=20)
    unit: Unit = "tab"

    @model_validator(mode="after")
    def plausible(self) -> Dose:
        if self.unit in ("tab", "cap") and max(self.morning, self.afternoon, self.night) > 4:
            raise ValueError("more than 4 tablets in one slot: flag for a human instead")
        return self


class TaperStep(BaseModel):
    dose: Dose
    days: int = Field(ge=1, le=90)


class MedLine(BaseModel):
    """One medicine line, copied (never inferred) from a prescription."""

    drug: str | None
    strength: str | None = None
    form: Form = "tab"
    kind: Kind = "daily"
    dose: Dose | None = None
    every_n_days: int = Field(1, ge=1, le=30)
    taper: list[TaperStep] = Field(default_factory=list)
    food: Food = "any"
    duration_days: int | None = None
    prn_max_per_day: int | None = None
    note: str | None = None
    needs_check: list[CheckField] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent(self) -> MedLine:
        if self.kind == "taper" and not self.taper:
            raise ValueError("taper needs steps")
        if self.kind == "daily" and self.dose is None and "dose" not in self.needs_check:
            raise ValueError("daily line without dose must be flagged")
        if self.kind == "prn" and self.dose and (self.dose.morning + self.dose.afternoon + self.dose.night):
            raise ValueError("prn lines have no fixed slots")
        return self
