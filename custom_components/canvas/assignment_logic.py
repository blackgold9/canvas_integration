"""Core logic for Canvas assignments."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

_LOGGER = logging.getLogger(__name__)

@dataclass
class CanvasAssignment:
    """Representation of a Canvas Assignment."""
    id: str
    name: str
    course_name: str
    due_at: datetime | None
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict, course_name: str) -> CanvasAssignment:
        """Create from a dictionary."""
        due_at_str = data.get("due_at")
        due_at = None
        if due_at_str:
            try:
                # Use fromisoformat for speed, but handle Z suffix
                clean_date = due_at_str.replace("Z", "+00:00")
                due_at = datetime.fromisoformat(clean_date)
            except ValueError:
                _LOGGER.warning("Could not parse due_at date: %s", due_at_str)

        return cls(
            id=str(data.get("id")),
            name=data.get("name", "Unknown"),
            course_name=course_name,
            due_at=due_at,
            description=data.get("description", ""),
        )

def filter_assignments(
    assignments: list[CanvasAssignment],
    now: datetime,
    filter_type: str,
    days: int = 7
) -> list[CanvasAssignment]:
    """Filter assignments based on type."""
    local_today = now.date()
    filtered = []

    for assignment in assignments:
        if not assignment.due_at:
            continue
            
        local_due = assignment.due_at.astimezone() # Assume system local if no tz
        local_due_date = local_due.date()

        include = False
        if filter_type == "today":
            include = local_due_date == local_today
        elif filter_type == "tomorrow":
            include = local_due_date == (local_today + timedelta(days=1))
        elif filter_type == "upcoming":
            limit = now + timedelta(days=days)
            include = now < assignment.due_at <= limit
        elif filter_type == "missed":
            limit = now - timedelta(days=days)
            include = limit <= assignment.due_at <= now

        if include:
            filtered.append(assignment)

    return filtered
