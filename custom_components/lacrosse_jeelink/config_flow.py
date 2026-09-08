"""Config flow for LaCrosse Jeelink."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_DEVICE
from homeassistant.core import callback
from homeassistant.util import slugify

from .const import (
    CONF_BAUD,
    CONF_EXPIRE_AFTER,
    CONF_RADIO_ID,
    CONF_SENSOR_KEY,
    CONF_SENSOR_NAME,
    CONF_SENSORS,
    DEFAULT_BAUD,
    DEFAULT_DEVICE,
    DEFAULT_EXPIRE_AFTER,
    DOMAIN,
)


class LaCrosseJeelinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LaCrosse Jeelink."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up the Jeelink serial connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device = user_input[CONF_DEVICE].strip()
            baud = int(user_input[CONF_BAUD])

            await self.async_set_unique_id(device)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"LaCrosse Jeelink ({device})",
                data={CONF_DEVICE: device, CONF_BAUD: baud},
                options={CONF_SENSORS: {}},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE, default=DEFAULT_DEVICE): str,
                vol.Required(CONF_BAUD, default=DEFAULT_BAUD): vol.All(
                    vol.Coerce(int), vol.Range(min=1)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change serial connection settings."""
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            device = user_input[CONF_DEVICE].strip()
            baud = int(user_input[CONF_BAUD])
            for other_entry in self._async_current_entries():
                if other_entry.entry_id != entry.entry_id and other_entry.data.get(CONF_DEVICE) == device:
                    return self.async_abort(reason="already_configured")
            return self.async_update_reload_and_abort(
                entry,
                data_updates={CONF_DEVICE: device, CONF_BAUD: baud},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE, default=entry.data[CONF_DEVICE]): str,
                vol.Required(
                    CONF_BAUD, default=entry.data.get(CONF_BAUD, DEFAULT_BAUD)
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LaCrosseJeelinkOptionsFlow:
        """Return the options flow."""
        return LaCrosseJeelinkOptionsFlow()


class LaCrosseJeelinkOptionsFlow(OptionsFlowWithReload):
    """Manage LaCrosse radio sensors."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the sensor management menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_sensor", "remove_sensor"],
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a physical LaCrosse sensor."""
        errors: dict[str, str] = {}
        sensors = dict(self.config_entry.options.get(CONF_SENSORS, {}))

        if user_input is not None:
            name = user_input[CONF_SENSOR_NAME].strip()
            radio_id = int(user_input[CONF_RADIO_ID])
            expire_after = int(user_input[CONF_EXPIRE_AFTER])
            sensor_key = slugify(name)

            if not sensor_key:
                errors[CONF_SENSOR_NAME] = "invalid_name"
            elif sensor_key in sensors:
                errors[CONF_SENSOR_NAME] = "name_exists"
            elif any(int(item[CONF_RADIO_ID]) == radio_id for item in sensors.values()):
                errors[CONF_RADIO_ID] = "radio_id_exists"
            else:
                sensors[sensor_key] = {
                    "name": name,
                    CONF_RADIO_ID: radio_id,
                    CONF_EXPIRE_AFTER: expire_after,
                }
                return self.async_create_entry(
                    data={**self.config_entry.options, CONF_SENSORS: sensors}
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_SENSOR_NAME): str,
                vol.Required(CONF_RADIO_ID): vol.All(vol.Coerce(int), vol.Range(min=1, max=255)),
                vol.Required(
                    CONF_EXPIRE_AFTER, default=DEFAULT_EXPIRE_AFTER
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            }
        )
        return self.async_show_form(
            step_id="add_sensor", data_schema=schema, errors=errors
        )

    async def async_step_remove_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove a configured physical sensor."""
        sensors = dict(self.config_entry.options.get(CONF_SENSORS, {}))
        if not sensors:
            return self.async_abort(reason="no_sensors")

        if user_input is not None:
            sensors.pop(user_input[CONF_SENSOR_KEY], None)
            return self.async_create_entry(
                data={**self.config_entry.options, CONF_SENSORS: sensors}
            )

        choices = {key: value[CONF_NAME] for key, value in sensors.items()}
        schema = vol.Schema({vol.Required(CONF_SENSOR_KEY): vol.In(choices)})
        return self.async_show_form(step_id="remove_sensor", data_schema=schema)
