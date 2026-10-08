bash
-lc
mkdir -p /mnt/data/lacrosse_v030; cat > /mnt/data/lacrosse_v030/__init__.py <<'PY'
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
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_BAUD,
    CONF_HAS_HUMIDITY,
    CONF_RADIO_ID,
    CONF_SENSORS,
    DEFAULT_BAUD,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class LaCrosseRuntimeData:
    """Runtime data for a LaCrosse Jeelink config entry."""

    lacrosse: pylacrosse.LaCrosse

    # Includes configured and unconfigured radio sensors.
    discovered_sensors: dict[int, dict[str, Any]] = field(default_factory=dict)


LaCrosseConfigEntry = ConfigEntry[LaCrosseRuntimeData]


def _has_valid_humidity(humidity: int | None) -> bool:
    """Return whether a received humidity value is valid."""
    return humidity is not None and 0 <= humidity <= 100


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LaCrosseConfigEntry,
) -> bool:
    """Set up LaCrosse Jeelink from a config entry."""

    device = entry.data["device"]
    baud = entry.data.get(CONF_BAUD, DEFAULT_BAUD)

    lacrosse = pylacrosse.LaCrosse(device, baud)
    discovered_sensors: dict[int, dict[str, Any]] = {}

    # Prevent duplicate migration tasks while radio packets arrive.
    humidity_migrations_in_progress: set[str] = set()

    async def migrate_temperature_only_sensor(sensor_key: str) -> None:
        """Migrate an existing sensor to temperature-only."""
        try:
            sensors = dict(entry.options.get(CONF_SENSORS, {}))
            sensor_config = sensors.get(sensor_key)
            if sensor_config is None:
                return
            if sensor_config.get(CONF_HAS_HUMIDITY) is False:
                return

            updated_sensor_config = dict(sensor_config)
            updated_sensor_config[CONF_HAS_HUMIDITY] = False
            sensors[sensor_key] = updated_sensor_config

            new_options = {**entry.options, CONF_SENSORS: sensors}
            entity_registry = er.async_get(hass)
            humidity_unique_id = f"{entry.entry_id}_{sensor_key}_humidity"
            humidity_entity_id = entity_registry.async_get_entity_id(
                "sensor", DOMAIN, humidity_unique_id
            )

            if humidity_entity_id is not None:
                _LOGGER.info(
                    "Removing unsupported humidity entity %s for LaCrosse sensor %s",
                    humidity_entity_id,
                    sensor_key,
                )
                entity_registry.async_remove(humidity_entity_id)

            _LOGGER.info(
                "Detected LaCrosse sensor %s as temperature-only; "
                "disabling humidity support",
                sensor_key,
            )
            hass.config_entries.async_update_entry(entry, options=new_options)
            await hass.config_entries.async_reload(entry.entry_id)
        finally:
            humidity_migrations_in_progress.discard(sensor_key)

    def check_existing_sensor_capabilities(sensor_id: int, humidity: int) -> None:
        """Check whether an existing sensor is temperature-only."""
        if _has_valid_humidity(humidity):
            return

        configured_sensors = entry.options.get(CONF_SENSORS, {})
        for sensor_key, sensor_config in configured_sensors.items():
            if int(sensor_config[CONF_RADIO_ID]) != sensor_id:
                continue
            if sensor_config.get(CONF_HAS_HUMIDITY) is False:
                return
            if sensor_key in humidity_migrations_in_progress:
                return

            humidity_migrations_in_progress.add(sensor_key)
            hass.async_create_task(migrate_temperature_only_sensor(sensor_key))
            return

    def update_discovered_sensor(
        sensor_id: int,
        temperature: float,
        humidity: int,
        low_battery: bool,
        new_battery: bool,
    ) -> None:
        """Update discovery while retaining the last new-battery event."""
        now = datetime.now(timezone.utc)
        previous = discovered_sensors.get(sensor_id)

        # Normal radio packets must not erase a recent new-battery event.
        last_new_battery_seen = (
            now if new_battery else (
                previous.get("last_new_battery_seen")
                if previous is not None else None
            )
        )

        discovered_sensors[sensor_id] = {
            "radio_id": sensor_id,
            "temperature": temperature,
            "humidity": humidity,
            "low_battery": low_battery,
            "new_battery": new_battery,
            "last_seen": now,
            "last_new_battery_seen": last_new_battery_seen,
        }

        _LOGGER.debug(
            "LaCrosse sensor discovered: ID %s, temperature %.1f °C, "
            "humidity %s %%, low battery %s, new battery %s",
            sensor_id,
            temperature,
            humidity,
            low_battery,
            new_battery,
        )

        check_existing_sensor_capabilities(sensor_id, humidity)

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
        except Exception:  # pragma: no cover - best effort cleanup
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
        entry, PLATFORMS
    )

    if unload_ok:
        hass.data.get("lacrosse_jeelink_device_data", {}).pop(
            entry.entry_id, None
        )
        try:
            await hass.async_add_executor_job(entry.runtime_data.lacrosse.close)
        except Exception:
            _LOGGER.exception("Error while closing LaCrosse Jeelink")

    return unload_ok
PY
python -m py_compile /mnt/data/lacrosse_v030/__init__.py && echo 'Syntaxprüfung erfolgreich'; wc -l /mnt/data/lacrosse_v030/__init__.py
