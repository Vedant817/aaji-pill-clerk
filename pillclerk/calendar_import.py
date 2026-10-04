"""Prepare Google event payloads from the clerk's actual ICS export. No API calls."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from icalendar import Calendar


def google_events(raw: bytes, timezone_name: str, *, synthetic: bool = False) -> list[dict]:
    zone = ZoneInfo(timezone_name)
    events = Calendar.from_ical(raw).walk("VEVENT")
    if not events:
        raise ValueError("Calendar contains no medicine events")
    result, seen = [], set()
    for event in events:
        uid = str(event.get("UID", ""))
        if not uid.startswith("pillclerk-") or uid in seen:
            raise ValueError("Require unique clerk export UIDs")
        seen.add(uid)
        if any(key in event for key in ("EXDATE", "RDATE", "RECURRENCE-ID", "ATTENDEE")):
            raise ValueError("Exceptions, attendees and edited instances need manual calendar review")
        start = event.decoded("DTSTART")
        if not isinstance(start, datetime):
            raise ValueError("Require timed events, not all-day reminders")
        if start.tzinfo is None:
            first, second = start.replace(tzinfo=zone, fold=0), start.replace(tzinfo=zone, fold=1)
            if first.utcoffset() != second.utcoffset() or first.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != start:
                raise ValueError("Ambiguous or nonexistent local time; check the calendar timezone")
            start = first
        else:
            start = start.astimezone(zone)
        duration = event.decoded("DURATION") if "DURATION" in event else event.decoded("DTEND") - event.decoded("DTSTART")
        if not isinstance(duration, timedelta) or not timedelta(0) < duration <= timedelta(days=1):
            raise ValueError("Require a positive reminder duration of at most one day")
        rule = event.get("RRULE")
        if not rule or set(rule) - {"FREQ", "INTERVAL", "COUNT"} or rule.get("FREQ") != ["DAILY"]:
            raise ValueError("Only the clerk's daily interval/count recurrence is supported")
        if any(len(rule.get(key, [])) != 1 or int(rule[key][0]) < 1 for key in ("INTERVAL",)):
            raise ValueError("Require a positive recurrence interval")
        if "COUNT" in rule and (len(rule["COUNT"]) != 1 or int(rule["COUNT"][0]) < 1):
            raise ValueError("Require a positive occurrence count")
        alarms = event.walk("VALARM")
        if len(alarms) != 1 or str(alarms[0].get("ACTION")) != "DISPLAY" or alarms[0].decoded("TRIGGER") != timedelta(0):
            raise ValueError("Require exactly one at-start display reminder")
        title = str(event.get("SUMMARY", "")).strip()
        if not title:
            raise ValueError("Require the exported medicine description")
        end = (start.astimezone(timezone.utc) + duration).astimezone(zone)
        result.append({"source_uid": uid, "payload": {
            "title": ("[Synthetic test] " if synthetic else "") + title,
            "start_time": start.isoformat(), "end_time": end.isoformat(),
            "timezone_str": timezone_name, "attendees": [], "add_google_meet": False,
            "recurrence": ["RRULE:" + rule.to_ical().decode("ascii")],
            "reminders": {"use_default": False, "overrides": [{"method": "popup", "minutes": 0}]},
            "visibility": "private", "transparency": "transparent"}})
    return result
