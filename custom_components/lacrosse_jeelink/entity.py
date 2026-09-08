"""Base entity for LaCrosse Jeelink."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .device import LaCrosseDeviceData


class LaCrosseEntity(Entity):
    """Base entity belonging to one physical LaCrosse sensor."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        data: LaCrosseDeviceData,
        entry_id: str,
        sensor_key: str,
        device_name: str,
        entity_suffix: str,
    ) -> None:
        self.data = data
        self._attr_unique_id = f"{entry_id}_{sensor_key}_{entity_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}:{sensor_key}")},
            name=device_name,
            manufacturer="LaCrosse / Technoline",
            model="Jeelink LaCrosse sensor",
            via_device=(DOMAIN, entry_id),
        )

    @property
    def available(self) -> bool:
        """Return whether the physical sensor is currently available."""
        return self.data.available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose useful radio metadata."""
        return {
            "radio_id": self.data.radio_id,
            "new_battery": self.data.new_battery,
        }

    async def async_added_to_hass(self) -> None:
        """Register state update callback."""
        self.data.add_listener(self.async_write_ha_state)
