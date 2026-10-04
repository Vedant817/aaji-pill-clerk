"""Make a fresh non-medical ICS event for an actual phone notification check."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from icalendar import Alarm, Calendar, Event


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=10)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.minutes < 5:
        parser.error("Allow at least five minutes for import and phone sync")
    if args.out.exists():
        parser.error("Choose a new output file; existing evidence is not overwritten")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start = now + timedelta(minutes=args.minutes)
    event = Event()
    event.add("uid", f"{uuid4()}@pillclerk-notification-test")
    event.add("dtstamp", now)
    event.add("dtstart", start)
    event.add("dtend", start + timedelta(minutes=1))
    event.add("summary", "Pill Clerk notification test (synthetic, no medicine)")
    event.add("description", "Test notification delivery only. No medicine or dose instruction. Delete the test calendar afterward.")
    alarm = Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add("description", "Synthetic notification test")
    alarm.add("trigger", timedelta(0))
    event.add_component(alarm)
    calendar = Calendar()
    calendar.add("version", "2.0")
    calendar.add("prodid", "-//Pill Clerk//Notification verification//EN")
    calendar.add_component(event)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(calendar.to_ical())
    print(f"Created {args.out}; notification at {start.isoformat()} (UTC). Import and sync before this time.")
    print("File creation does not verify import or notification delivery.")


if __name__ == "__main__":
    main()
