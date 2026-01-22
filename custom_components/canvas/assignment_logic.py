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
    is_submitted: bool = False
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> CanvasAssignment:
        """Create from a Planner API item dictionary."""
        # Planner API has 'plannable' for the object and 'submissions' for status
        plannable = data.get("plannable", {})
        submissions = data.get("submissions", {})
        
        due_at_str = plannable.get("due_at")
        due_at = None
        if due_at_str:
            try:
                clean_date = due_at_str.replace("Z", "+00:00")
                due_at = datetime.fromisoformat(clean_date)
            except ValueError:
                _LOGGER.warning("Could not parse due_at date: %s", due_at_str)

        # Determine submission status from Planner 'submissions' object
        is_submitted = False
        if isinstance(submissions, dict):
            # Planner API provides 'submitted' and 'graded' booleans directly
            is_submitted = submissions.get("submitted", False) or submissions.get("graded", False)
        elif submissions is True:
            is_submitted = True

        return cls(
            id=str(plannable.get("id")),
            name=plannable.get("title", "Unknown"),
            course_name=data.get("context_name", "Unknown"),
            due_at=due_at,
            is_submitted=is_submitted,
            description=plannable.get("description", ""),
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
        # Hide anything already submitted from sensors
        if assignment.is_submitted:
            continue

        if not assignment.due_at:
            continue
            
        local_due = assignment.due_at.astimezone() # Assume system local if no tz
        local_due_date = local_due.date()

        include = False
        if filter_type == "today":
            include = local_due_date == local_today
        elif filter_type == "tomorrow":
            include = local_due_date == (local_today + timedelta(days=1))
        elif filter_type == "upcoming_week":
            limit = now + timedelta(days=days)
            include = now < assignment.due_at <= limit
        elif filter_type == "missed":
            limit = now - timedelta(days=days)
            include = limit <= assignment.due_at <= now

        if include:
            filtered.append(assignment)

    return filtered
