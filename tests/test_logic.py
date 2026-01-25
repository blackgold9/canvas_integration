import pytest
from datetime import datetime, timedelta, timezone
from custom_components.canvas.assignment_logic import CanvasAssignment, filter_assignments, clean_course_name
from custom_components.canvas.calendar_logic import get_calendar_events

def test_assignment_parsing():
    data = {
        "context_name": "Math",
        "plannable": {
            "id": 123,
            "title": "Homework",
            "due_at": "2026-01-22T23:59:59Z",
            "description": "Do work"
        },
        "submissions": {"submitted": False}
    }
    assignment = CanvasAssignment.from_dict(data)
    assert assignment.name == "Homework"
    assert assignment.course_name == "Math"
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

def test_filter_submitted():
    now = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
    assignments = [
        CanvasAssignment("1", "Unsubmitted", "Math", now, is_submitted=False),
        CanvasAssignment("2", "Submitted", "Math", now, is_submitted=True),
    ]
    
    result = filter_assignments(assignments, now, "today")
    assert len(result) == 1
    assert result[0].name == "Unsubmitted"

def test_filter_upcoming_week():
    now = datetime(2026, 1, 22, 10, 0, 0, tzinfo=timezone.utc)
    assignments = [
        CanvasAssignment("1", "Upcoming", "Math", now + timedelta(days=3)),
        CanvasAssignment("2", "Too Far", "Math", now + timedelta(days=10)),
    ]
    
    result = filter_assignments(assignments, now, "upcoming_week", days=7)
    assert len(result) == 1
    assert result[0].name == "Upcoming"

def test_course_name_cleaning():
    assert clean_course_name("- Math 101") == "Math 101"
    assert clean_course_name("  - Physics 202  ") == "Physics 202"
    assert clean_course_name("CHEM-101 - Chemistry") == "Chemistry"
    assert clean_course_name("BIO101 - Biology") == "Biology"
    assert clean_course_name("English Comp") == "English Comp"
    assert clean_course_name(None) == "Unknown Course"
    
    # Raw data patterns from diag output
    assert clean_course_name("1st and 3rd period-Health-Fall2025-Paul") == "Health-Fall2025-Paul"
    assert clean_course_name("P1-Spanish 2 H-PASSAGLIA") == "Spanish 2 H-PASSAGLIA"
    assert clean_course_name("P2-Social Studies 6-Goldstein") == "Social Studies 6-Goldstein"
    assert clean_course_name("7th Grade 4th Period") == "7th Grade 4th Period" # Should not over-clean
    
    # Complex but descriptive
    assert clean_course_name("Introduction to Psychology - Sec 01") == "Introduction to Psychology - Sec 01"
