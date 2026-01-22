import pytest
from datetime import datetime, timedelta, timezone
from custom_components.canvas.assignment_logic import CanvasAssignment, filter_assignments
from custom_components.canvas.calendar_logic import get_calendar_events

def test_assignment_parsing():
    data = {
        "id": 123,
        "name": "Homework",
        "due_at": "2026-01-22T23:59:59Z",
        "description": "Do work"
    }
    assignment = CanvasAssignment.from_dict(data, "Math")
    assert assignment.name == "Homework"
    assert assignment.due_at.year == 2026
    assert assignment.due_at.month == 1
    assert assignment.due_at.day == 22

def test_filter_today():
    now = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
    assignments = [
        CanvasAssignment("1", "Today", "Math", now),
        CanvasAssignment("2", "Tomorrow", "Math", now + timedelta(days=1)),
    ]
    
    result = filter_assignments(assignments, now, "today")
    assert len(result) == 1
    assert result[0].name == "Today"

def test_calendar_transformation():
    now = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
    assignments = [
        CanvasAssignment("1", "HW 1", "Math", now),
    ]
    
    events = get_calendar_events(assignments, now - timedelta(days=1), now + timedelta(days=1))
    assert len(events) == 1
    assert events[0].summary == "[Math] HW 1"
    assert events[0].end == now + timedelta(hours=1)
