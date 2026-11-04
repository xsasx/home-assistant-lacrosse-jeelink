
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
        *,
        multi_channel: bool = False,
    ) -> None:
        self.hass = hass
        self.lacrosse = lacrosse
        self.radio_id = radio_id
        self.expire_after = expire_after
        self.multi_channel = multi_channel

        # Primary sensor state.
        self.temperature: float | None = None
        self.humidity: int | None = None
        self.low_battery: bool | None = None
        self.new_battery: bool | None = None
        self.available = False

        # Dual-temperature sensor state.
        self.temperature_external: float | None = None
        self.external_available = False
        self.raw_flags: int | None = None

        # Independent humidity availability.
        self.humidity_available = False

        self._expiration_cancel: Callable[[], None] | None = None
        self._external_expiration_cancel: Callable[[], None] | None = None
        self._humidity_expiration_cancel: Callable[[], None] | None = None

        self._listeners: list[Callable[[], None]] = []
        self._shutdown = False

        lacrosse.register_callback(
            radio_id,
            self._radio_callback,
            None,
        )

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Register an entity update listener."""
        if not self._shutdown and listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        """Unregister an entity update listener."""
        try:
            self._listeners.remove(listener)
        except ValueError:
            pass

    @callback
    def async_shutdown(self) -> None:
        """Cancel expiration timers and release entity listeners."""
        if self._shutdown:
            return

        self._shutdown = True

        for cancel_attribute in (
            "_expiration_cancel",
            "_external_expiration_cancel",
            "_humidity_expiration_cancel",
        ):
            cancel = getattr(self, cancel_attribute)
            if cancel is not None:
                cancel()
                setattr(self, cancel_attribute, None)

        self._listeners.clear()

    def _radio_callback(
        self,
        lacrosse_sensor: Any,
        _user_data: Any,
    ) -> None:
        """Receive data from pylacrosse's reader thread."""
        if self._shutdown:
            return

        temperature = lacrosse_sensor.temperature
        humidity = lacrosse_sensor.humidity
        low_battery = lacrosse_sensor.low_battery
        new_battery = lacrosse_sensor.new_battery
        raw_flags = getattr(
            lacrosse_sensor,
            "raw_flags",
            None,
        )

        self.hass.loop.call_soon_threadsafe(
            self._handle_packet,
            temperature,
            humidity,
            low_battery,
            new_battery,
            raw_flags,
        )

    @callback
    def _handle_packet(
        self,
        temperature: float | None,
        humidity: int | None,
        low_battery: bool | None,
        new_battery: bool | None,
        raw_flags: int | None = None,
    ) -> None:
        """Handle a packet in Home Assistant's event loop."""
        if self._shutdown:
            return

        self.raw_flags = raw_flags

        if self.multi_channel:
            # TX25TP-IT: external temperature packet.
            if raw_flags == 130:
                self.temperature_external = temperature
                self.external_available = True
                self._schedule_external_expiration()
                self._notify_listeners()
                return

            # TX25TP-IT: internal temperature packet.
            if raw_flags != 1:
                return

            # Dual-temperature packets do not contain humidity.
            humidity = None

        self.temperature = temperature
        self.low_battery = low_battery
        self.new_battery = new_battery
        self.available = True

        # Only valid humidity readings update the humidity state.
        # Invalid values must never reset its expiration timer.
        if (
            not self.multi_channel
            and humidity is not None
            and 0 <= humidity <= 100
        ):
            self.humidity = humidity
            self.humidity_available = True
            self._schedule_humidity_expiration()

        self._schedule_expiration()
        self._notify_listeners()

    @callback
    def _schedule_expiration(self) -> None:
        """Schedule expiration of the primary temperature."""
        if self._expiration_cancel is not None:
            self._expiration_cancel()
            self._expiration_cancel = None

        if self.expire_after > 0:
            expiration_at = (
                dt_util.utcnow()
                + timedelta(seconds=self.expire_after)
            )
            self._expiration_cancel = async_track_point_in_utc_time(
                self.hass,
                self._mark_expired,
                expiration_at,
            )

    @callback
    def _schedule_external_expiration(self) -> None:
        """Schedule expiration of the external temperature."""
        if self._external_expiration_cancel is not None:
            self._external_expiration_cancel()
            self._external_expiration_cancel = None

        if self.expire_after > 0:
            expiration_at = (
                dt_util.utcnow()
                + timedelta(seconds=self.expire_after)
            )
            self._external_expiration_cancel = (
                async_track_point_in_utc_time(
                    self.hass,
                    self._mark_external_expired,
                    expiration_at,
                )
            )

    @callback
    def _schedule_humidity_expiration(self) -> None:
        """Schedule expiration after the last valid humidity packet."""
        if self._humidity_expiration_cancel is not None:
            self._humidity_expiration_cancel()
            self._humidity_expiration_cancel = None

        if self.expire_after > 0:
            expiration_at = (
                dt_util.utcnow()
                + timedelta(seconds=self.expire_after)
            )
            self._humidity_expiration_cancel = (
                async_track_point_in_utc_time(
                    self.hass,
                    self._mark_humidity_expired,
                    expiration_at,
                )
            )

    @callback
    def _mark_expired(self, _now: datetime) -> None:
        """Mark the primary sensor unavailable."""
        self._expiration_cancel = None

        if self._shutdown:
            return

        self.available = False
        self._notify_listeners()

    @callback
    def _mark_external_expired(self, _now: datetime) -> None:
        """Mark the external temperature unavailable."""
        self._external_expiration_cancel = None

        if self._shutdown:
            return

        self.external_available = False
        self._notify_listeners()

    @callback
    def _mark_humidity_expired(self, _now: datetime) -> None:
        """Mark humidity unavailable without removing its entity."""
        self._humidity_expiration_cancel = None

        if self._shutdown:
            return

        self.humidity_available = False
        self._notify_listeners()

    @callback
    def _notify_listeners(self) -> None:
        """Notify all entities for this physical sensor."""
        if self._shutdown:
            return

        for listener in self._listeners:
            listener()
