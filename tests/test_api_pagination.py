import json
import pytest
import aiohttp
from custom_components.canvas.api import CanvasAPI

@pytest.mark.asyncio
async def test_get_paginated_data(aresponses):
    # Mock first page
    aresponses.add(
        "example.com",
        "/api/v1/courses/101/assignments",
        "GET",
        aresponses.Response(
            text=json.dumps([{"id": 1, "name": "Assignment 1"}]),
            status=200,
            content_type="application/json",
            headers={
                "Link": '<https://example.com/api/v1/courses/101/assignments?page=2&per_page=100>; rel="next"'
            }
        )
    )
    
    # Mock second page
    aresponses.add(
        "example.com",
        "/api/v1/courses/101/assignments",
        "GET",
        aresponses.Response(
            text=json.dumps([{"id": 2, "name": "Assignment 2"}]),
            status=200,
            content_type="application/json"
        )
    )
    
    async with aiohttp.ClientSession() as session:
        api = CanvasAPI("https://example.com", "token", session)
        result = await api.async_get_assignments("101")
        
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
