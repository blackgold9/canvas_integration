"""DataUpdateCoordinator for Canvas LMS."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import CanvasAPI
from .const import DOMAIN
from .assignment_logic import CanvasAssignment
from .student_logic import CanvasStudentData
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

class CanvasDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Canvas data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: CanvasAPI,
        entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self.api = api
        self.entry = entry
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=30),
        )

    async def _async_update_data(self) -> dict:
        """Update data via library."""
        try:
            data = {}
            # 1. Get Students (Observees)
            students = await self.api.async_get_students()
            if not students:
                # If no observees, maybe the user is a student themselves?
                user_info = await self.api.async_get_user_info()
                students = [user_info] # Minimal student info
            
            data["students"] = students
            data["student_data"] = {}
            _LOGGER.debug("Found %s students", len(students))

            for student in students:
                student_id = student["id"]
                # 2. Get ALL Courses with Grades in 1 call
                courses = await self.api.async_get_courses(user_id=student_id)
                _LOGGER.debug("Found %s courses for student %s", len(courses), student_id)
                
                final_courses = []
                context_codes = []
                now = dt_util.now()
                grace_period = timedelta(days=7)

                for course in courses:
                    if not course.get("name"):
                        continue
                    
                    # 1. Filter out archived courses by name
                    term_name = course.get("term", {}).get("name", "")
                    if "Archive" in term_name:
                        _LOGGER.debug("Skipping archived course by name: %s (%s)", course.get("name"), term_name)
                        continue

                    # 2. Filter out administrative/portal courses
                    course_name = course.get("name", "")
                    if any(word in course_name for word in ["Students", "Hub"]):
                        _LOGGER.debug("Skipping administrative course: %s", course_name)
                        continue

                    # 3. Filter out courses that have already ended (with 7-day grace)
                    # Check both course and term end dates
                    end_str = course.get("end_at") or course.get("term", {}).get("end_at")
                    if end_str:
                        try:
                            # Parse with Home Assistant utility for consistency
                            end_date = dt_util.parse_datetime(end_str)
                            if end_date and (end_date + grace_period) < now:
                                _LOGGER.debug(
                                    "Skipping ended course: %s (Ended: %s)", 
                                    course.get("name"), 
                                    end_str
                                )
                                continue
                        except (ValueError, TypeError):
                            _LOGGER.warning("Could not parse end_at for course %s", course.get("id"))

                    final_courses.append(course)
                    context_codes.append(f"course_{course['id']}")

                # 3. Get ALL Assignments/Submissions via Planner API in 1 call
                # Setting range from 30 days ago to 365 days ahead
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                end_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
                
                all_assignments = []
                if context_codes:
                    planner_items = await self.api.async_get_planner_items(
                        student_id, start_date, end_date, context_codes
                    )
                    
                    for item in planner_items:
                        if item.get("plannable_type") == "assignment":
                            all_assignments.append(CanvasAssignment.from_dict(item))

                _LOGGER.debug("Student %s: found %s total assignments via Planner", student_id, len(all_assignments))

                # Wrap in student logic class
                data["student_data"][student_id] = CanvasStudentData(
                    student_id=student_id,
                    name=student.get("name", f"Student {student_id}"),
                    courses=final_courses,
                    assignments=all_assignments
                )

            return data
        except Exception as exception:
            raise UpdateFailed(f"Error communicating with API: {exception}") from exception
