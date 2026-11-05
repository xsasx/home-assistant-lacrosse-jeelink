"""Regression tests for ignored radio IDs during battery reassignment.

Execute the real options-flow methods with lightweight stand-ins so
Home Assistant and radio hardware are not required.
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
    def Schema(schema):
        return schema


def _load_battery_methods():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    flow = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "LaCrosseJeelinkOptionsFlow"
    )
    wanted = {
        "async_step_replace_battery_scan",
        "async_step_replace_battery_confirm",
    }
    functions = [
        node for node in flow.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name in wanted
    ]
    assert len(functions) == 2
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
                body=functions,
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
    }
    exec(compile(wrapper, str(SOURCE), "exec"), namespace)
    return namespace["FlowUnderTest"]


FlowUnderTest = _load_battery_methods()


class BatteryFlowHarness(FlowUnderTest):
    def __init__(self, ignored=(), packets=None):
        self._replacement_sensor_key = "kitchen"
        self._replacement_old_id = 10
        self._replacement_candidate_id = None
        self._replacement_started_at = datetime.now(timezone.utc) - timedelta(
            seconds=5
        )
        self.config_entry = SimpleNamespace(
            options={
                "sensors": {
                    "kitchen": {"name": "Kitchen", "radio_id": 10}
                },
                "ignored_radio_ids": list(ignored),
            },
            runtime_data=SimpleNamespace(
                discovered_sensors=packets or {}
            ),
        )

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "entry", **kwargs}

    def async_abort(self, **kwargs):
        return {"type": "abort", **kwargs}


class TestIgnoredBatteryReassignment(unittest.IsolatedAsyncioTestCase):
    def packet(self):
        return {
            "last_new_battery_seen": (
                datetime.now(timezone.utc) - timedelta(seconds=1)
            )
        }

    async def test_ignored_candidate_is_blocked(self):
        flow = BatteryFlowHarness(
            ignored=[8], packets={8: self.packet()}
        )
        result = await flow.async_step_replace_battery_scan(
            {"continue_scan": True}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(
            result["errors"]["base"], "ignored_radio_id_detected"
        )
        self.assertIsNone(flow._replacement_candidate_id)

    async def test_mixed_candidates_do_not_auto_assign(self):
        flow = BatteryFlowHarness(
            ignored=[8],
            packets={8: self.packet(), 55: self.packet()},
        )
        result = await flow.async_step_replace_battery_scan(
            {"continue_scan": True}
        )
        self.assertEqual(
            result["errors"]["base"], "ignored_radio_id_detected"
        )
        self.assertIsNone(flow._replacement_candidate_id)

    async def test_normal_candidate_is_still_accepted(self):
        flow = BatteryFlowHarness(
            ignored=[8], packets={55: self.packet()}
        )
        result = await flow.async_step_replace_battery_scan(
            {"continue_scan": True}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(flow._replacement_candidate_id, 55)
        self.assertEqual(result["step_id"], "replace_battery_confirm")

    async def test_confirmation_rechecks_ignore_list(self):
        flow = BatteryFlowHarness(ignored=[8])
        flow._replacement_candidate_id = 8
        result = await flow.async_step_replace_battery_confirm(
            {"confirm": True}
        )
        self.assertEqual(result["type"], "form")
        self.assertEqual(
            result["errors"]["base"], "ignored_radio_id_detected"
        )
        self.assertEqual(
            flow.config_entry.options["sensors"]["kitchen"]["radio_id"], 10
        )

    async def test_normal_confirmation_keeps_sensor_identity(self):
        flow = BatteryFlowHarness(ignored=[8])
        flow._replacement_candidate_id = 55
        result = await flow.async_step_replace_battery_confirm(
            {"confirm": True}
        )
        self.assertEqual(result["type"], "entry")
        self.assertEqual(
            result["data"]["sensors"]["kitchen"]["radio_id"], 55
        )
        self.assertEqual(
            flow.config_entry.options["sensors"]["kitchen"]["radio_id"], 10
        )


if __name__ == "__main__":
    unittest.main()
