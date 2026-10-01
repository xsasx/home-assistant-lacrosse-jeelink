"""Config flow for LaCrosse Jeelink"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_DEVICE
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
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


class LaCrosseJeelinkConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for LaCrosse Jeelink."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
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
                data={
                    CONF_DEVICE: device,
                    CONF_BAUD: baud,
                },
                options={
                    CONF_SENSORS: {},
                },
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE,
                    default=DEFAULT_DEVICE,
                ): str,
                vol.Required(
                    CONF_BAUD,
                    default=DEFAULT_BAUD,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1),
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Change serial connection settings."""

        entry = self._get_reconfigure_entry()

        if user_input is not None:
            device = user_input[CONF_DEVICE].strip()
            baud = int(user_input[CONF_BAUD])

            for other_entry in self._async_current_entries():
                if (
                    other_entry.entry_id != entry.entry_id
                    and other_entry.data.get(CONF_DEVICE) == device
                ):
                    return self.async_abort(
                        reason="already_configured"
                    )

            return self.async_update_reload_and_abort(
                entry,
                data_updates={
                    CONF_DEVICE: device,
                    CONF_BAUD: baud,
                },
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE,
                    default=entry.data[CONF_DEVICE],
                ): str,
                vol.Required(
                    CONF_BAUD,
                    default=entry.data.get(
                        CONF_BAUD,
                        DEFAULT_BAUD,
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1),
                ),
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> LaCrosseJeelinkOptionsFlow:
        """Return the options flow."""

        return LaCrosseJeelinkOptionsFlow()


class LaCrosseJeelinkOptionsFlow(OptionsFlowWithReload):
    """Manage LaCrosse radio sensors."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._discovered_radio_id: int | None = None

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show the sensor management menu."""

        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "add_sensor",
                "scan_sensor",
                "remove_sensor",
            ],
        )

    async def async_step_add_sensor(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Add a physical LaCrosse sensor manually."""

        errors: dict[str, str] = {}

        sensors = dict(
            self.config_entry.options.get(
                CONF_SENSORS,
                {},
            )
        )

        if user_input is not None:
            name = user_input[CONF_SENSOR_NAME].strip()
            radio_id = int(user_input[CONF_RADIO_ID])
            expire_after = int(user_input[CONF_EXPIRE_AFTER])

            sensor_key = slugify(name)

            if not sensor_key:
                errors[CONF_SENSOR_NAME] = "invalid_name"

            elif sensor_key in sensors:
                errors[CONF_SENSOR_NAME] = "name_exists"

            elif any(
                int(item[CONF_RADIO_ID]) == radio_id
                for item in sensors.values()
            ):
                errors[CONF_RADIO_ID] = "radio_id_exists"

            else:
                sensors[sensor_key] = {
                    "name": name,
                    CONF_RADIO_ID: radio_id,
                    CONF_EXPIRE_AFTER: expire_after,
                }

                return self.async_create_entry(
                    data={
                        **self.config_entry.options,
                        CONF_SENSORS: sensors,
                    }
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_SENSOR_NAME): str,
                vol.Required(CONF_RADIO_ID): NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=255,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_EXPIRE_AFTER,
                    default=DEFAULT_EXPIRE_AFTER,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1),
                ),
            }
        )

        return self.async_show_form(
            step_id="add_sensor",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_scan_sensor(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Show all sensors currently detected by Jeelink."""

        discovered = self.config_entry.runtime_data.discovered_sensors

        if not discovered:
            return self.async_abort(
                reason="no_discovered_sensors"
            )

        configured_sensors = self.config_entry.options.get(
            CONF_SENSORS,
            {},
        )

        configured_ids = {
            int(sensor[CONF_RADIO_ID])
            for sensor in configured_sensors.values()
        }

        choices: dict[str, str] = {}

        for radio_id in sorted(discovered):
            sensor = discovered[radio_id]

            temperature = sensor["temperature"]
            humidity = sensor["humidity"]
            low_battery = sensor["low_battery"]

            battery_text = "LOW" if low_battery else "OK"

            if radio_id in configured_ids:
                configured_name = next(
                    (
                        item["name"]
                        for item in configured_sensors.values()
                        if int(item[CONF_RADIO_ID]) == radio_id
                    ),
                    "configured",
                )

                label = (
                    f"ID {radio_id} — "
                    f"{temperature:.1f} °C / "
                    f"{humidity} % — "
                    f"Battery {battery_text} — "
                    f"{configured_name}"
                )
            else:
                label = (
                    f"ID {radio_id} — "
                    f"{temperature:.1f} °C / "
                    f"{humidity} % — "
                    f"Battery {battery_text} — NEW"
                )

            choices[str(radio_id)] = label

        if user_input is not None:
            radio_id = int(user_input["discovered_sensor"])

            if radio_id in configured_ids:
                return self.async_abort(
                    reason="sensor_already_configured"
                )

            self._discovered_radio_id = radio_id
            return await self.async_step_add_discovered_sensor()

        schema = vol.Schema(
            {
                vol.Required(
                    "discovered_sensor"
                ): vol.In(choices)
            }
        )

        return self.async_show_form(
            step_id="scan_sensor",
            data_schema=schema,
        )

    async def async_step_add_discovered_sensor(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Add a sensor selected from discovery."""

        if self._discovered_radio_id is None:
            return self.async_abort(
                reason="no_discovered_sensors"
            )

        errors: dict[str, str] = {}

        sensors = dict(
            self.config_entry.options.get(
                CONF_SENSORS,
                {},
            )
        )

        radio_id = self._discovered_radio_id

        if user_input is not None:
            name = user_input[CONF_SENSOR_NAME].strip()
            expire_after = int(user_input[CONF_EXPIRE_AFTER])

            sensor_key = slugify(name)

            if not sensor_key:
                errors[CONF_SENSOR_NAME] = "invalid_name"

            elif sensor_key in sensors:
                errors[CONF_SENSOR_NAME] = "name_exists"

            elif any(
                int(item[CONF_RADIO_ID]) == radio_id
                for item in sensors.values()
            ):
                errors[CONF_SENSOR_NAME] = "radio_id_exists"

            else:
                sensors[sensor_key] = {
                    "name": name,
                    CONF_RADIO_ID: radio_id,
                    CONF_EXPIRE_AFTER: expire_after,
                }

                return self.async_create_entry(
                    data={
                        **self.config_entry.options,
                        CONF_SENSORS: sensors,
                    }
                )

        discovered = (
            self.config_entry.runtime_data.discovered_sensors.get(
                radio_id,
                {},
            )
        )

        temperature = discovered.get("temperature")
        humidity = discovered.get("humidity")

        description_placeholders = {
            "radio_id": str(radio_id),
            "temperature": (
                f"{temperature:.1f}"
                if temperature is not None
                else "?"
            ),
            "humidity": (
                str(humidity)
                if humidity is not None
                else "?"
            ),
        }

        schema = vol.Schema(
            {
                vol.Required(CONF_SENSOR_NAME): str,
                vol.Required(
                    CONF_EXPIRE_AFTER,
                    default=DEFAULT_EXPIRE_AFTER,
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=1),
                ),
            }
        )

        return self.async_show_form(
            step_id="add_discovered_sensor",
            data_schema=schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_remove_sensor(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Remove a configured physical sensor."""

        sensors = dict(
            self.config_entry.options.get(
                CONF_SENSORS,
                {},
            )
        )

        if not sensors:
            return self.async_abort(
                reason="no_sensors"
            )

        if user_input is not None:
            sensor_key = user_input[CONF_SENSOR_KEY]

            # Remove the sensor from the integration configuration.
            sensors.pop(sensor_key, None)

            # Remove the corresponding Home Assistant device.
            #
            # All entities belonging to a physical LaCrosse sensor use:
            #
            #   (DOMAIN, "<entry_id>:<sensor_key>")
            #
            # as their device identifier. This lets us remove exactly
            # this sensor without touching the Jeelink hub or any other
            # configured LaCrosse sensors.
            device_registry = dr.async_get(self.hass)

            device = device_registry.async_get_device(
                identifiers={
                    (
                        DOMAIN,
                        f"{self.config_entry.entry_id}:{sensor_key}",
                    )
                }
            )

            if device is not None:
                device_registry.async_remove_device(device.id)

            return self.async_create_entry(
                data={
                    **self.config_entry.options,
                    CONF_SENSORS: sensors,
                }
            )

        choices = {
            key: value["name"]
            for key, value in sensors.items()
        }

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SENSOR_KEY
                ): vol.In(choices)
            }
        )

        return self.async_show_form(
            step_id="remove_sensor",
            data_schema=schema,
        )
