"""Tests for the 'alias' plugin."""

import os
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generator
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


tests_path = Path(__file__).parent


class BeetsTestCase(unittest.TestCase, TestHelper):  # type: ignore
    """TestHelper based TestCase for beets."""

    def setUp(self) -> None:
        """Set up test case."""
        self.setup_beets()
        self.config["pluginpath"] = [
            str(tests_path.parent / "src" / "beetsplug"),
            str(tests_path / "beetsplug"),
        ]
        self.config["plugins"] = ["testplugin"]

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

    def unregister_listener(self, event: str, func: Any) -> None:
        """Unregister a beets plugin event listener."""
        for i, f in enumerate(self.plugin._raw_listeners[event]):
            if f == func:
                self.plugin._raw_listeners[event].pop(i)
                self.plugin.listeners[event].pop(i)

    @contextmanager
    def assertFiresEvent(  # noqa: N802
        self, event: str, **event_args: Any
    ) -> Generator[List[List[Any]], None, None]:
        """Assert that a beets plugin event is fired."""
        events: List[List[Any]] = []

        def event_func(event: str = event, **args: Any) -> None:
            events.append([event, args])

        self.plugin.register_listener(event, event_func)
        try:
            yield events

            event_names = [event for event, _ in events]
            self.assertIn(event, event_names)

            fired_args = next(args for name, args in events if name == event)
            for name, value in event_args.items():
                self.assertIn(name, fired_args)
                self.assertEqual(fired_args[name], value)
        finally:
            self.unregister_listener(event, event_func)


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

        testcommand2 = Path(os.fsdecode(self.temp_dir)) / "beet-testcommand2"
        with open(testcommand2, "w") as f:
            f.write("#!/bin/sh\necho 'Hello, world from beet-testcommand2!'\n")

        self.load_plugin()
        self.config_path = Path(os.fsdecode(self.temp_dir)) / "config.yaml"

    def load_plugin(self) -> None:
        """Load alias plugin."""
        plugins = self.load_plugins("testplugin", "alias")
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

    @pytest.mark.skipif(sys.platform == "win32", reason="Skipping test on Windows")
    def test_from_path_ignore_noexec(self) -> None:
        """Test that alias will ignore non-executable external commands from PATH."""
        self._setup_config({"from_path": True})

        alias_output = self.run_with_output("alias")
        self.assertNotIn("testcommand2", alias_output)

        with self.assertRaisesRegex(UserError, "unknown command 'testcommand2'"):
            self.run_with_output("testcommand2")

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

        with self.assertFiresEvent(
            "alias_succeeded", alias="hello", command=["echo", "hello,", "world"]
        ):
            self.run_with_output("hello", "world")

    def test_alias_failed_event(self) -> None:
        """Test firing of alias_failed event."""
        self._setup_config({"from_path": False, "aliases": {"fail": "!false"}})

        event_args = {"alias": "fail", "command": ["false"], "exitcode": 1}
        with self.assertRaises(SystemExit), self.assertFiresEvent(
            "alias_failed", **event_args
        ):
            self.run_with_output("fail")

    def test_alias_trigger_database_change(self) -> None:
        """Test triggering of database_change event."""
        self._setup_config({"from_path": False, "aliases": {"fail": "!sh -c 'exit 8'"}})

        with self.assertRaises(SystemExit), self.assertFiresEvent(
            "database_change", model=None
        ):
            self.run_with_output("fail")

    def test_alias_to_command_which_exits_explicitly(self) -> None:
        """Test alias to a command which explicitly exits successfully ."""
        self._setup_config({"from_path": False, "aliases": {"testalias": "testexit"}})

        self.run_with_output("testalias")
