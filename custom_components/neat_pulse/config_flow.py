# config_flow.py

import logging
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_ACCESS_TOKEN,
    CONF_ORGANIZATION_ID,
    CONF_ENDPOINT_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)
from .api import NeatPulseAPI, AuthenticationError, NeatPulseAPIError

_LOGGER = logging.getLogger(__name__)

class NeatPulseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Neat Pulse."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            access_token = user_input[CONF_ACCESS_TOKEN]
            organization_id = user_input[CONF_ORGANIZATION_ID]
            endpoint_id = user_input.get(CONF_ENDPOINT_ID)

            # Validate credentials and IDs
            session = aiohttp.ClientSession()
            api = NeatPulseAPI(session, access_token, organization_id)
            try:
                if endpoint_id:
                    # Try to fetch sensor data for the endpoint
                    sensor_data = await api.get_endpoint_sensor_data(endpoint_id)
                    # If successful, proceed
                else:
                    errors["base"] = "no_endpoint_id"
                await session.close()
                return self.async_create_entry(
                    title="Neat Pulse",
                    data={
                        CONF_ACCESS_TOKEN: access_token,
                        CONF_ORGANIZATION_ID: organization_id,
                        CONF_ENDPOINT_ID: endpoint_id,
                    },
                )
            except AuthenticationError:
                errors["base"] = "auth"
            except NeatPulseAPIError as e:
                errors["base"] = "api_error"
                _LOGGER.error(f"API error during authentication: {e}")
            except Exception as e:
                _LOGGER.error(f"Unexpected error during authentication: {e}")
                errors["base"] = "unknown"
            await session.close()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN, title="API Key"): str,
                vol.Required(CONF_ORGANIZATION_ID, title="Organization ID"): str,
                vol.Required(CONF_ENDPOINT_ID, title="Device ID"): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return NeatPulseOptionsFlowHandler(config_entry)

class NeatPulseOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Neat Pulse options."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the Neat Pulse options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=current_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=1))
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
