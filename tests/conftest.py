import sys
from unittest.mock import MagicMock, AsyncMock

# Define a minimal DataUpdateCoordinator for inheritance in tests
class MockDataUpdateCoordinator:
    def __init__(self, hass, logger, **kwargs):
        self.hass = hass
        self.logger = logger
        self.data = None

class MockCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator
    def __class_getitem__(cls, _):
        return cls

class MockSensorEntity:
    pass

class MockCalendarEntity:
    pass

class MockDeviceInfo:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
    def __eq__(self, other):
        if not isinstance(other, MockDeviceInfo):
            return False
        return self.__dict__ == other.__dict__

# Mock homeassistant modules
mock_hass = MagicMock()
mock_hass.async_create_task = AsyncMock()

sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.components"] = MagicMock()
sys.modules["homeassistant.components.sensor"] = MagicMock()
sys.modules["homeassistant.components.sensor"].SensorEntity = MockSensorEntity
sys.modules["homeassistant.components.calendar"] = MagicMock()
sys.modules["homeassistant.components.calendar"].CalendarEntity = MockCalendarEntity
sys.modules["homeassistant.helpers"] = MagicMock()
mock_device_reg = MagicMock()
mock_device_reg.DeviceInfo = MockDeviceInfo
sys.modules["homeassistant.helpers.device_registry"] = mock_device_reg
sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()
sys.modules["homeassistant.helpers.entity_platform"] = MagicMock()
sys.modules["homeassistant.util"] = MagicMock()

# Specifically handle the update_coordinator module
mock_coordinator_mod = MagicMock()
mock_coordinator_mod.DataUpdateCoordinator = MockDataUpdateCoordinator
mock_coordinator_mod.CoordinatorEntity = MockCoordinatorEntity
mock_coordinator_mod.UpdateFailed = Exception
sys.modules["homeassistant.helpers.update_coordinator"] = mock_coordinator_mod
