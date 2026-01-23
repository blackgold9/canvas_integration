"""API Client for Canvas LMS."""
from __future__ import annotations

import logging
import aiohttp
import async_timeout

_LOGGER = logging.getLogger(__name__)

class CanvasAPI:
    """Canvas API Client."""

    def __init__(self, url: str, token: str, session: aiohttp.ClientSession) -> None:
        """Initialize."""
        self._url = url.rstrip("/")
        self._token = token
        self._session = session

    async def async_get_user_info(self) -> dict:
        """Get information about the current user."""
        return await self._async_get("/api/v1/users/self/profile")

    async def async_get_students(self) -> list:
        """Get observed students."""
        return await self._async_get_paginated("/api/v1/users/self/observees")


    async def async_get_enrollments(self, user_id: str) -> list:
        """Get enrollments for a user (includes grades and course)."""
        params = [("include[]", "course"), ("include[]", "grades")]
        return await self._async_get_paginated(f"/api/v1/users/{user_id}/enrollments", params=params)

    async def async_get_courses(self, user_id: str | None = None) -> list:
        """Get courses for a user, including total scores and term info."""
        endpoint = f"/api/v1/users/{user_id}/courses" if user_id else "/api/v1/courses"
        params = [("include[]", "total_scores"), ("include[]", "term"), ("include[]", "enrollments")]
        return await self._async_get_paginated(endpoint, params=params)

    async def async_get_assignments(self, course_id: str) -> list:
        """Get assignments for a course."""
        return await self._async_get_paginated(f"/api/v1/courses/{course_id}/assignments")

    async def async_get_planner_items(self, student_id: str, start_date: str, end_date: str, context_codes: list[str]) -> list:
        """Get planner items for a student in bulk."""
        params = [
            ("observed_user_id", student_id),
            ("start_date", start_date),
            ("end_date", end_date),
        ]
        for code in context_codes:
            params.append(("context_codes[]", code))
            
        return await self._async_get_paginated("/api/v1/planner/items", params=params)

    async def _async_get_paginated(self, endpoint: str, params: dict | list | None = None) -> list:
        """Make a GET request and follow pagination links."""
        if params is None:
            params = {}
        
        # Ensure per_page is set
        if isinstance(params, dict):
            params["per_page"] = 100
        else:
            # list of tuples
            params.append(("per_page", 100))
        
        results = []
        url = f"{self._url}{endpoint}"
        
        while url:
            headers = {
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
            }
            
            try:
                async with async_timeout.timeout(10):
                    response = await self._session.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    data = await response.json()
                    
                    if isinstance(data, list):
                        results.extend(data)
                    else:
                        # Fallback for non-list responses (though usually wouldn't be paginated)
                        return data

                    # Check Link header for next page
                    url = None
                    params = None # Parameters are already in the Link URL
                    if "Link" in response.headers:
                        links = response.headers["Link"].split(",")
                        for link in links:
                            if 'rel="next"' in link:
                                # Extract URL between < and >
                                url = link.split(";")[0].strip("< >")
                                break
            except Exception as err:
                _LOGGER.error("Error fetching paginated data from Canvas: %s", err)
                raise

        return results

    async def _async_get(self, endpoint: str, params: dict | None = None) -> any:
        """Make a GET request."""
        url = f"{self._url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }
        
        try:
            async with async_timeout.timeout(10):
                response = await self._session.get(url, headers=headers, params=params)
                response.raise_for_status()
                return await response.json()
        except Exception as err:
            _LOGGER.error("Error fetching data from Canvas: %s", err)
            raise
