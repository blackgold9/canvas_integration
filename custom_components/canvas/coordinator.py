"""DataUpdateCoordinator for Canvas LMS."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CanvasAPI
from .const import DOMAIN
from .assignment_logic import CanvasAssignment
from .student_logic import CanvasStudentData

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
                # 2. Get Courses for this student
                courses = await self.api.async_get_courses(user_id=student_id)
                _LOGGER.debug("Found %s courses for student %s", len(courses), student_id)
                
                # 3. For each course, get the student's enrollment to get grades
                # AND Get Assignments
                all_assignments = []
                final_courses = []
                for course in courses:
                    course_id = course["id"]
                    if not course.get("name"):
                        continue
                    
                    try:
                        # Get enrollment for grades
                        enrollments = await self.api.async_get_enrollment_for_course(course_id, student_id)
                        if enrollments:
                            course["enrollments"] = enrollments
                            final_courses.append(course)
                        
                        # Get assignments
                        assignments = await self.api.async_get_assignments(course_id)
                        for assignment in assignments:
                            assignment["course_name"] = course.get("name")
                            assignment["student_name"] = student.get("name")
                        all_assignments.extend(assignments)
                        _LOGGER.debug("Course %s: found %s assignments", course_id, len(assignments))
                    except Exception as err:
                        _LOGGER.warning("Could not fetch data for course %s: %s", course_id, err)

                # Wrap in student logic class
                data["student_data"][student_id] = CanvasStudentData(
                    student_id=student_id,
                    name=student.get("name", f"Student {student_id}"),
                    courses=final_courses,
                    assignments=[
                        CanvasAssignment.from_dict(a, a.get("course_name", "Unknown"))
                        for a in all_assignments
                    ]
                )

            return data
        except Exception as exception:
            raise UpdateFailed(f"Error communicating with API: {exception}") from exception
