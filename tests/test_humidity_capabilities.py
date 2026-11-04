
"""Regression tests for LaCrosse humidity capability handling.

Issue #11:
Invalid humidity packets must never permanently disable
humidity support for an existing sensor.

These tests inspect the integration source without requiring
Home Assistant or physical JeeLink hardware.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


INIT_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "lacrosse_jeelink"
    / "__init__.py"
)


class TestHumidityCapabilities(unittest.TestCase):
    """Protect humidity capability handling against regressions."""

    @classmethod
    def setUpClass(cls):
        """Parse the actual integration source."""
        cls.source = INIT_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

        cls.setup_function = next(
            node
            for node in cls.tree.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "async_setup_entry"
        )

    @classmethod
    def get_nested_function(cls, name):
        """Find a function inside async_setup_entry."""
        for node in ast.walk(cls.setup_function):
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ) and node.name == name:
                return node

        raise AssertionError(
            f"Expected function {name!r} was not found"
        )

    def test_valid_humidity_helper_exists(self):
        """Humidity validity must be checked explicitly."""
        functions = [
            node.name
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
        ]

        self.assertIn(
            "_has_valid_humidity",
            functions,
        )

    def test_invalid_packets_are_ignored_for_restoration(self):
        """Invalid packets must not trigger capability changes."""
        function = self.get_nested_function(
            "check_existing_sensor_capabilities"
        )

        statements = function.body

        self.assertTrue(
            statements,
            "Capability check must not be empty",
        )

        first_statement = statements[0]

        self.assertIsInstance(first_statement, ast.Expr)
        self.assertIsInstance(
            first_statement.value,
            ast.Constant,
        )

        guards = [
            node
            for node in statements
            if isinstance(node, ast.If)
        ]

        self.assertTrue(
            guards,
            "Expected a humidity validation guard",
        )

        first_guard = guards[0]

        self.assertIn(
            "_has_valid_humidity",
            ast.unparse(first_guard.test),
        )

        self.assertTrue(
            any(
                isinstance(node, ast.Return)
                for node in first_guard.body
            ),
            "Invalid humidity must return without changes",
        )

    def test_humidity_restoration_is_preserved(self):
        """Valid readings must still allow humidity restoration."""
        function = self.get_nested_function(
            "restore_humidity_sensor"
        )

        source = ast.unparse(function)

        self.assertIn(
            "CONF_HAS_HUMIDITY",
            source,
        )

        self.assertIn(
            "async_update_entry",
            source,
        )

        self.assertIn(
            "async_reload",
            source,
        )

    def test_dual_channel_sensors_are_excluded(self):
        """TX25TP-IT sensors must not gain humidity entities."""
        for function_name in (
            "restore_humidity_sensor",
            "check_existing_sensor_capabilities",
        ):
            function = self.get_nested_function(
                function_name
            )

            self.assertIn(
                "CONF_MULTI_CHANNEL",
                ast.unparse(function),
            )

    def test_manual_capabilities_are_preserved(self):
        """Explicit user choices must not be overwritten."""
        for function_name in (
            "restore_humidity_sensor",
            "check_existing_sensor_capabilities",
        ):
            function = self.get_nested_function(
                function_name
            )

            source = ast.unparse(function)

            self.assertIn(
                "CONF_HUMIDITY_MODE",
                source,
            )

            self.assertIn(
                "HUMIDITY_MODE_MANUAL",
                source,
            )

    def test_no_automatic_humidity_disable(self):
        """Automatic detection must not disable humidity support."""
        function = self.get_nested_function(
            "check_existing_sensor_capabilities"
        )

        source = ast.unparse(function)

        self.assertNotIn(
            "CONF_HAS_HUMIDITY: False",
            source,
        )

        self.assertNotIn(
            "CONF_HAS_HUMIDITY] = False",
            source,
        )


if __name__ == "__main__":
    unittest.main()
