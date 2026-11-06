"""Startup readiness regression tests for the pylacrosse-ng HA beta adapter.

These tests exercise the adapter's synchronous readiness contract without
accessing a serial device or importing Home Assistant.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ADAPTER_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components" / "lacrosse_jeelink" / "ng_adapter.py"
)
MODULE_NAME = "lacrosse_ng_adapter_readiness_under_test"
spec = importlib.util.spec_from_file_location(MODULE_NAME, ADAPTER_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = module
spec.loader.exec_module(module)


class TestNgAdapterReadiness(unittest.TestCase):
    def setUp(self) -> None:
        self.serial_patch = patch.object(module, "SerialConnection")
        self.receiver_patch = patch.object(module, "NgReceiver")
        self.serial_patch.start()
        self.receiver_constructor = self.receiver_patch.start()
        self.addCleanup(self.serial_patch.stop)
        self.addCleanup(self.receiver_patch.stop)
        self.receiver = self.receiver_constructor.return_value
        self.adapter = module.LaCrosseNgAdapter("/dev/test", 57600)

    def test_connected_receiver_is_ready(self) -> None:
        self.receiver.is_connected = True
        self.adapter.wait_until_connected(timeout=0.1)

    def test_connection_becomes_ready_after_worker_starts(self) -> None:
        type(self.receiver).is_connected = property(
            lambda instance: next(states)
        )
        states = iter([False, False, True])
        self.receiver.is_running = True
        self.adapter.wait_until_connected(timeout=0.5)

    def test_worker_stops_before_connection(self) -> None:
        self.receiver.is_connected = False
        self.receiver.is_running = False
        with self.assertRaisesRegex(ConnectionError, "worker stopped"):
            self.adapter.wait_until_connected(timeout=0.1)

    def test_missing_usb_device_times_out_with_receiver_error(self) -> None:
        self.receiver.is_connected = False
        self.receiver.is_running = True
        self.receiver.health.last_error = "device not found"
        with self.assertRaisesRegex(ConnectionError, "device not found"):
            self.adapter.wait_until_connected(timeout=0.08)

    def test_never_connected_without_error_reports_timeout(self) -> None:
        self.receiver.is_connected = False
        self.receiver.is_running = True
        self.receiver.health.last_error = None
        with self.assertRaisesRegex(ConnectionError, "connection not established"):
            self.adapter.wait_until_connected(timeout=0.08)

    def test_nonpositive_timeout_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "timeout must be positive"):
            self.adapter.wait_until_connected(timeout=0)


if __name__ == "__main__":
    unittest.main()
