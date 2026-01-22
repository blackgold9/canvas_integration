"""Sensor platform for Canvas LMS."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DEFAULT_UPCOMING_DAYS,
    DEFAULT_MISSED_DAYS,
    CONF_UPCOMING_DAYS,
    CONF_MISSED_DAYS,
)
from .coordinator import CanvasDataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Canvas sensors."""
    coordinator: CanvasDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    
    # Create sensors for each student
    for student_id, student_data in coordinator.data["student_data"].items():
        student_info = student_data["info"]
        student_name = student_info.get("name", f"Student {student_id}")
        
        # 1. Assignment Summary Sensor
        entities.append(
            CanvasAssignmentsSensor(
                coordinator,
                student_id,
                student_name,
                entry.options.get(CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS),
                entry.options.get(CONF_MISSED_DAYS, DEFAULT_MISSED_DAYS),
            )
        )

        # 2. Grade sensors for each course
        for course in student_data["courses"]:
            # Check if there's an enrollment with a grade
            enrollments = course.get("enrollments", [])
            for enrollment in enrollments:
                if enrollment.get("type") == "StudentEnrollment":
                    entities.append(
                        CanvasGradeSensor(
                            coordinator,
                            student_id,
                            student_name,
                            course,
                            enrollment
                        )
                    )

    async_add_entities(entities)

class CanvasGradeSensor(CoordinatorEntity[CanvasDataUpdateCoordinator], SensorEntity):
    """Representation of a Canvas Course Grade sensor."""

    def __init__(
        self,
        coordinator: CanvasDataUpdateCoordinator,
        student_id: str,
        student_name: str,
        course: dict,
        enrollment: dict,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._student_id = student_id
        self._student_name = student_name
        self._course_id = course["id"]
        self._course_name = course.get("name", course.get("course_code", "Unknown Course"))
        self._enrollment = enrollment
        
        self._attr_name = f"{student_name} - {self._course_name} Grade"
        self._attr_unique_id = f"canvas_{student_id}_{self._course_id}_grade"
        self._attr_icon = "mdi:school"

    @property
    def state(self) -> str | float | None:
        """Return the state of the sensor."""
        # Refresh enrollment data from coordinator
        student_data = self.coordinator.data["student_data"].get(self._student_id)
        if not student_data:
            return None
            
        for course in student_data["courses"]:
            if course["id"] == self._course_id:
                for enrollment in course.get("enrollments", []):
                    grades = enrollment.get("grades", {})
                    # Return current score or grade from the 'grades' sub-dict
                    return grades.get("current_score") or grades.get("current_grade")
        
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return entity specific state attributes."""
        student_data = self.coordinator.data["student_data"].get(self._student_id)
        if not student_data:
            return {}
            
        current_grades = {}
        for course in student_data["courses"]:
            if course["id"] == self._course_id:
                for enrollment in course.get("enrollments", []):
                    current_grades = enrollment.get("grades", {})
                    break

        return {
            "course_name": self._course_name,
            "student_name": self._student_name,
            "current_score": current_grades.get("current_score"),
            "current_grade": current_grades.get("current_grade"),
            "final_score": current_grades.get("final_score"),
            "final_grade": current_grades.get("final_grade"),
        }

class CanvasAssignmentsSensor(CoordinatorEntity[CanvasDataUpdateCoordinator], SensorEntity):
    """Representation of a Canvas Assignment Summary sensor."""

    def __init__(
        self,
        coordinator: CanvasDataUpdateCoordinator,
        student_id: str,
        student_name: str,
        upcoming_days: int,
        missed_days: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._student_id = student_id
        self._student_name = student_name
        self._upcoming_days = upcoming_days
        self._missed_days = missed_days
        
        self._attr_name = f"{student_name} Assignments"
        self._attr_unique_id = f"canvas_{student_id}_assignments_summary"
        self._attr_icon = "mdi:notebook-edit"
        self._upcoming: list[dict] = []
        self._missed: list[dict] = []

    @property
    def state(self) -> int:
        """Return the state of the sensor (total important assignments)."""
        self._update_assignment_lists()
        return len(self._upcoming) + len(self._missed)

    def _update_assignment_lists(self) -> None:
        """Update the internal lists of upcoming and missed assignments."""
        student_data = self.coordinator.data["student_data"].get(self._student_id)
        if not student_data or "assignments" not in student_data:
            self._upcoming = []
            self._missed = []
            return

        now = dt_util.now()
        upcoming_limit = now + dt_util.dt.timedelta(days=self._upcoming_days)
        missed_limit = now - dt_util.dt.timedelta(days=self._missed_days)

        upcoming = []
        missed = []

        for assignment in student_data["assignments"]:
            due_at_str = assignment.get("due_at")
            if not due_at_str:
                continue
            
            due_at = dt_util.parse_datetime(due_at_str)
            if not due_at:
                continue

            assignment_info = {
                "name": assignment["name"],
                "course": assignment.get("course_name", "Unknown"),
                "due_at": due_at_str,
            }

            # Check if it's in the upcoming window
            if now < due_at <= upcoming_limit:
                upcoming.append(assignment_info)
            
            # Check if it's in the missed window
            # For now, we consider it "missed" if it's past due and within the last X days.
            # In a future update, we can check for submission status if we fetch it.
            elif missed_limit <= due_at <= now:
                # We also check if it has been graded as a proxy for "not missed"
                # But that's hard to do without assignment-level submission info.
                # For now, let's keep it simple: past due in the last 7 days.
                missed.append(assignment_info)

        self._upcoming = sorted(upcoming, key=lambda x: x["due_at"])
        self._missed = sorted(missed, key=lambda x: x["due_at"], reverse=True)

    @property
    def extra_state_attributes(self) -> dict:
        """Return entity specific state attributes."""
        return {
            "student_name": self._student_name,
            "upcoming_assignments": self._upcoming,
            "missed_assignments": self._missed,
            "upcoming_count": len(self._upcoming),
            "missed_count": len(self._missed),
            "upcoming_window_days": self._upcoming_days,
            "missed_window_days": self._missed_days,
        }
