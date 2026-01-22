import json
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
async def test_coordinator_update_data(aresponses, mock_observees, mock_courses, mock_enrollments, mock_assignments):
    # 1. Observees
    aresponses.add(
        "example.com",
        "/api/v1/users/self/observees",
        "GET",
        aresponses.Response(text=json.dumps(mock_observees), status=200, content_type="application/json")
    )
    
    # 2. Courses for Student A (67890)
    aresponses.add(
        "example.com",
        "/api/v1/users/67890/courses",
        "GET",
        aresponses.Response(text=json.dumps(mock_courses), status=200, content_type="application/json")
    )
    
    # 3. Enrollment for Math 101 (Course 101)
    aresponses.add(
        "example.com",
        "/api/v1/courses/101/enrollments",
        "GET",
        aresponses.Response(text=json.dumps(mock_enrollments), status=200, content_type="application/json")
    )
    
    # 4. Assignments for Math 101
    aresponses.add(
        "example.com",
        "/api/v1/courses/101/assignments",
        "GET",
        aresponses.Response(text=json.dumps(mock_assignments), status=200, content_type="application/json")
    )
    
    # 5. Enrollment for History 101 (Course 102)
    aresponses.add(
        "example.com",
        "/api/v1/courses/102/enrollments",
        "GET",
        aresponses.Response(text="[]", status=200, content_type="application/json")
    )
    
    # 6. Assignments for History 101
    aresponses.add(
        "example.com",
        "/api/v1/courses/102/assignments",
        "GET",
        aresponses.Response(text="[]", status=200, content_type="application/json")
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
        
        # Course 101 was added because it had enrollments, 102 was nicht because we mocked empty enrollment
        assert len(student_data["courses"]) == 1
        assert student_data["courses"][0]["id"] == 101
        
        # Assignments for Course 101
        assert len(student_data["assignments"]) == 2
        assert student_data["assignments"][0]["name"] == "Homework 1"
