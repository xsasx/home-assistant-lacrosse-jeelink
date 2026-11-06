"""Experimental pylacrosse-ng adapter for the Home Assistant beta branch.

This adapter is not wired into the production config entry yet. It keeps
the callback surface used by the current HA integration while delegating
serial I/O, parsing and reconnection to pylacrosse-ng.

Only one receiver may own a JeeLink serial device at a time.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
import threading
from typing import Any

from pylacrosse_ng import LaCrosseReading, SensorRegistry, SerialConnection
from pylacrosse_ng import LaCrosseReceiver as NgReceiver

_LOGGER = logging.getLogger(__name__)

SensorCallback = Callable[[Any, Any], None]


@dataclass(frozen=True, slots=True)
class LegacySensorView:
    """Expose the fields expected by existing HA device/discovery callbacks.

    The legacy discovery callback converts humidity to int unconditionally,
    so preserve the raw byte (including invalid sentinel 106). HA's existing
    capability checks decide whether that humidity value is usable.
    """

    sensorid: int
    temperature: float
    humidity: int
    low_battery: bool
    new_battery: bool
    raw_flags: int
    raw_telegram: str

    @classmethod
    def from_reading(cls, reading: LaCrosseReading) -> LegacySensorView:
        return cls(
            sensorid=reading.sensor_id,
            temperature=reading.temperature,
            humidity=reading.raw_humidity & 0x7F,
            low_battery=reading.low_battery,
            new_battery=reading.new_battery,
            raw_flags=reading.raw_flags,
            raw_telegram=reading.raw_telegram,
        )


class LaCrosseNgAdapter:
    """Bridge pylacrosse-ng's receiver into the legacy HA callback contract.

    Provides register_all(), register_callback(), open(), start_scan(),
    close() and sensors for the current HA integration. The actual serial
    connection is opened only when the background receiver starts.
    """

    def __init__(
        self,
        device: str,
        baud: int,
        *,
        raw_diagnostics: bool = False,
    ) -> None:
        self.raw_diagnostics = raw_diagnostics
        self.sensors: dict[int, LegacySensorView] = {}
        self._callback_lock = threading.RLock()
        self._all_callback: tuple[SensorCallback, Any] | None = None
        self._callbacks: dict[int, list[tuple[SensorCallback, Any]]] = {}
        self.sensor_registry = SensorRegistry()
        self._receiver = NgReceiver(
            SerialConnection(device, baudrate=baud),
            callback=self._on_reading,
            sensor_registry=self.sensor_registry,
        )

    def register_all(self, callback: SensorCallback, user_data: Any = None) -> None:
        """Register the global discovery callback."""
        with self._callback_lock:
            self._all_callback = (callback, user_data)

    def register_callback(
        self, sensor_id: int, callback: SensorCallback, user_data: Any = None
    ) -> None:
        """Register a callback for one radio ID."""
        with self._callback_lock:
            self._callbacks.setdefault(sensor_id, []).append(
                (callback, user_data)
            )

    def open(self) -> None:
        """Compatibility hook; receiver.start() opens the serial port.

        Defer the open deliberately so the new receiver retains exclusive
        ownership of open/read/reconnect/close in its worker thread.
        """
        _LOGGER.debug("pylacrosse-ng adapter prepared; port not yet opened")

    def start_scan(self) -> None:
        """Start reading packets and handling automatic reconnection."""
        self._receiver.start()

    def close(self) -> None:
        """Stop the worker and release the serial device."""
        self._receiver.stop()

    @property
    def health(self):
        """Current pylacrosse-ng receiver health snapshot."""
        return self._receiver.health

    @property
    def reception_statistics(self):
        """Current pylacrosse-ng reception statistics."""
        return self._receiver.reception_statistics

    def _on_reading(self, reading: LaCrosseReading) -> None:
        if self.raw_diagnostics and _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug("JeeLink raw telegram: %r", reading.raw_telegram)

        sensor = LegacySensorView.from_reading(reading)

        with self._callback_lock:
            self.sensors[sensor.sensorid] = sensor
            global_callback = self._all_callback
            specific_callbacks = tuple(self._callbacks.get(sensor.sensorid, ()))

        if global_callback is not None:
            callback, user_data = global_callback
            try:
                callback(sensor, user_data)
            except Exception:
                _LOGGER.exception("LaCrosse global discovery callback failed")

        for callback, user_data in specific_callbacks:
            try:
                callback(sensor, user_data)
            except Exception:
                _LOGGER.exception(
                    "LaCrosse sensor callback failed for ID %s", sensor.sensorid
                )
