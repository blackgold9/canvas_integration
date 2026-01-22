import json
import os
import pytest
import aiohttp
from custom_components.canvas.api import CanvasAPI

@pytest.fixture
def mock_user_profile():
    with open("tests/fixtures/user_profile.json") as f:
        return json.load(f)

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
async def test_get_user_info(aresponses, mock_user_profile):
    aresponses.add(
        "example.com",
        "/api/v1/users/self/profile",
        "GET",
        aresponses.Response(text=json.dumps(mock_user_profile), status=200, content_type="application/json")
    )
    
    async with aiohttp.ClientSession() as session:
        api = CanvasAPI("https://example.com", "token", session)
        result = await api.async_get_user_info()
        assert result["name"] == "Test User"
        assert result["id"] == 12345

@pytest.mark.asyncio
async def test_get_students(aresponses, mock_observees):
    aresponses.add(
        "example.com",
        "/api/v1/users/self/observees",
        "GET",
        aresponses.Response(text=json.dumps(mock_observees), status=200, content_type="application/json")
    )
    
    async with aiohttp.ClientSession() as session:
        api = CanvasAPI("https://example.com", "token", session)
        result = await api.async_get_students()
        assert len(result) == 1
        assert result[0]["name"] == "Student A"

@pytest.mark.asyncio
async def test_get_enrollment_for_course(aresponses, mock_enrollments):
    aresponses.add(
        "example.com",
        "/api/v1/courses/101/enrollments",
        "GET",
        aresponses.Response(text=json.dumps(mock_enrollments), status=200, content_type="application/json")
    )
    
    async with aiohttp.ClientSession() as session:
        api = CanvasAPI("https://example.com", "token", session)
        result = await api.async_get_enrollment_for_course("101", "67890")
        assert len(result) == 1
        assert result[0]["grades"]["current_score"] == 95.5

@pytest.mark.asyncio
async def test_api_error(aresponses):
    aresponses.add(
        "example.com",
        "/api/v1/users/self/profile",
        "GET",
        aresponses.Response(text="Error", status=404)
    )
    
    async with aiohttp.ClientSession() as session:
        api = CanvasAPI("https://example.com", "token", session)
        with pytest.raises(aiohttp.ClientResponseError):
            await api.async_get_user_info()
