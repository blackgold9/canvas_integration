"""Logic for Canvas calendar events."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from .assignment_logic import CanvasAssignment

@dataclass
class CalendarEventData:
    """Simplified event data for HA consumption."""
    summary: str
    start: datetime
    end: datetime
    description: str
    location: str = "Canvas"

def get_calendar_events(
    assignments: list[CanvasAssignment],
    start_date: datetime,
    end_date: datetime
) -> list[CalendarEventData]:
    """Transform assignments into calendar events within a range."""
    events = []
    for assignment in assignments:
        if not assignment.due_at:
            continue

        if start_date <= assignment.due_at <= end_date:
            events.append(
                CalendarEventData(
                    summary=f"[{assignment.course_name}] {assignment.name}",
                    start=assignment.due_at,
                    end=assignment.due_at + timedelta(hours=1),
                    description=assignment.description,
                )
            )

    # Sort by start date
    events.sort(key=lambda x: x.start)
    return events
