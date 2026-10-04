"""Local, explicitly attributed acceptance observations; never synthetic success."""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pillclerk.config import ROOT

DEFAULT_PATH = ROOT / "data/real/acceptance-feedback.jsonl"
Status = Literal["pass", "fail", "not_checked"]


class Observation(BaseModel):
    observer_id: str = Field(min_length=1)
    source: Literal["human_self_report", "human_observer", "agent_test"]
    actual_observation_attested: bool
    sharing_allowed: bool
    context: Literal["synthetic_input", "real_prescription"]
    workflow: Status
    ask_understood: Status
    source_compared: Status
    ics_import: Status
    recurrence: Status
    notification: Status
    sound: Status
    device: str = ""
    calendar_app: str = ""
    timezone: str = ""
    feedback: str = ""

    @model_validator(mode="after")
    def actual(self):
        self.observer_id = self.observer_id.strip()
        if not self.observer_id or not self.actual_observation_attested:
            raise ValueError("Enter an observer ID and attest an actual observation")
        if all(getattr(self, field) == "not_checked" for field in ("workflow", "ask_understood", "source_compared", "ics_import", "recurrence", "notification", "sound")) and not self.feedback.strip():
            raise ValueError("Record at least one actual check or feedback observation")
        if any(getattr(self, field) != "not_checked" for field in ("ics_import", "recurrence", "notification", "sound")) and not (self.device.strip() and self.calendar_app.strip() and self.timezone.strip()):
            raise ValueError("Phone observations require device, calendar app and timezone")
        return self


def save_observation(record: Observation, path: Path = DEFAULT_PATH) -> None:
    row = {**record.model_dump(), "recorded_at_utc": datetime.now(timezone.utc).isoformat()}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def shareable_summary(path: Path = DEFAULT_PATH) -> dict:
    rows = [Observation.model_validate(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []
    allowed = [r for r in rows if r.sharing_allowed]
    fields = ("workflow", "ask_understood", "source_compared", "ics_import", "recurrence", "notification", "sound")
    return {"consented_observations": len(allowed), "human_observations": sum(r.source != "agent_test" for r in allowed),
            "agent_tests": sum(r.source == "agent_test" for r in allowed),
            "checks": {source: {field: {status: sum(r.source == source and getattr(r, field) == status for r in allowed) for status in ("pass", "fail", "not_checked")} for field in fields} for source in ("human_self_report", "human_observer", "agent_test")},
            "limits": "Self-reported observations, not identity verification or independent medical validation. Private feedback, observer IDs and device details omitted."}
