"""Core logic for Canvas assignments."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

_LOGGER = logging.getLogger(__name__)

def clean_course_name(name: str | None) -> str:
    """Clean up Canvas course names by removing common prefixes and suffixes.
    
    Handles patterns like:
    - "- Math 101" -> "Math 101"
    - "P1-Spanish 2" -> "Spanish 2"
    - "1st period-Health" -> "Health"
    - "MATH-101 - Calculus" -> "Calculus"
    """
    if not name:
        return "Unknown Course"
        
    cleaned = name.strip()
    
    # 1. Handle leading dash/space prefixes
    if cleaned.startswith("- "):
        cleaned = cleaned[2:].strip()
    elif cleaned.startswith("-"):
        cleaned = cleaned[1:].strip()
        
    # 2. Handle common "Period" prefixes: P1-, P2-, 1st-, 1st period-, etc.
    import re
    # Match P1-, P10-, 1st-, 1st period-, 1st and 3rd period-
    period_pattern = r'^([pP]\d+|(\d+(st|nd|rd|th)(\s+and\s+\d+(st|nd|rd|th))?\s+period))[\s-]*'
    cleaned = re.sub(period_pattern, '', cleaned).strip()

    # 3. Handle separator logic (e.g., CODE - DESCRIPTION or CODE-DESCRIPTION)
    # Check for " - " first as it's the strongest signal
    if " - " in cleaned:
        parts = cleaned.split(" - ", 1)
        first_part, second_part = parts[0].strip(), parts[1].strip()
        # Heuristic: first part is short/cody
        if len(first_part) < 15 and (first_part.isupper() or any(c.isdigit() for c in first_part)):
            cleaned = second_part
    elif "-" in cleaned:
        # Avoid splitting if it's just a hyphenated word
        parts = cleaned.split("-", 1)
        first_part, second_part = parts[0].strip(), parts[1].strip()
        # More conservative check for single dash
        if len(first_part) < 8 and (first_part.isupper() or any(c.isdigit() for c in first_part)):
            cleaned = second_part
            
    return cleaned

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
            course_name=clean_course_name(data.get("context_name")),
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
