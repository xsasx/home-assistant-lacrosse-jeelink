"""Integration tests for pylacrosse-ng through the Home Assistant beta adapter.

Exercises the real ng receiver thread, parser, registry and legacy callbacks.
Only the serial transport is faked: no Home Assistant or USB device required.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import queue
import sys
import threading
import time
import unittest
from unittest.mock import patch

from pylacrosse_ng import SerialConnectionError

ADAPTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components" / "lacrosse_jeelink" / "ng_adapter.py"
)
NAME = "lacrosse_ng_adapter_integration_under_test"
spec = importlib.util.spec_from_file_location(NAME, ADAPTER_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[NAME] = module
spec.loader.exec_module(module)


class FakeSerialTransport:
    """Simulate a pyserial connection, including errors and timeouts."""

    def __init__(self):
        self.events = queue.Queue()
        self.open_count = 0
        self.close_count = 0
        self._connected = False
        self._lock = threading.Lock()

    def open(self):
        with self._lock:
            self.open_count += 1
            self._connected = True

    def readline(self):
        try:
            value = self.events.get(timeout=0.02)
        except queue.Empty:
            return b""
        if isinstance(value, Exception):
            raise value
        return value

    def close(self):
        with self._lock:
            self.close_count += 1
            self._connected = False

    def send(self, value):
        self.events.put(value)


def await_condition(check, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.005)
    raise AssertionError("Timed out waiting for receiver event")


class TestNgAdapterFullReceivePath(unittest.TestCase):
    def setUp(self):
        self.transport = FakeSerialTransport()
        self.events = []
        patcher = patch.object(module, "SerialConnection", return_value=self.transport)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.adapter = module.LaCrosseNgAdapter("/dev/never-open", 57600)
        self.adapter.register_all(
            lambda sensor, user_data: self.events.append(
                ("global", sensor.sensorid, sensor.temperature, sensor.humidity)
            )
        )
        self.adapter.register_callback(
            5,
            lambda sensor, user_data: self.events.append(
                ("configured", sensor.sensorid, sensor.temperature, sensor.raw_flags)
            ),
        )
        self.adapter.open()
        self.adapter.start_scan()
        self.addCleanup(self.adapter.close)
        await_condition(lambda: self.adapter.health.status == "connected")

    def test_real_freezer_telegram_reaches_both_callbacks(self):
        self.transport.send(b"OK 9 5 1 3 21 106\n")
        await_condition(lambda: len(self.events) == 2)
        self.assertIn(("global", 5, -21.1, 106), self.events)
        self.assertIn(("configured", 5, -21.1, 1), self.events)
        self.assertEqual(self.adapter.sensors[5].raw_telegram, "OK 9 5 1 3 21 106")
        self.assertEqual(self.adapter.sensor_registry.discoveries()[0].radio_id, 5)
        self.assertEqual(self.adapter.reception_statistics.valid_packets, 1)

    def test_multiple_sensors_update_registry_and_sensor_cache(self):
        self.transport.send(b"OK 9 10 1 4 176 38\n")
        self.transport.send(b"OK 9 60 1 4 199 36\n")
        await_condition(lambda: len(self.events) == 2)
        self.assertEqual(set(self.adapter.sensors), {10, 60})
        self.assertEqual(
            [sensor.radio_id for sensor in self.adapter.sensor_registry.discoveries()],
            [10, 60],
        )
        self.assertEqual(self.adapter.reception_statistics.valid_packets, 2)
        self.assertEqual(self.transport.open_count, 1)

    def test_bad_packet_is_ignored_without_discovery(self):
        self.transport.send(b"NOT A JEELINK TELEGRAM\n")
        await_condition(lambda: self.adapter.reception_statistics.invalid_packets == 1)
        self.assertEqual(self.adapter.sensors, {})
        self.assertEqual(self.adapter.sensor_registry.discoveries(), ())
        self.assertEqual(self.events, [])

    def test_serial_error_recovers_without_losing_sensor_data(self):
        self.transport.send(b"OK 9 5 1 3 21 106\n")
        await_condition(lambda: len(self.events) == 2)
        self.transport.send(SerialConnectionError("simulated unplug"))
        await_condition(lambda: self.transport.open_count >= 2, timeout=3.0)
        await_condition(lambda: self.adapter.health.status == "connected")
        self.transport.send(b"OK 9 5 1 3 21 106\n")
        await_condition(lambda: len(self.events) == 4)
        self.assertEqual(self.adapter.reception_statistics.valid_packets, 2)
        self.assertEqual(self.adapter.sensor_registry.discoveries()[0].packets, 2)
        self.assertEqual(self.adapter.health.successful_connections, 2)


if __name__ == "__main__":
    unittest.main()
