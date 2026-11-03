
"""Shared JeeLink receiver with optional raw telegram diagnostics.

Based on the receive flow of pylacrosse 0.4.

Preserves the original pylacrosse callbacks and sensor cache while
retaining raw telegram metadata for future multi-channel sensors.
"""

from __future__ import annotations

import logging

import pylacrosse

_LOGGER = logging.getLogger(__name__)


class LaCrosseReceiver(pylacrosse.LaCrosse):
    """LaCrosse receiver with raw packet metadata support."""

    def __init__(
        self,
        device: str,
        baud: int,
        *,
        raw_diagnostics: bool = False,
    ) -> None:
        super().__init__(device, baud)
        self.raw_diagnostics = raw_diagnostics

    def _refresh(self) -> None:
        """Receive and decode JeeLink telegrams."""

        sensor_class = pylacrosse.LaCrosseSensor

        while not self._stopevent.isSet():
            line = self._serial.readline()

            if isinstance(line, bytes):
                line = line.decode("utf-8")
            elif not isinstance(line, str):
                continue

            if not line.strip():
                continue

            matched = sensor_class.re_reading.match(line)

            if self.raw_diagnostics and _LOGGER.isEnabledFor(
                logging.DEBUG
            ):
                if matched:
                    _LOGGER.debug(
                        "JeeLink raw telegram: %r",
                        line.strip(),
                    )
                else:
                    _LOGGER.debug(
                        "JeeLink unrecognized telegram: %r",
                        line.strip(),
                    )

            if not matched:
                continue

            sensor = sensor_class(line)

            # Preserve the original raw telegram for channel-aware
            # processing. Existing pylacrosse properties remain intact.
            sensor.raw_telegram = line.strip()

            # The third numeric field in "OK 9 ID FLAGS ..."
            # is retained without assigning a sensor type yet.
            fields = line.split()

            if len(fields) >= 4:
                try:
                    sensor.raw_flags = int(fields[3])
                except ValueError:
                    sensor.raw_flags = None
            else:
                sensor.raw_flags = None

            # Preserve pylacrosse's sensor cache.
            self.sensors[sensor.sensorid] = sensor

            # Preserve the global discovery callback.
            if self._callback:
                self._callback(
                    sensor,
                    self._callback_data,
                )

            # Preserve sensor-specific callbacks.
            if sensor.sensorid in self._registry:
                for registered_callback, user_data in self._registry[
                    sensor.sensorid
                ]:
                    registered_callback(sensor, user_data)
