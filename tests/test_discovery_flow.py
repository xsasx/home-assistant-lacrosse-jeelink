"""Regression tests for LaCrosse discovery freshness and filtering.

Run actual options-flow methods with lightweight Home Assistant stand-ins.
No hardware or Home Assistant installation required.
"""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components" / "lacrosse_jeelink" / "config_flow.py"
)


class _Vol:
    @staticmethod
    def Required(name, **kwargs):
        return name

    @staticmethod
    def In(choices):
        return choices

    @staticmethod
    def Schema(schema):
        return schema


def _has_valid_humidity(value):
    return value is not None and 0 <= value <= 100


def _load_scan_method():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    flow = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "LaCrosseJeelinkOptionsFlow"
    )
    scan = next(
        node for node in flow.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "async_step_scan_sensor"
    )
    wrapper = ast.Module(
        body=[
            ast.ImportFrom(
                module="__future__",
                names=[ast.alias(name="annotations")],
                level=0,
            ),
            ast.ClassDef(
                name="FlowUnderTest",
                bases=[],
                keywords=[],
                body=[scan],
                decorator_list=[],
            ),
        ],
        type_ignores=[],
    )
    ast.fix_missing_locations(wrapper)
    namespace = {
        "datetime": datetime,
        "timedelta": timedelta,
        "timezone": timezone,
        "vol": _Vol,
        "CONF_SENSORS": "sensors",
        "CONF_RADIO_ID": "radio_id",
        "CONF_IGNORED_RADIO_IDS": "ignored_radio_ids",
        "_has_valid_humidity": _has_valid_humidity,
    }
    exec(compile(wrapper, str(SOURCE), "exec"), namespace)
    return namespace["FlowUnderTest"]


FlowUnderTest = _load_scan_method()


class DiscoveryHarness(FlowUnderTest):
    def __init__(self, packets, *, configured=None, ignored=()):
        self._show_stale_discoveries = True
        self._discovered_radio_id = None
        self.config_entry = SimpleNamespace(
            runtime_data=SimpleNamespace(discovered_sensors=packets),
            options={
                "sensors": configured or {},
                "ignored_radio_ids": list(ignored),
            },
        )

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_abort(self, **kwargs):
        return {"type": "abort", **kwargs}

    async def async_step_add_discovered_sensor(self):
        return {"type": "add", "radio_id": self._discovered_radio_id}


def packet(*, minutes_old=0, humidity=50, seen=True):
    return {
        "temperature": 19.5,
        "humidity": humidity,
        "low_battery": False,
        "last_seen": (
            datetime.now(timezone.utc) - timedelta(minutes=minutes_old)
            if seen else None
        ),
    }


class TestDiscoveryFreshness(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def choices(result):
        return result["data_schema"]["discovered_sensor"]

    async def test_active_and_stale_indicators(self):
        flow = DiscoveryHarness({5: packet(), 8: packet(minutes_old=11)})
        choices = self.choices(await flow.async_step_scan_sensor())
        self.assertIn("ACTIVE (just now)", choices["5"])
        self.assertIn("STALE (11 min ago)", choices["8"])

    async def test_filter_hides_only_stale_unconfigured(self):
        flow = DiscoveryHarness(
            {5: packet(minutes_old=20), 8: packet(minutes_old=20),
             9: packet(minutes_old=1), 55: packet(seen=False)},
            configured={"freezer": {"radio_id": 5, "name": "Freezer"}},
        )
        filtered = self.choices(await flow.async_step_scan_sensor(
            {"discovered_sensor": "__toggle_stale__"}
        ))
        self.assertFalse(flow._show_stale_discoveries)
        self.assertIn("5", filtered)
        self.assertIn("9", filtered)
        self.assertNotIn("8", filtered)
        self.assertNotIn("55", filtered)
        self.assertIn("Show stale discoveries", filtered["__toggle_stale__"])

        restored = self.choices(await flow.async_step_scan_sensor(
            {"discovered_sensor": "__toggle_stale__"}
        ))
        self.assertTrue(flow._show_stale_discoveries)
        self.assertIn("8", restored)
        self.assertIn("55", restored)

    async def test_ignored_id_stays_hidden_even_after_toggle(self):
        flow = DiscoveryHarness(
            {5: packet(), 8: packet(), 55: packet(minutes_old=30)},
            ignored=[8],
        )
        initial = self.choices(await flow.async_step_scan_sensor())
        self.assertNotIn("8", initial)
        refreshed = self.choices(await flow.async_step_scan_sensor(
            {"discovered_sensor": "__toggle_stale__"}
        ))
        self.assertNotIn("8", refreshed)

    async def test_refresh_rereads_updated_packets(self):
        flow = DiscoveryHarness({5: packet(minutes_old=15)})
        first = self.choices(await flow.async_step_scan_sensor())
        self.assertIn("STALE", first["5"])
        flow.config_entry.runtime_data.discovered_sensors[5] = packet()
        refreshed = self.choices(await flow.async_step_scan_sensor(
            {"discovered_sensor": "__refresh__"}
        ))
        self.assertIn("ACTIVE", refreshed["5"])

    async def test_hidden_id_cannot_be_added_from_old_form(self):
        flow = DiscoveryHarness({8: packet(minutes_old=15)})
        await flow.async_step_scan_sensor({"discovered_sensor": "__toggle_stale__"})
        result = await flow.async_step_scan_sensor({"discovered_sensor": "8"})
        self.assertEqual(result["type"], "form")
        self.assertIsNone(flow._discovered_radio_id)

    async def test_active_new_id_still_can_be_added(self):
        flow = DiscoveryHarness({8: packet()})
        result = await flow.async_step_scan_sensor({"discovered_sensor": "8"})
        self.assertEqual(result, {"type": "add", "radio_id": 8})

    async def test_configured_id_not_addable(self):
        flow = DiscoveryHarness(
            {5: packet()},
            configured={"freezer": {"radio_id": 5, "name": "Freezer"}},
        )
        result = await flow.async_step_scan_sensor({"discovered_sensor": "5"})
        self.assertEqual(
            result,
            {"type": "abort", "reason": "sensor_already_configured"},
        )


if __name__ == "__main__":
    unittest.main()
