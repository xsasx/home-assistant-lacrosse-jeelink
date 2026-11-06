"""Regression tests for the experimental pylacrosse-ng HA compatibility adapter.

Load only the adapter module, without importing Home Assistant or touching
a serial port. CI installs pylacrosse-ng on the beta branch.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from pylacrosse_ng import parse_telegram


ADAPTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components" / "lacrosse_jeelink" / "ng_adapter.py"
)
MODULE_NAME = "lacrosse_ng_adapter_under_test"
spec = importlib.util.spec_from_file_location(MODULE_NAME, ADAPTER_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)

LaCrosseNgAdapter = module.LaCrosseNgAdapter


class TestNgAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.serial_patch = patch.object(module, "SerialConnection")
        self.receiver_patch = patch.object(module, "NgReceiver")
        self.serial = self.serial_patch.start()
        self.ng_receiver = self.receiver_patch.start()
        self.addCleanup(self.serial_patch.stop)
        self.addCleanup(self.receiver_patch.stop)
        self.instance = self.ng_receiver.return_value
        self.adapter = LaCrosseNgAdapter("/dev/test-jeelink", 57600)
        self.callback = self.ng_receiver.call_args.kwargs["callback"]

    def receive(self, telegram: str) -> None:
        reading = parse_telegram(telegram)
        self.assertIsNotNone(reading)
        self.callback(reading)

    def test_adapter_constructs_ng_receiver_without_opening_serial(self) -> None:
        self.serial.assert_called_once_with("/dev/test-jeelink", baudrate=57600)
        self.assertIs(
            self.ng_receiver.call_args.kwargs["sensor_registry"],
            self.adapter.sensor_registry,
        )
        self.instance.start.assert_not_called()
        self.adapter.open()
        self.instance.start.assert_not_called()
        self.adapter.start_scan()
        self.instance.start.assert_called_once_with()
        self.adapter.close()
        self.instance.stop.assert_called_once_with()

    def test_global_and_specific_callbacks_receive_legacy_sensor_fields(self) -> None:
        global_events = []
        specific_events = []
        self.adapter.register_all(
            lambda sensor, data: global_events.append((sensor, data)),
            "discovery",
        )
        self.adapter.register_callback(
            10,
            lambda sensor, data: specific_events.append((sensor, data)),
            "configured",
        )
        self.receive("OK 9 10 1 4 176 38")
        self.assertEqual(len(global_events), 1)
        self.assertEqual(len(specific_events), 1)
        sensor, global_data = global_events[0]
        self.assertIs(sensor, specific_events[0][0])
        self.assertEqual(global_data, "discovery")
        self.assertEqual(specific_events[0][1], "configured")
        self.assertEqual(sensor.sensorid, 10)
        self.assertAlmostEqual(sensor.temperature, 20.0)
        self.assertEqual(sensor.humidity, 38)
        self.assertEqual(sensor.raw_flags, 1)
        self.assertEqual(self.adapter.sensors[10], sensor)

    def test_freezer_raw_humidity_sentinel_is_preserved_for_legacy_callbacks(self):
        self.receive("OK 9 5 1 3 21 106")
        sensor = self.adapter.sensors[5]
        self.assertAlmostEqual(sensor.temperature, -21.1)
        self.assertEqual(sensor.humidity, 106)
        self.assertFalse(sensor.low_battery)
        self.assertFalse(sensor.new_battery)
        self.assertEqual(sensor.raw_telegram, "OK 9 5 1 3 21 106")

    def test_tx25tp_external_probe_keeps_raw_flags_not_battery_event(self):
        self.receive("OK 9 25 130 4 180 106")
        sensor = self.adapter.sensors[25]
        self.assertEqual(sensor.raw_flags, 130)
        self.assertFalse(sensor.new_battery)
        self.assertEqual(sensor.humidity, 106)
        self.assertAlmostEqual(sensor.temperature, 20.4)

    def test_callback_failure_does_not_block_other_callbacks(self) -> None:
        events = []
        def broken(_sensor, _user_data):
            raise RuntimeError("consumer error")

        self.adapter.register_all(broken)
        self.adapter.register_callback(10, broken)
        self.adapter.register_callback(
            10, lambda sensor, data: events.append((sensor.sensorid, data)), "ok"
        )
        with self.assertLogs(module._LOGGER, level="ERROR") as logs:
            self.receive("OK 9 10 1 4 176 38")
        self.assertEqual(events, [(10, "ok")])
        self.assertEqual(len(logs.output), 2)
        self.assertIn(10, self.adapter.sensors)

    def test_only_registered_sensor_receives_specific_callback(self) -> None:
        received = []
        self.adapter.register_callback(10, lambda s, _: received.append(s.sensorid))
        self.receive("OK 9 60 1 4 199 36")
        self.assertEqual(received, [])
        self.assertIn(60, self.adapter.sensors)

    def test_debug_telegram_requires_opt_in_and_debug_level(self) -> None:
        self.receive("OK 9 10 1 4 176 38")
        with patch.object(module._LOGGER, "debug") as debug:
            self.receive("OK 9 10 1 4 176 38")
            debug.assert_not_called()

        self.adapter.raw_diagnostics = True
        with patch.object(module._LOGGER, "isEnabledFor", return_value=True):
            with patch.object(module._LOGGER, "debug") as debug:
                self.receive("OK 9 10 1 4 176 38")
                debug.assert_called_once_with(
                    "JeeLink raw telegram: %r", "OK 9 10 1 4 176 38"
                )

    def test_ng_health_and_statistics_are_accessible(self) -> None:
        self.instance.health = MagicMock(status="connected")
        self.instance.reception_statistics = MagicMock(valid_packets=3)
        self.assertIs(self.adapter.health, self.instance.health)
        self.assertIs(
            self.adapter.reception_statistics, self.instance.reception_statistics
        )


if __name__ == "__main__":
    unittest.main()
