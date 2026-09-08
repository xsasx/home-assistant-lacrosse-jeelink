"""Shared device data for LaCrosse Jeelink sensors."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util


class LaCrosseDeviceData:
    """State for one physical LaCrosse radio sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        lacrosse: Any,
        radio_id: int,
        expire_after: int,
    ) -> None:
        self.hass = hass
        self.lacrosse = lacrosse
        self.radio_id = radio_id
        self.expire_after = expire_after

        self.temperature: float | None = None
        self.humidity: int | None = None
        self.low_battery: bool | None = None
        self.new_battery: bool | None = None
        self.available = False

        self._expiration_cancel: Callable[[], None] | None = None
        self._listeners: list[Callable[[], None]] = []

        lacrosse.register_callback(radio_id, self._radio_callback, None)

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Register an entity update listener."""
        self._listeners.append(listener)

    def _radio_callback(self, lacrosse_sensor: Any, _user_data: Any) -> None:
        """Receive data from pylacrosse's reader thread."""
        temperature = lacrosse_sensor.temperature
        humidity = lacrosse_sensor.humidity
        low_battery = lacrosse_sensor.low_battery
        new_battery = lacrosse_sensor.new_battery

        self.hass.loop.call_soon_threadsafe(
            self._handle_packet,
            temperature,
            humidity,
            low_battery,
            new_battery,
        )

    @callback
    def _handle_packet(
        self,
        temperature: float | None,
        humidity: int | None,
        low_battery: bool | None,
        new_battery: bool | None,
    ) -> None:
        """Handle a packet in Home Assistant's event loop."""
        self.temperature = temperature
        self.humidity = humidity
        self.low_battery = low_battery
        self.new_battery = new_battery
        self.available = True

        if self._expiration_cancel is not None:
            self._expiration_cancel()
            self._expiration_cancel = None

        if self.expire_after > 0:
            expiration_at = dt_util.utcnow() + timedelta(seconds=self.expire_after)
            self._expiration_cancel = async_track_point_in_utc_time(
                self.hass, self._mark_expired, expiration_at
            )

        self._notify_listeners()

    @callback
    def _mark_expired(self, _now: datetime) -> None:
        """Mark the sensor unavailable after the configured timeout."""
        self._expiration_cancel = None
        self.available = False
        self._notify_listeners()

    @callback
    def _notify_listeners(self) -> None:
        """Notify all entities for this physical sensor."""
        for listener in self._listeners:
            listener()
