
"""Regression tests for LaCrosse device data handling."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch


DEVICE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "lacrosse_jeelink"
    / "device.py"
)


def load_device_module():
    """Load device.py with minimal Home Assistant test stubs."""
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []

    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = MagicMock
    core.callback = lambda function: function

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []

    event = types.ModuleType("homeassistant.helpers.event")
    event.async_track_point_in_utc_time = MagicMock()

    util = types.ModuleType("homeassistant.util")
    util.__path__ = []

    dt = types.ModuleType("homeassistant.util.dt")
    dt.utcnow = lambda: datetime.now(timezone.utc)

    modules = {
        "homeassistant": homeassistant,
        "homeassistant.core": core,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.event": event,
        "homeassistant.util": util,
        "homeassistant.util.dt": dt,
    }

    with patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location(
            "lacrosse_device_under_test",
            DEVICE_PATH,
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    return module


device_module = load_device_module()
LaCrosseDeviceData = device_module.LaCrosseDeviceData


class TestLaCrosseDeviceData(unittest.TestCase):
    """Test humidity validation and multi-channel processing."""

    def setUp(self):
        """Create a device without real hardware."""
        self.hass = MagicMock()
        self.lacrosse = MagicMock()

        self.expiration_callbacks = []

        def schedule(_hass, callback, _when):
            cancel = MagicMock()
            self.expiration_callbacks.append(
                (callback, cancel)
            )
            return cancel

        self.scheduler_patch = patch.object(
            device_module,
            "async_track_point_in_utc_time",
            side_effect=schedule,
        )
        self.scheduler_patch.start()
        self.addCleanup(self.scheduler_patch.stop)

        self.data = LaCrosseDeviceData(
            hass=self.hass,
            lacrosse=self.lacrosse,
            radio_id=60,
            expire_after=300,
        )

    def packet(
        self,
        humidity,
        temperature=21.5,
        raw_flags=1,
    ):
        """Deliver a decoded packet directly to the event loop handler."""
        self.data._handle_packet(
            temperature,
            humidity,
            False,
            False,
            raw_flags,
        )

    def test_valid_humidity_is_accepted(self):
        """Valid humidity updates the sensor."""
        self.packet(69)

        self.assertEqual(self.data.humidity, 69)
        self.assertTrue(self.data.humidity_available)
        self.assertTrue(self.data.available)

    def test_invalid_humidity_preserves_last_valid_value(self):
        """Invalid readings must not overwrite valid humidity."""
        self.packet(70)
        self.packet(106)
        self.packet(125)

        self.assertEqual(self.data.humidity, 70)
        self.assertTrue(self.data.humidity_available)

    def test_invalid_humidity_does_not_reset_expiration(self):
        """Invalid readings must not extend humidity availability."""
        self.packet(70)

        humidity_cancel = self.data._humidity_expiration_cancel
        self.assertIsNotNone(humidity_cancel)

        self.packet(106)
        self.packet(125)

        self.assertIs(
            self.data._humidity_expiration_cancel,
            humidity_cancel,
        )
        humidity_cancel.assert_not_called()

    def test_humidity_expires_independently(self):
        """Humidity can expire while temperature remains available."""
        self.packet(70)

        self.data._mark_humidity_expired(
            datetime.now(timezone.utc)
        )

        self.assertFalse(self.data.humidity_available)
        self.assertTrue(self.data.available)
        self.assertEqual(self.data.humidity, 70)

    def test_valid_humidity_restores_availability(self):
        """A valid reading restores humidity after expiration."""
        self.packet(70)

        self.data._mark_humidity_expired(
            datetime.now(timezone.utc)
        )

        self.assertFalse(self.data.humidity_available)

        self.packet(71)

        self.assertEqual(self.data.humidity, 71)
        self.assertTrue(self.data.humidity_available)

    def test_mixed_valid_and_invalid_packets(self):
        """Regression for Issue #11."""
        for humidity in (69, 70, 106, 69, 125, 70):
            self.packet(humidity)

        self.assertEqual(self.data.humidity, 70)
        self.assertTrue(self.data.humidity_available)

    def test_dual_temperature_channels(self):
        """TX25TP-IT channels must remain independent."""
        data = LaCrosseDeviceData(
            hass=self.hass,
            lacrosse=self.lacrosse,
            radio_id=59,
            expire_after=300,
            multi_channel=True,
        )

        data._handle_packet(
            21.5, 106, False, False, 1
        )

        self.assertEqual(data.temperature, 21.5)
        self.assertTrue(data.available)
        self.assertIsNone(data.humidity)
        self.assertFalse(data.humidity_available)

        data._handle_packet(
            16.9, 125, False, False, 130
        )

        self.assertEqual(data.temperature, 21.5)
        self.assertEqual(data.temperature_external, 16.9)
        self.assertTrue(data.external_available)
        self.assertFalse(data.humidity_available)

        data.async_shutdown()

    def test_external_temperature_expires_independently(self):
        """External channel expiration must not affect internal."""
        data = LaCrosseDeviceData(
            hass=self.hass,
            lacrosse=self.lacrosse,
            radio_id=59,
            expire_after=300,
            multi_channel=True,
        )

        data._handle_packet(
            21.5, 106, False, False, 1
        )
        data._handle_packet(
            16.9, 125, False, False, 130
        )

        data._mark_external_expired(
            datetime.now(timezone.utc)
        )

        self.assertTrue(data.available)
        self.assertFalse(data.external_available)

        data.async_shutdown()

    def test_shutdown_cancels_all_timers(self):
        """Shutdown must cancel every scheduled expiration."""
        self.packet(69)

        data = LaCrosseDeviceData(
            hass=self.hass,
            lacrosse=self.lacrosse,
            radio_id=59,
            expire_after=300,
            multi_channel=True,
        )

        data._handle_packet(
            21.5, 106, False, False, 1
        )
        data._handle_packet(
            16.9, 125, False, False, 130
        )

        timers = [
            self.data._expiration_cancel,
            self.data._humidity_expiration_cancel,
            data._expiration_cancel,
            data._external_expiration_cancel,
        ]

        self.data.async_shutdown()
        data.async_shutdown()

        for cancel in timers:
            self.assertIsNotNone(cancel)
            cancel.assert_called_once()

    def test_packets_after_shutdown_are_ignored(self):
        """Late packets must not modify a shut-down device."""
        self.packet(69)

        self.data.async_shutdown()

        self.packet(80)

        self.assertEqual(self.data.humidity, 69)


if __name__ == "__main__":
    unittest.main()
