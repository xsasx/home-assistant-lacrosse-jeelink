"""LaCrosse Jeelink integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any

import pylacrosse

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import CONF_BAUD, DEFAULT_BAUD, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


@dataclass
class LaCrosseRuntimeData:
    """Runtime data for a LaCrosse Jeelink config entry."""

    lacrosse: pylacrosse.LaCrosse

    # All sensors seen on the radio, including sensors which are not
    # configured in Home Assistant yet.
    discovered_sensors: dict[int, dict[str, Any]] = field(default_factory=dict)


LaCrosseConfigEntry = ConfigEntry[LaCrosseRuntimeData]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LaCrosseConfigEntry,
) -> bool:
    """Set up LaCrosse Jeelink from a config entry."""

    device = entry.data["device"]
    baud = entry.data.get(CONF_BAUD, DEFAULT_BAUD)

    lacrosse = pylacrosse.LaCrosse(device, baud)

    discovered_sensors: dict[int, dict[str, Any]] = {}

    def update_discovered_sensor(
        sensor_id: int,
        temperature: float,
        humidity: int,
        low_battery: bool,
        new_battery: bool,
    ) -> None:
        """Update a sensor in the discovery cache."""

        discovered_sensors[sensor_id] = {
            "radio_id": sensor_id,
            "temperature": temperature,
            "humidity": humidity,
            "low_battery": low_battery,
            "new_battery": new_battery,
            "last_seen": datetime.now(timezone.utc),
        }

        _LOGGER.debug(
            "LaCrosse sensor discovered: ID %s, temperature %.1f °C, "
            "humidity %s %%, low battery %s",
            sensor_id,
            temperature,
            humidity,
            low_battery,
        )

    def discovery_callback(sensor: Any, _user_data: Any) -> None:
        """Receive every LaCrosse sensor packet."""

        hass.loop.call_soon_threadsafe(
            update_discovered_sensor,
            int(sensor.sensorid),
            float(sensor.temperature),
            int(sensor.humidity),
            bool(sensor.low_battery),
            bool(sensor.new_battery),
        )

    lacrosse.register_all(discovery_callback)

    try:
        await hass.async_add_executor_job(lacrosse.open)
        await hass.async_add_executor_job(lacrosse.start_scan)
    except Exception as err:
        try:
            await hass.async_add_executor_job(lacrosse.close)
        except Exception:
            pass

        raise ConfigEntryNotReady(
            f"Unable to open LaCrosse Jeelink on {device} at {baud} baud"
        ) from err

    entry.runtime_data = LaCrosseRuntimeData(
        lacrosse=lacrosse,
        discovered_sensors=discovered_sensors,
    )

    device_registry = dr.async_get(hass)

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="LaCrosse Jeelink",
        manufacturer="Jeelink",
        model="USB radio gateway",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: LaCrosseConfigEntry,
) -> bool:
    """Unload a LaCrosse Jeelink config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        hass.data.get(
            "lacrosse_jeelink_device_data",
            {},
        ).pop(entry.entry_id, None)

        try:
            await hass.async_add_executor_job(
                entry.runtime_data.lacrosse.close
            )
        except Exception:
            _LOGGER.exception(
                "Error while closing LaCrosse Jeelink"
            )

    return unload_ok
