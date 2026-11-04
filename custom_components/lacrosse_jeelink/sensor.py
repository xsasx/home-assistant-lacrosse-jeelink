
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
from .const import (
    CONF_EXPIRE_AFTER,
    CONF_HAS_HUMIDITY,
    CONF_RADIO_ID,
    CONF_SENSORS,
    DEFAULT_EXPIRE_AFTER,
)
from .device import LaCrosseDeviceData
from .entity import LaCrosseEntity


CONF_MULTI_CHANNEL = "multi_channel"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LaCrosseConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up temperature and humidity entities."""

    sensors_config = entry.options.get(CONF_SENSORS, {})
    entities: list[SensorEntity] = []

    device_data = hass.data.setdefault(
        "lacrosse_jeelink_device_data",
        {},
    ).setdefault(
        entry.entry_id,
        {},
    )

    for sensor_key, sensor_config in sensors_config.items():
        data = device_data.get(sensor_key)

        multi_channel = (
            sensor_config.get(CONF_MULTI_CHANNEL, False) is True
        )

        if data is None:
            data = LaCrosseDeviceData(
                hass=hass,
                lacrosse=entry.runtime_data.lacrosse,
                radio_id=int(sensor_config[CONF_RADIO_ID]),
                expire_after=int(
                    sensor_config.get(
                        CONF_EXPIRE_AFTER,
                        DEFAULT_EXPIRE_AFTER,
                    )
                ),
                multi_channel=multi_channel,
            )
            device_data[sensor_key] = data

        name = sensor_config["name"]

        # Preserve the existing temperature entity and unique ID.
        entities.append(
            LaCrosseTemperature(
                data,
                entry.entry_id,
                sensor_key,
                name,
            )
        )

        if multi_channel:
            entities.append(
                LaCrosseExternalTemperature(
                    data,
                    entry.entry_id,
                    sensor_key,
                    name,
                )
            )

        # Existing configurations created before has_humidity was
        # introduced default to True for backwards compatibility.
        #
        # TX25TP-IT packets do not contain valid humidity readings
        # in the observed protocol format.
        if (
            not multi_channel
            and sensor_config.get(CONF_HAS_HUMIDITY, True)
        ):
            entities.append(
                LaCrosseHumidity(
                    data,
                    entry.entry_id,
                    sensor_key,
                    name,
                )
            )

    async_add_entities(entities)


class LaCrosseTemperature(LaCrosseEntity, SensorEntity):
    """LaCrosse temperature sensor."""

    _attr_translation_key = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        data,
        entry_id: str,
        sensor_key: str,
        device_name: str,
    ) -> None:
        super().__init__(
            data,
            entry_id,
            sensor_key,
            device_name,
            "temperature",
        )

    @property
    def native_value(self) -> float | None:
        """Return primary temperature."""
        return self.data.temperature


class LaCrosseExternalTemperature(LaCrosseEntity, SensorEntity):
    """External temperature of a dual-channel LaCrosse sensor."""

    _attr_translation_key = "temperature_external"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        data,
        entry_id: str,
        sensor_key: str,
        device_name: str,
    ) -> None:
        super().__init__(
            data,
            entry_id,
            sensor_key,
            device_name,
            "temperature_external",
        )

    @property
    def available(self) -> bool:
        """Return whether external temperature is available."""
        return self.data.external_available

    @property
    def native_value(self) -> float | None:
        """Return external temperature."""
        return self.data.temperature_external


class LaCrosseHumidity(LaCrosseEntity, SensorEntity):
    """LaCrosse humidity sensor."""

    _attr_translation_key = "humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        data,
        entry_id: str,
        sensor_key: str,
        device_name: str,
    ) -> None:
        super().__init__(
            data,
            entry_id,
            sensor_key,
            device_name,
            "humidity",
        )

    @property
    def available(self) -> bool:
        """Return whether valid humidity data is available."""
        return self.data.humidity_available

    @property
    def native_value(self) -> int | None:
        """Return the last valid humidity reading."""
        return self.data.humidity
