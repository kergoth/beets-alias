"""Tests for the 'alias' plugin."""

import os
import sys
import unittest
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import beets.plugins  # type: ignore
import pytest
from beets.plugins import BeetsPlugin
from beets.plugins import find_plugins
from beets.plugins import send
from beets.test.helper import TestHelper  # type: ignore
from beets.ui import UserError  # type: ignore
from confuse.exceptions import ConfigError  # type: ignore


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

        os.environ["PATH"] = (
            os.fsdecode(self.temp_dir) + os.pathsep + os.environ["PATH"]
        )

        testcommand = Path(os.fsdecode(self.temp_dir)) / "beet-testcommand"
        with open(testcommand, "w") as f:
            f.write("#!/bin/sh\necho 'Hello, world from beet-testcommand!'\n")
        testcommand.chmod(0o755)

        self.load_plugin()
        self.config_path = Path(os.fsdecode(self.temp_dir)) / "config.yaml"

    def load_plugin(self) -> None:
        """Load alias plugin."""
        plugins = self.load_plugins("alias")
        for plugin in plugins:
            if plugin.name == "alias":
                self.plugin = plugin
                break
        else:
            self.fail("Plugin not loaded")

    def _setup_config(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Set up configuration."""
        if config is None:
            config = {
                "from_path": False,
                "aliases": {
                    "hello": '!echo "Hello {0}, I\'m a plugin"',
                    "bye": '!echo "Goodbye!"',
                    "echo": "!echo",
                    "ls-alias": "ls",
                    "version-alias": "version",
                    "config-paths": "config -p",
                    "config-alias": "config",
                    "config-paths-alias": "config-paths",
                    "echo-alias": "echo",
                },
            }
        self.config["alias"] = config
        self.config["aliases"] = {}
        return config

    def test_alias_command(self) -> None:
        """Test alias subcommand."""
        config = self._setup_config()
        output = self.run_with_output("alias").splitlines()
        for alias, command in config["aliases"].items():
            self.assertIn(f"{alias}: {command}", output)

    def test_alias_run_external(self) -> None:
        """Test alias run without parameters or substitution."""
        self._setup_config()
        output = self.run_with_output("bye")
        self.assertIn("Goodbye!", output)

    def test_alias_run_external_params(self) -> None:
        """Test alias run with parameters."""
        self._setup_config()
        output = self.run_with_output("echo", "hello world")
        self.assertIn("hello world", output)

    def test_alias_run_external_param_subst(self) -> None:
        """Test alias run with parameter substitution."""
        self._setup_config()
        output = self.run_with_output("hello", "world")
        self.assertIn("Hello world, I'm a plugin", output)

    def test_alias_run_external_param_subst_multiple_append(self) -> None:
        """Test alias run with multiple parameter substitution, appending remainder."""
        self._setup_config()
        output = self.run_with_output("hello", "world", "beets")
        self.assertIn("Hello world, I'm a plugin beets", output)

    def test_alias_run_external_param_subst_multiple_explicit(self) -> None:
        """Test alias run with multiple parameter substitution."""
        self._setup_config(
            {
                "from_path": False,
                "aliases": {"hello": '!echo "Hello {0}, I\'m a {1} plugin"'},
            }
        )
        output = self.run_with_output("hello", "world", "beets")
        self.assertIn("Hello world, I'm a beets plugin", output)

    def test_alias_run_external_param_subst_multiple_remainder(self) -> None:
        """Test alias run with multiple parameter substitution with remainder."""
        self._setup_config(
            {
                "from_path": False,
                "aliases": {"hello": '!echo "Hello {0}, I\'m a" {} "plugin"'},
            }
        )
        output = self.run_with_output("hello", "world", "beets", "extra")
        self.assertIn("Hello world, I'm a beets extra plugin", output)

    def test_alias_run_internal(self) -> None:
        """Test alias run internal command."""
        self._setup_config()
        output = self.run_with_output("version-alias")
        self.assertIn("beets version ", output)
        self.assertIn("Python version ", output)
        self.assertIn("plugins:", output)

    def test_alias_run_internal_arguments(self) -> None:
        """Test alias run internal command with arguments."""
        self._setup_config()
        output = self.run_with_output("config-paths")
        self.assertEqual(output, f"{self.config_path}\n")

    def test_alias_run_internal_passed_arguments(self) -> None:
        """Test alias run internal command with passed arguments."""
        self._setup_config()
        output = self.run_with_output("config-alias", "-p")
        output2 = self.run_with_output("config-paths")
        self.assertNotEqual(output, "")
        self.assertEqual(output, output2)

    def test_run_internal_indirect(self) -> None:
        """Test alias run internal command aliased to another alias."""
        self._setup_config()
        output = self.run_with_output("config-paths-alias")
        self.assertEqual(output, f"{self.config_path}\n")

    def test_run_external_indirect(self) -> None:
        """Test alias run external command aliased to another alias."""
        self._setup_config()
        output = self.run_with_output("echo-alias", "Hello, world!")
        self.assertEqual(output, "Hello, world!\n")

    @pytest.mark.skipif(sys.platform == "win32", reason="Skipping test on Windows")
    def test_from_path(self) -> None:
        """Test alias run external command from PATH."""
        self._setup_config({"from_path": True})

        alias_output = self.run_with_output("alias")
        self.assertIn("testcommand", alias_output)

        output = self.run_with_output("testcommand")
        self.assertEqual(output, "Hello, world from beet-testcommand!\n")

    def test_duplicate_alias(self) -> None:
        """Test alias with duplicate name."""
        self._setup_config({"from_path": False, "aliases": {"hello": "echo"}})
        self.config["aliases"] = {"hello": "echo2"}

        with self.assertRaisesRegex(
            ConfigError, "alias hello was specified multiple times"
        ):
            self.run_with_output("hello")

    def test_mapping_alias(self) -> None:
        """Test alias with mapping."""
        self._setup_config(
            {
                "from_path": False,
                "aliases": {
                    "hello": {
                        "command": "!echo Hello",
                        "help": "Say hello",
                    }
                },
            }
        )
        output = self.run_with_output("hello")
        self.assertEqual(output, "Hello\n")

    def test_config_mapping_missing_command(self) -> None:
        """Test alias with mapping missing command."""
        self._setup_config({"from_path": False, "aliases": {"hello": {}}})
        with self.assertRaisesRegex(ConfigError, "command not found"):
            self.run_with_output("hello")

    def test_config_invalid_alias_type(self) -> None:
        """Test alias with invalid type."""
        self._setup_config({"from_path": False, "aliases": {"hello": 1}})
        with self.assertRaisesRegex(
            ConfigError, "must be a string or single-element mapping"
        ):
            self.run_with_output("hello")

    def test_config_alias_alias(self) -> None:
        """Test alias named alias."""
        self._setup_config(
            {
                "from_path": False,
                "aliases": {
                    "alias": "echo",
                },
            }
        )
        with self.assertRaisesRegex(
            UserError, "alias `alias` is reserved for the alias plugin"
        ):
            self.run_with_output("alias")

    def test_alias_unknown_command(self) -> None:
        """Test alias to an missing beets subcommand."""
        self._setup_config({"from_path": False, "aliases": {"unknown": "missing"}})
        with self.assertRaisesRegex(UserError, "unknown command 'missing'"):
            self.run_with_output("unknown")

    def test_alias_external_failed(self) -> None:
        """Test alias run external command which fails."""
        self._setup_config({"from_path": False, "aliases": {"fail": "!false"}})
        with self.assertRaises(SystemExit) as exc:
            self.run_with_output("fail")
            self.assertEqual(exc.exception.code, 1)

    def test_alias_internal_failed(self) -> None:
        """Test alias run internal command which fails."""
        self._setup_config({"from_path": False, "aliases": {"fail": "config -x"}})
        with self.assertRaises(SystemExit) as exc:
            self.run_with_output("fail")
            self.assertEqual(exc.exception.code, 2)

    def test_alias_succeeded_event(self) -> None:
        """Test firing of alias_succeeded event."""
        self._setup_config(
            {"from_path": False, "aliases": {"hello": "!echo hello, {0}"}}
        )

        events: List[Any] = []
        self.plugin.register_listener(
            "alias_succeeded", lambda **kwargs: events.append(kwargs)
        )
        self.run_with_output("hello", "world")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["alias"], "hello")
        self.assertEqual(events[0]["command"], ["echo", "hello,", "world"])

    def test_alias_failed_event(self) -> None:
        """Test firing of alias_failed event."""
        self._setup_config({"from_path": False, "aliases": {"fail": "!false"}})

        events: List[Any] = []
        self.plugin.register_listener(
            "alias_failed", lambda **kwargs: events.append(kwargs)
        )
        with self.assertRaises(SystemExit):
            self.run_with_output("fail")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["alias"], "fail")
        self.assertEqual(events[0]["command"], ["false"])
        self.assertEqual(events[0]["exitcode"], 1)

    def test_alias_trigger_database_change(self) -> None:
        """Test triggering of database_change event."""
        self._setup_config({"from_path": False, "aliases": {"fail": "!sh -c 'exit 8'"}})

        events: List[Any] = []
        self.plugin.register_listener(
            "database_change", lambda **kwargs: events.append(kwargs)
        )
        with self.assertRaises(SystemExit):
            self.run_with_output("fail")

        self.assertEqual(len(events), 1)
        self.assertIsNone(events[0]["model"])
