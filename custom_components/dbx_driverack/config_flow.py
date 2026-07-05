import voluptuous as vol
from homeassistant import config_entries

from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_PASSWORD,
    DEFAULT_USERNAME,
    DOMAIN,
)


class DriveRackConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for dbx DriveRack PA2."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Simple unique ID check based on host IP
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"DriveRack PA2 ({user_input[CONF_HOST]})",
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
            }),
            errors=errors,
        )
