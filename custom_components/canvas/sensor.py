"""Sensor platform for Canvas LMS."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CanvasDataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Canvas sensors."""
    coordinator: CanvasDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    
    # Create a sensor for each student and each course they are enrolled in
    for student_id, student_data in coordinator.data["student_data"].items():
        student_info = student_data["info"]
        student_name = student_info.get("name", f"Student {student_id}")
        
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
