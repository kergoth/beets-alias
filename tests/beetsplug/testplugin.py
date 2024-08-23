"""Test Plugin."""

import sys
from optparse import Values
from typing import List

from beets.library import Library  # type: ignore
from beets.plugins import BeetsPlugin  # type: ignore
from beets.plugins import send
from beets.ui import Subcommand  # type: ignore


test_exit_command = Subcommand("testexit", help="test command")


def do_test_exit_command(lib: Library, opts: Values, args: List[str]) -> None:
    """Run a test command which explicitly exits."""
    send("cli_exit", lib=lib)
    lib._close()
    sys.exit(0)


test_exit_command.func = do_test_exit_command


class TestPlugin(BeetsPlugin):  # type: ignore
    """Test Plugin."""

    def commands(self) -> List[Subcommand]:
        """Return beets subcommands."""
        return [test_exit_command]
