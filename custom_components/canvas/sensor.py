"""Sensor platform for Canvas LMS."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    DEFAULT_UPCOMING_DAYS,
    DEFAULT_MISSED_DAYS,
    CONF_UPCOMING_DAYS,
    CONF_MISSED_DAYS,
)
from .coordinator import CanvasDataUpdateCoordinator
from .assignment_logic import filter_assignments, clean_course_name

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
        student_name = student_data.name
        
        # 1. Assignment Timeline/Summary Sensors
        entities.extend([
            CanvasAssignmentSensor(coordinator, student_id, student_name, "today"),
            CanvasAssignmentSensor(coordinator, student_id, student_name, "tomorrow"),
            CanvasAssignmentSensor(
                coordinator, 
                student_id, 
                student_name, 
                "upcoming_week", 
                days=entry.options.get(CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS)
            ),
            CanvasAssignmentSensor(
                coordinator, 
                student_id, 
                student_name, 
                "missed", 
                days=entry.options.get(CONF_MISSED_DAYS, DEFAULT_MISSED_DAYS)
            ),
            CanvasLastMissedSensor(
                coordinator,
                student_id,
                student_name,
                days=entry.options.get(CONF_MISSED_DAYS, DEFAULT_MISSED_DAYS)
            ),
        ])

        # 2. Grade sensors for each course
        for course in student_data.courses:
            # Check if there's an enrollment with a grade
            enrollments = course.get("enrollments", [])
            for enrollment in enrollments:
                enrollment_type = enrollment.get("type", "").lower()
                if enrollment_type in ["studentenrollment", "student"]:
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
        raw_name = course.get("name", course.get("course_code", "Unknown Course"))
        self._course_name = clean_course_name(raw_name)
        self._enrollment = enrollment
        
        self._attr_has_entity_name = True
        self._attr_name = f"{self._course_name} Grade"
        self._attr_unique_id = f"canvas_{student_id}_{self._course_id}_grade"
        self._attr_icon = "mdi:school"
        self._attr_native_unit_of_measurement = "%"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, student_id)},
            name=student_name,
            manufacturer="Canvas LMS",
            model="Student",
        )

    @property
    def native_value(self) -> str | float | None:
        """Return the state of the sensor."""
        # Refresh enrollment data from coordinator
        student_data = self.coordinator.data["student_data"].get(self._student_id)
        if not student_data:
            return None
            
        for course in student_data.courses:
            if course["id"] == self._course_id:
                for enrollment in course.get("enrollments", []):
                    # For total_scores include, it's computed_current_score
                    return enrollment.get("computed_current_score") or enrollment.get("computed_current_grade")
        
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return entity specific state attributes."""
        student_data = self.coordinator.data["student_data"].get(self._student_id)
        if not student_data:
            return {}
            
        current_enrollment = {}
        for course in student_data.courses:
            if course["id"] == self._course_id:
                for enrollment in course.get("enrollments", []):
                    current_enrollment = enrollment
                    break

        return {
            "course_name": self._course_name,
            "student_name": self._student_name,
            "current_score": current_enrollment.get("computed_current_score"),
            "current_grade": current_enrollment.get("computed_current_grade"),
            "final_score": current_enrollment.get("computed_final_score"),
            "final_grade": current_enrollment.get("computed_final_grade"),
        }

class CanvasAssignmentSensor(CoordinatorEntity[CanvasDataUpdateCoordinator], SensorEntity):
    """Unified Representation of a Canvas Assignment sensor."""

    def __init__(
        self,
        coordinator: CanvasDataUpdateCoordinator,
        student_id: str,
        student_name: str,
        sensor_type: str, # 'today', 'tomorrow', 'upcoming_week', 'missed'
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
            "today": "Assignments Due Today",
            "tomorrow": "Assignments Due Tomorrow",
            "upcoming_week": "Assignments Upcoming Week",
            "missed": "Assignments Missed",
        }
        icons = {
            "today": "mdi:calendar-today",
            "tomorrow": "mdi:calendar-arrow-right",
            "upcoming_week": "mdi:calendar-clock",
            "missed": "mdi:calendar-remove",
        }
        
        self._attr_has_entity_name = True
        self._attr_name = type_names.get(sensor_type, "Assignments")
        self._attr_unique_id = f"canvas_{student_id}_assignments_{sensor_type}"
        self._attr_icon = icons.get(sensor_type, "mdi:notebook-edit")
        self._assignments: list[dict] = []
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, student_id)},
            name=student_name,
            manufacturer="Canvas LMS",
            model="Student",
        )

    @property
    def native_value(self) -> int:
        """Return the count of assignments."""
        self._update_list()
        return len(self._assignments)

    def _update_list(self) -> None:
        """Filter the coordinator data for this sensor's time window."""
        student_data = self.coordinator.data["student_data"].get(self._student_id)
        if not student_data:
            self._assignments = []
            return

        # Use our external logic for filtering
        now = dt_util.now()
        filtered = filter_assignments(
            student_data.assignments, 
            now, 
            self._sensor_type, 
            days=self._days or 7
        )

        self._assignments = [
            {
                "id": a.id,
                "name": a.name,
                "course": a.course_name,
                "due_at": a.due_at.isoformat() if a.due_at else None,
            }
            for a in filtered
        ]

    @property
    def assignment_ids(self) -> list[str]:
        """Return the list of assignment IDs."""
        return [a["id"] for a in self._assignments]

    @property
    def extra_state_attributes(self) -> dict:
        """Return entity specific state attributes."""
        attrs = {
            "student_name": self._student_name,
            "assignments": self._assignments,
            "assignment_ids": self.assignment_ids,
            "count": len(self._assignments),
        }
        if self._days:
            attrs["window_days"] = self._days
        return attrs

class CanvasLastMissedSensor(CoordinatorEntity[CanvasDataUpdateCoordinator], SensorEntity):
    """Representation of the most recently missed Canvas assignment."""

    def __init__(
        self,
        coordinator: CanvasDataUpdateCoordinator,
        student_id: str,
        student_name: str,
        days: int | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._student_id = student_id
        self._student_name = student_name
        self._days = days
        
        self._attr_has_entity_name = True
        self._attr_name = "Last Missed Assignment"
        self._attr_unique_id = f"canvas_{student_id}_last_missed"
        self._attr_icon = "mdi:calendar-alert"
        self._last_missed: dict | None = None
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, student_id)},
            name=student_name,
            manufacturer="Canvas LMS",
            model="Student",
        )

    @property
    def native_value(self) -> str | None:
        """Return the name of the last missed assignment."""
        self._update_state()
        return self._last_missed.get("name") if self._last_missed else None

    def _update_state(self) -> None:
        """Update the last missed assignment from coordinator data."""
        student_data = self.coordinator.data["student_data"].get(self._student_id)
        if not student_data:
            self._last_missed = None
            return

        now = dt_util.now()
        missed = filter_assignments(
            student_data.assignments, 
            now, 
            "missed", 
            days=self._days or 7
        )

        if not missed:
            self._last_missed = None
            return

        # Sort by due_at descending to get the most recent one
        # filter_assignments returns a list, we sort it here
        missed.sort(key=lambda x: x.due_at, reverse=True)
        
        latest = missed[0]
        self._last_missed = {
            "id": latest.id,
            "name": latest.name,
            "course": latest.course_name,
            "due_at": latest.due_at.isoformat() if latest.due_at else None,
        }

    @property
    def extra_state_attributes(self) -> dict:
        """Return entity specific state attributes."""
        attrs = {
            "student_name": self._student_name,
        }
        if self._last_missed:
            attrs.update(self._last_missed)
        if self._days:
            attrs["window_days"] = self._days
        return attrs
