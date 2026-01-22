"""Calendar platform for Canvas LMS."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import CanvasDataUpdateCoordinator
from .calendar_logic import get_calendar_events

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Canvas calendar."""
    coordinator: CanvasDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for student_id, student_data in coordinator.data["student_data"].items():
        entities.append(CanvasCalendarEntity(coordinator, student_id, student_data.name))

    async_add_entities(entities)

class CanvasCalendarEntity(CoordinatorEntity[CanvasDataUpdateCoordinator], CalendarEntity):
    """Representation of a Canvas Assignment Calendar."""

    def __init__(
        self,
        coordinator: CanvasDataUpdateCoordinator,
        student_id: str,
        student_name: str,
    ) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator)
        self._student_id = student_id
        self._student_name = student_name
        self._attr_name = f"Canvas - {student_name} Assignments"
        self._attr_unique_id = f"canvas_{student_id}_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        now = dt_util.now()
        events = self._get_events(now, now + timedelta(days=365))
        return events[0] if events else None

    def _get_events(self, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        """Get events between two dates."""
        student_data = self.coordinator.data["student_data"].get(self._student_id)
        if not student_data:
            return []

        logic_events = get_calendar_events(student_data.assignments, start_date, end_date)
        
        return [
            CalendarEvent(
                summary=event.summary,
                start=event.start,
                end=event.end,
                description=event.description,
                location=event.location,
            )
            for event in logic_events
        ]

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events between two dates."""
        return self._get_events(start_date, end_date)
