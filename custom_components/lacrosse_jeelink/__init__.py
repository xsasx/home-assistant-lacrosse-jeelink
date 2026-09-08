"""LaCrosse Jeelink integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging

import pylacrosse

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

from .const import CONF_BAUD, DEFAULT_BAUD, PLATFORMS

_LOGGER = logging.getLogger(__name__)


@dataclass
class LaCrosseRuntimeData:
    """Runtime data for a LaCrosse Jeelink config entry."""

    lacrosse: pylacrosse.LaCrosse


LaCrosseConfigEntry = ConfigEntry[LaCrosseRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: LaCrosseConfigEntry) -> bool:
    """Set up LaCrosse Jeelink from a config entry."""

    device = entry.data["device"]
    baud = entry.data.get(CONF_BAUD, DEFAULT_BAUD)

    lacrosse = pylacrosse.LaCrosse(device, baud)

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

    entry.runtime_data = LaCrosseRuntimeData(lacrosse=lacrosse)

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


async def async_unload_entry(hass: HomeAssistant, entry: LaCrosseConfigEntry) -> bool:
    """Unload a LaCrosse Jeelink config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get("lacrosse_jeelink_device_data", {}).pop(entry.entry_id, None)
        try:
            await hass.async_add_executor_job(entry.runtime_data.lacrosse.close)
        except Exception:
            _LOGGER.exception("Error while closing LaCrosse Jeelink")
    return unload_ok
