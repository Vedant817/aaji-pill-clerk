"""User-entered source/check context for a saved or exported copy."""
from datetime import date, time

from pydantic import BaseModel, Field, field_validator

from pillclerk.schedule import SLOTS


class CopyContext(BaseModel):
    source_reference: str = Field(min_length=1)
    prescription_date: date | None = None
    checker: str = Field(min_length=1)
    checked_on: date
    start_date: date
    slot_times: dict[str, time]
    ongoing_confirmed: list[bool] = Field(default_factory=list)

    @field_validator("source_reference", "checker")
    @classmethod
    def entered_text(cls, value):
        if not value.strip():
            raise ValueError("Enter a source reference and checker initials")
        return value.strip()

    @field_validator("slot_times")
    @classmethod
    def all_slots(cls, value):
        if set(value) != set(SLOTS):
            raise ValueError("Record all three reminder times")
        return value


def context_text(context: dict | None, lang: str = "en") -> str:
    if not context:
        return ""
    record = CopyContext.model_validate(context)
    labels = {
        "en": ("Source", "prescription date", "not recorded", "Checked by", "checked on", "Chart start", "reminders", ("morning", "afternoon", "night")),
        "mr": ("मूळ प्रिस्क्रिप्शन", "प्रिस्क्रिप्शनची तारीख", "नोंद नाही", "तपासले", "तपासणीची तारीख", "तक्त्याची सुरुवात", "स्मरण वेळा", ("सकाळ", "दुपार", "रात्र")),
        "hi": ("मूल पर्चा", "पर्चे की तारीख", "दर्ज नहीं", "जाँचकर्ता", "जाँच की तारीख", "चार्ट की शुरुआत", "रिमाइंडर समय", ("सुबह", "दोपहर", "रात")),
    }.get(lang)
    if labels is None:
        return context_text(context, "en")
    source, prescription, missing, checker, checked, start, reminders, slots = labels
    return (f"{source}: {record.source_reference}; {prescription}: {record.prescription_date or missing}\n"
            f"{checker}: {record.checker}; {checked}: {record.checked_on}\n"
            f"{start}: {record.start_date}; {reminders}: "
            + ", ".join(f"{name} {record.slot_times[slot].strftime('%H:%M')}" for slot, name in zip(SLOTS, slots)))


def reminder_times(slot_times: dict[str, time] | None, context: dict | None) -> dict[str, time]:
    recorded = CopyContext.model_validate(context).slot_times if context else None
    if recorded is not None and slot_times is not None and slot_times != recorded:
        raise ValueError("Reminder times differ from the source/check record")
    return slot_times or recorded or SLOTS
