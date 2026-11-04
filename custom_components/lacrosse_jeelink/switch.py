"""Per-device configuration controls for LaCrosse sensors."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory

from .const import CONF_HAS_HUMIDITY, CONF_SENSORS
from .entity import LaCrosseEntity

CONF_HUMIDITY_MODE = "humidity_mode"
HUMIDITY_MODE_MANUAL = "manual"
CONF_MULTI_CHANNEL = "multi_channel"


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Expose humidity support on each physical sensor device."""
    device_data = hass.data.get("lacrosse_jeelink_device_data", {}).get(
        entry.entry_id, {}
    )
    entities = []
    for sensor_key, config in entry.options.get(CONF_SENSORS, {}).items():
        data = device_data.get(sensor_key)
        if data is not None:
            entities.append(
                LaCrosseHumidityEnabled(
                    data, entry, sensor_key, config["name"]
                )
            )
    async_add_entities(entities)


class LaCrosseHumidityEnabled(LaCrosseEntity, SwitchEntity):
    """Configure humidity capability on a specific physical sensor."""

    _attr_name = "Humidity measurement"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, data, entry, sensor_key: str, device_name: str) -> None:
        super().__init__(
            data, entry.entry_id, sensor_key, device_name, "humidity_enabled"
        )
        self._entry = entry
        self._sensor_key = sensor_key

    @property
    def is_on(self) -> bool:
        """Return whether humidity is enabled in the saved configuration."""
        config = self._entry.options.get(CONF_SENSORS, {}).get(
            self._sensor_key, {}
        )
        return (
            not config.get(CONF_MULTI_CHANNEL, False)
            and config.get(CONF_HAS_HUMIDITY, True) is True
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Enable humidity and reload the integration."""
        await self._set_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable humidity and reload the integration."""
        await self._set_enabled(False)

    async def _set_enabled(self, enabled: bool) -> None:
        sensors = dict(self._entry.options.get(CONF_SENSORS, {}))
        sensor = sensors.get(self._sensor_key)
        if sensor is None:
            return
        if enabled and sensor.get(CONF_MULTI_CHANNEL, False):
            # Dual-temperature devices do not report humidity.
            return
        updated = dict(sensor)
        updated[CONF_HAS_HUMIDITY] = enabled
        updated[CONF_HUMIDITY_MODE] = HUMIDITY_MODE_MANUAL
        sensors[self._sensor_key] = updated
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, CONF_SENSORS: sensors},
        )
        await self.hass.config_entries.async_reload(self._entry.entry_id)
