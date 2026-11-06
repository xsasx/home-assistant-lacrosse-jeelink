"""Guard stable Home Assistant entity identities during the ng migration.

The beta replaces only the receiver. Existing configuration entry IDs and
sensor keys must continue producing the same HA entity/device identifiers.
These checks do not import Home Assistant or access serial hardware.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest


COMPONENT = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "lacrosse_jeelink"
)


class TestNgMigrationIdentity(unittest.TestCase):
    def test_unique_id_format_is_unchanged(self) -> None:
        tree = ast.parse((COMPONENT / "entity.py").read_text())
        base = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "LaCrosseEntity")
        init = next(node for node in base.body if isinstance(node, ast.FunctionDef) and node.name == "__init__")
        assignment = next(
            node for node in ast.walk(init)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Attribute) and target.attr == "_attr_unique_id" for target in node.targets)
        )
        self.assertIsInstance(assignment.value, ast.JoinedStr)
        self.assertEqual(
            [item.value.id for item in assignment.value.values if isinstance(item, ast.FormattedValue)],
            ["entry_id", "sensor_key", "entity_suffix"],
        )
        self.assertEqual(
            [item.value for item in assignment.value.values if isinstance(item, ast.Constant)],
            ["_", "_"],
        )

    def test_device_identifier_retains_entry_and_sensor_key(self) -> None:
        source = (COMPONENT / "entity.py").read_text()
        self.assertIn('f"{entry_id}:{sensor_key}"', source)
        self.assertIn("via_device=(DOMAIN, entry_id)", source)

    def test_existing_temperature_humidity_and_external_suffixes(self) -> None:
        tree = ast.parse((COMPONENT / "sensor.py").read_text())
        expected = {
            "LaCrosseTemperature": "temperature",
            "LaCrosseHumidity": "humidity",
            "LaCrosseExternalTemperature": "temperature_external",
        }
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or node.name not in expected:
                continue
            init = next(item for item in node.body if isinstance(item, ast.FunctionDef) and item.name == "__init__")
            calls = [item for item in ast.walk(init) if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute) and item.func.attr == "__init__"]
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].args[-1].value, expected.pop(node.name))
        self.assertEqual(expected, {})

    def test_humidity_registry_removal_uses_original_unique_id(self) -> None:
        source = (COMPONENT / "sensor.py").read_text()
        self.assertIn('f"{entry.entry_id}_{sensor_key}_humidity"', source)

    def test_config_entry_reuses_existing_options_and_sensor_ids(self) -> None:
        source = (COMPONENT / "sensor.py").read_text()
        self.assertIn("entry.options.get(CONF_SENSORS, {})", source)
        self.assertIn("int(sensor_config[CONF_RADIO_ID])", source)
        self.assertIn("entry.entry_id,", source)


if __name__ == "__main__":
    unittest.main()
