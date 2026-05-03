"""Test Plugin."""

import sys
from optparse import Values

from beets.library import Library
from beets.plugins import BeetsPlugin
from beets.plugins import send
from beets.ui import Subcommand


test_exit_command = Subcommand("testexit", help="test command")  # type: ignore[no-untyped-call]


def do_test_exit_command(lib: Library, opts: Values, args: list[str]) -> None:
    """Run a test command which explicitly exits."""
    send("cli_exit", lib=lib)
    lib._close()  # type: ignore[no-untyped-call]
    sys.exit(0)


test_exit_command.func = do_test_exit_command


class TestPlugin(BeetsPlugin):
    """Test Plugin."""

    def commands(self) -> list[Subcommand]:
        """Return beets subcommands."""
        return [test_exit_command]
