"""Tests for the 'alias' plugin."""

import unittest
from typing import List

import beets.plugins  # type: ignore
from beets.plugins import BeetsPlugin
from beets.plugins import find_plugins
from beets.plugins import send
from beets.test.helper import TestHelper  # type: ignore
from beets.test.helper import capture_log


class BeetsTestCase(unittest.TestCase, TestHelper):  # type: ignore
    """TestHelper based TestCase for beets."""

    def setUp(self) -> None:
        """Set up test case."""
        self.setup_beets()

    def tearDown(self) -> None:
        """Tear down test case."""
        self.teardown_beets()

    def load_plugins(self, *plugins: str) -> List[BeetsPlugin]:
        """Load and initialize plugins by names."""
        beets.plugins._instances.clear()
        beets.plugins._classes.clear()
        super().load_plugins(*plugins)
        send("pluginload")
        return find_plugins()  # type: ignore


class AliasPluginTest(BeetsTestCase):
    """Test cases for the alias beets plugin."""

    def setUp(self) -> None:
        """Set up test cases."""
        super().setUp()
        self.load_plugin()

    def load_plugin(self) -> None:
        """Load alias plugin."""
        with capture_log() as logs:
            plugins = self.load_plugins("alias")

        for plugin in plugins:
            if plugin.name == "alias":
                self.plugin = plugin
                break
        else:
            self.fail("Plugin not loaded")

        self.assertIn("alias: Plugin loaded!", logs)

    def test_command(self) -> None:
        """Test alias subcommand."""
        output = self.run_with_output("alias")
        self.assertIn("Hello everybody! I'm a plugin!", output)

    def test_template_function(self) -> None:
        """Test template function."""
        self.assertEqual(self.plugin.template_funcs["initial"]("hello"), "H")
        self.assertEqual(self.plugin.template_funcs["initial"](""), "")
