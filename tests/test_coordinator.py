import json
import re
import pytest
import aiohttp
from unittest.mock import MagicMock
from custom_components.canvas.api import CanvasAPI
from custom_components.canvas.coordinator import CanvasDataUpdateCoordinator

@pytest.fixture
def mock_observees():
    with open("tests/fixtures/observees.json") as f:
        return json.load(f)

@pytest.fixture
def mock_courses():
    with open("tests/fixtures/courses.json") as f:
        return json.load(f)

@pytest.fixture
def mock_enrollments():
    with open("tests/fixtures/enrollments.json") as f:
        return json.load(f)

@pytest.fixture
def mock_assignments():
    with open("tests/fixtures/assignments.json") as f:
        return json.load(f)

@pytest.mark.asyncio
async def test_coordinator_update_data(aresponses, mock_observees, mock_courses):
    # 1. Observees
    aresponses.add(
        "example.com",
        re.compile(r"/api/v1/users/self/observees.*"),
        "GET",
        aresponses.Response(text=json.dumps(mock_observees), status=200, content_type="application/json")
    )
    
    # 2. Courses for Student A (67890)
    aresponses.add(
        "example.com",
        re.compile(r"/api/v1/users/67890/courses.*"),
        "GET",
        aresponses.Response(text=json.dumps(mock_courses), status=200, content_type="application/json")
    )
    
    # 3. Planner Items for Student A
    mock_planner_items = [
        {
            "plannable_type": "assignment",
            "context_name": "Math 101",
            "plannable": {
                "id": 123,
                "title": "Homework 1",
                "due_at": "2026-01-22T23:59:59Z",
                "description": "Solve problems"
            },
            "submissions": {"submitted": False}
        }
    ]
    aresponses.add(
        "example.com",
        re.compile(r"/api/v1/planner/items.*"),
        "GET",
        aresponses.Response(text=json.dumps(mock_planner_items), status=200, content_type="application/json")
    )
    
    async with aiohttp.ClientSession() as session:
        api = CanvasAPI("https://example.com", "token", session)
        hass = MagicMock()
        entry = MagicMock()
        
        coordinator = CanvasDataUpdateCoordinator(hass, api, entry)
        
        # We call the internal method directly for the test
        data = await coordinator._async_update_data()
        
        assert "students" in data
        assert len(data["students"]) == 1
        assert data["students"][0]["id"] == 67890
        
        assert 67890 in data["student_data"]
        student_data = data["student_data"][67890]
        
        # Both courses matched from the fixture
        assert len(student_data.courses) == 2
        
        # Grade data check
        enrollment = student_data.courses[0]["enrollments"][0]
        assert enrollment["computed_current_score"] == 95.5
        
        # Assignments for Student A via Planner
        assert len(student_data.assignments) == 1
        assert student_data.assignments[0].name == "Homework 1"
