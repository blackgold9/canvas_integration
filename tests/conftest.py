import sys
from unittest.mock import MagicMock, AsyncMock

# Define a minimal DataUpdateCoordinator for inheritance in tests
class MockDataUpdateCoordinator:
    def __init__(self, hass, logger, **kwargs):
        self.hass = hass
        self.logger = logger
        self.data = None

# Mock homeassistant modules
mock_hass = MagicMock()
mock_hass.async_create_task = AsyncMock()

sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.config_entries"] = MagicMock()
sys.modules["homeassistant.const"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()
sys.modules["homeassistant.util"] = MagicMock()

# Specifically handle the update_coordinator module
mock_coordinator_mod = MagicMock()
mock_coordinator_mod.DataUpdateCoordinator = MockDataUpdateCoordinator
mock_coordinator_mod.UpdateFailed = Exception
sys.modules["homeassistant.helpers.update_coordinator"] = mock_coordinator_mod
