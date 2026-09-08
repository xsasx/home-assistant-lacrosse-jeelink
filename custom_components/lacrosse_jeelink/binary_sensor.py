"""Binary sensor platform for LaCrosse Jeelink."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LaCrosseConfigEntry
from .const import CONF_EXPIRE_AFTER, CONF_RADIO_ID, CONF_SENSORS, DEFAULT_EXPIRE_AFTER
from .device import LaCrosseDeviceData
from .entity import LaCrosseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LaCrosseConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up low-battery entities."""

    sensors_config = entry.options.get(CONF_SENSORS, {})
    entities: list[BinarySensorEntity] = []

    device_data = hass.data.setdefault("lacrosse_jeelink_device_data", {}).setdefault(
        entry.entry_id, {}
    )

    for sensor_key, sensor_config in sensors_config.items():
        data = device_data.get(sensor_key)
        if data is None:
            data = LaCrosseDeviceData(
                hass=hass,
                lacrosse=entry.runtime_data.lacrosse,
                radio_id=int(sensor_config[CONF_RADIO_ID]),
                expire_after=int(
                    sensor_config.get(CONF_EXPIRE_AFTER, DEFAULT_EXPIRE_AFTER)
                ),
            )
            device_data[sensor_key] = data

        entities.append(
            LaCrosseLowBattery(
                data,
                entry.entry_id,
                sensor_key,
                sensor_config["name"],
            )
        )

    async_add_entities(entities)


class LaCrosseLowBattery(LaCrosseEntity, BinarySensorEntity):
    """Low battery state reported by a LaCrosse sensor."""

    _attr_translation_key = "battery_low"
    _attr_device_class = BinarySensorDeviceClass.BATTERY

    def __init__(self, data, entry_id: str, sensor_key: str, device_name: str) -> None:
        super().__init__(data, entry_id, sensor_key, device_name, "battery_low")

    @property
    def is_on(self) -> bool | None:
        """Return true when the sensor reports a low battery."""
        return self.data.low_battery
