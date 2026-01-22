"""Config flow for Canvas LMS integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_URL, CONF_TOKEN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CanvasAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_TOKEN): str,
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Canvas LMS."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                api = CanvasAPI(user_input[CONF_URL], user_input[CONF_TOKEN], session)
                await api.async_get_user_info()
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Canvas LMS", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
