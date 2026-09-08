"""Sensor platform for LaCrosse Jeelink."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
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
    """Set up temperature and humidity entities."""

    sensors_config = entry.options.get(CONF_SENSORS, {})
    entities: list[SensorEntity] = []

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

        name = sensor_config["name"]
        entities.extend(
            [
                LaCrosseTemperature(data, entry.entry_id, sensor_key, name),
                LaCrosseHumidity(data, entry.entry_id, sensor_key, name),
            ]
        )

    async_add_entities(entities)


class LaCrosseTemperature(LaCrosseEntity, SensorEntity):
    """LaCrosse temperature sensor."""

    _attr_translation_key = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, data, entry_id: str, sensor_key: str, device_name: str) -> None:
        super().__init__(data, entry_id, sensor_key, device_name, "temperature")

    @property
    def native_value(self) -> float | None:
        """Return temperature."""
        return self.data.temperature


class LaCrosseHumidity(LaCrosseEntity, SensorEntity):
    """LaCrosse humidity sensor."""

    _attr_translation_key = "humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, data, entry_id: str, sensor_key: str, device_name: str) -> None:
        super().__init__(data, entry_id, sensor_key, device_name, "humidity")

    @property
    def native_value(self) -> int | None:
        """Return humidity."""
        return self.data.humidity
