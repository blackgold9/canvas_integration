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
        
        # 1. Assignment Timeline/Summary Sensors
        entities.extend([
            CanvasAssignmentSensor(coordinator, student_id, student_name, "today"),
            CanvasAssignmentSensor(coordinator, student_id, student_name, "tomorrow"),
            CanvasAssignmentSensor(
                coordinator, 
                student_id, 
                student_name, 
                "upcoming", 
                days=entry.options.get(CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS)
            ),
            CanvasAssignmentSensor(
                coordinator, 
                student_id, 
                student_name, 
                "missed", 
                days=entry.options.get(CONF_MISSED_DAYS, DEFAULT_MISSED_DAYS)
            ),
        ])

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
        self._attr_native_unit_of_measurement = "%"

    @property
    def native_value(self) -> str | float | None:
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

class CanvasAssignmentSensor(CoordinatorEntity[CanvasDataUpdateCoordinator], SensorEntity):
    """Unified Representation of a Canvas Assignment sensor."""

    def __init__(
        self,
        coordinator: CanvasDataUpdateCoordinator,
        student_id: str,
        student_name: str,
        sensor_type: str, # 'today', 'tomorrow', 'upcoming', 'missed'
        days: int | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._student_id = student_id
        self._student_name = student_name
        self._sensor_type = sensor_type
        self._days = days
        
        # Display Mapping
        type_names = {
            "today": "Due Today",
            "tomorrow": "Due Tomorrow",
            "upcoming": "Upcoming",
            "missed": "Missed",
        }
        icons = {
            "today": "mdi:calendar-today",
            "tomorrow": "mdi:calendar-arrow-right",
            "upcoming": "mdi:calendar-clock",
            "missed": "mdi:calendar-remove",
        }
        
        self._attr_name = f"{student_name} Assignments {type_names.get(sensor_type)}"
        self._attr_unique_id = f"canvas_{student_id}_assignments_{sensor_type}"
        self._attr_icon = icons.get(sensor_type, "mdi:notebook-edit")
        self._assignments: list[dict] = []

    @property
    def native_value(self) -> int:
        """Return the count of assignments."""
        self._update_list()
        return len(self._assignments)

    def _update_list(self) -> None:
        """Filter the coordinator data for this sensor's time window."""
        student_data = self.coordinator.data["student_data"].get(self._student_id)
        if not student_data or "assignments" not in student_data:
            self._assignments = []
            return

        now = dt_util.now()
        local_today = now.date()
        
        assignments = []
        for assignment in student_data["assignments"]:
            due_at_str = assignment.get("due_at")
            if not due_at_str:
                continue
            
            due_at = dt_util.parse_datetime(due_at_str)
            if not due_at:
                continue

            local_due = dt_util.as_local(due_at)
            local_due_date = local_due.date()

            include = False
            
            if self._sensor_type == "today":
                include = local_due_date == local_today
            elif self._sensor_type == "tomorrow":
                include = local_due_date == (local_today + timedelta(days=1))
            elif self._sensor_type == "upcoming":
                limit = now + timedelta(days=self._days or 7)
                include = now < due_at <= limit
            elif self._sensor_type == "missed":
                limit = now - timedelta(days=self._days or 7)
                include = limit <= due_at <= now

            if include:
                assignments.append({
                    "name": assignment["name"],
                    "course": assignment.get("course_name", "Unknown"),
                    "due_at": due_at_str,
                })

        # Sort: Upcoming/Soonest first, but for missed show most recent first
        reverse_sort = self._sensor_type == "missed"
        self._assignments = sorted(assignments, key=lambda x: x["due_at"], reverse=reverse_sort)

    @property
    def extra_state_attributes(self) -> dict:
        """Return entity specific state attributes."""
        attrs = {
            "student_name": self._student_name,
            "assignments": self._assignments,
            "count": len(self._assignments),
        }
        if self._days:
            attrs["window_days"] = self._days
        return attrs
