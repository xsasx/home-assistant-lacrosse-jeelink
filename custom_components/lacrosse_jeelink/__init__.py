
"""LaCrosse Jeelink integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import (
    CONF_BAUD,
    CONF_HAS_HUMIDITY,
    CONF_RADIO_ID,
    CONF_SENSORS,
    DEFAULT_BAUD,
    DOMAIN,
    PLATFORMS,
)
from .ng_adapter import LaCrosseNgAdapter

_LOGGER = logging.getLogger(__name__)

CONF_HUMIDITY_MODE = "humidity_mode"
HUMIDITY_MODE_MANUAL = "manual"
CONF_MULTI_CHANNEL = "multi_channel"
CONF_RAW_TELEGRAM_DIAGNOSTICS = "raw_telegram_diagnostics"


@dataclass
class LaCrosseRuntimeData:
    """Runtime data for a LaCrosse Jeelink config entry."""

    lacrosse: LaCrosseNgAdapter

    # Includes configured and unconfigured radio sensors.
    discovered_sensors: dict[int, dict[str, Any]] = field(
        default_factory=dict
    )


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

    raw_diagnostics_enabled = (
        entry.options.get(
            CONF_RAW_TELEGRAM_DIAGNOSTICS,
            False,
        )
        is True
    )

    lacrosse = LaCrosseNgAdapter(
        device,
        baud,
        raw_diagnostics=raw_diagnostics_enabled,
    )

    if raw_diagnostics_enabled:
        _LOGGER.warning(
            "LaCrosse Jeelink raw telegram diagnostics enabled "
            "for %s. Raw serial data will be logged at DEBUG level.",
            device,
        )
    else:
        _LOGGER.debug(
            "LaCrosse Jeelink beta using pylacrosse-ng adapter"
        )

    discovered_sensors: dict[int, dict[str, Any]] = {}

    humidity_restorations_in_progress: set[str] = set()

    async def restore_humidity_sensor(sensor_key: str) -> None:
        """Restore humidity for a legacy sensor when valid data arrives."""
        try:
            sensors = dict(entry.options.get(CONF_SENSORS, {}))
            sensor_config = sensors.get(sensor_key)

            if sensor_config is None:
                return

            # Dual-temperature sensors do not expose humidity.
            if sensor_config.get(CONF_MULTI_CHANNEL, False):
                return

            # Never override an explicit user choice.
            if (
                sensor_config.get(CONF_HUMIDITY_MODE)
                == HUMIDITY_MODE_MANUAL
            ):
                return

            if sensor_config.get(CONF_HAS_HUMIDITY) is not False:
                return

            updated_sensor_config = dict(sensor_config)
            updated_sensor_config[CONF_HAS_HUMIDITY] = True
            sensors[sensor_key] = updated_sensor_config

            new_options = {
                **entry.options,
                CONF_SENSORS: sensors,
            }

            _LOGGER.info(
                "Restoring humidity support for legacy LaCrosse "
                "sensor %s after receiving valid humidity",
                sensor_key,
            )

            hass.config_entries.async_update_entry(
                entry,
                options=new_options,
            )

            await hass.config_entries.async_reload(entry.entry_id)

        finally:
            humidity_restorations_in_progress.discard(sensor_key)

    def check_existing_sensor_capabilities(
        sensor_id: int,
        humidity: int,
    ) -> None:
        """Restore legacy humidity support when valid data is received."""
        if not _has_valid_humidity(humidity):
            return

        configured_sensors = entry.options.get(CONF_SENSORS, {})

        for sensor_key, sensor_config in configured_sensors.items():
            if int(sensor_config[CONF_RADIO_ID]) != sensor_id:
                continue

            # Dual-temperature sensors never gain a humidity entity.
            if sensor_config.get(CONF_MULTI_CHANNEL, False):
                return

            # A manually configured capability is authoritative.
            if (
                sensor_config.get(CONF_HUMIDITY_MODE)
                == HUMIDITY_MODE_MANUAL
            ):
                return

            if sensor_config.get(CONF_HAS_HUMIDITY) is not False:
                return

            if sensor_key in humidity_restorations_in_progress:
                return

            humidity_restorations_in_progress.add(sensor_key)

            hass.async_create_task(
                restore_humidity_sensor(sensor_key)
            )
            return

    def update_discovered_sensor(
        sensor_id: int,
        temperature: float,
        humidity: int,
        low_battery: bool,
        new_battery: bool,
        raw_flags: int | None,
    ) -> None:
        """Update discovery and retain genuine new-battery events."""
        now = datetime.now(timezone.utc)
        previous = discovered_sensors.get(sensor_id)

        # On the TX25TP-IT, flag 130 identifies the external probe.
        # Its high bit must not count as a new-battery event, including
        # when the radio ID has not yet been configured.
        external_temperature_packet = raw_flags == 130
        genuine_new_battery = new_battery and not external_temperature_packet

        # Normal packets must not erase a genuine new-battery event.
        last_new_battery_seen = (
            now
            if genuine_new_battery
            else (
                previous.get("last_new_battery_seen")
                if previous is not None
                else None
            )
        )

        discovered_sensors[sensor_id] = {
            "radio_id": sensor_id,
            "temperature": temperature,
            "humidity": humidity,
            "low_battery": low_battery,
            "new_battery": genuine_new_battery,
            "last_seen": now,
            "last_new_battery_seen": last_new_battery_seen,
        }

        _LOGGER.debug(
            "LaCrosse sensor discovered: ID %s, temperature %.1f °C, "
            "humidity %s %%, low battery %s, new battery %s, raw flags %s",
            sensor_id,
            temperature,
            humidity,
            low_battery,
            genuine_new_battery,
            raw_flags,
        )

        # The external probe's last byte is not a humidity reading.
        if not external_temperature_packet:
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
            getattr(sensor, "raw_flags", None),
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

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

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
        # Stop all device timers and release listeners before
        # removing the shared device cache.
        all_device_data = hass.data.get(
            "lacrosse_jeelink_device_data",
            {},
        )
        entry_device_data = all_device_data.pop(
            entry.entry_id,
            {},
        )

        for data in entry_device_data.values():
            data.async_shutdown()

        try:
            await hass.async_add_executor_job(
                entry.runtime_data.lacrosse.close
            )
        except Exception:
            _LOGGER.exception(
                "Error while closing LaCrosse Jeelink"
            )

    return unload_ok
