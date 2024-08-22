"""Support for beets command aliases, not unlike git.

By default, also checks $PATH for beet-* and makes those available as well.

Example:
    alias:
      from_path: yes # Default
      aliases:
        singletons: ls singleton:true
        external-cmd-test: '!echo'
        sh-c-test: '!sh -c "echo foo bar arg1:$1, arg2:$2" sh-c-test'
        with-help-text:
          command: ls -a
          help: do something or other
"""

import glob
import optparse
import os
import shlex
import subprocess
import sys
from collections import abc
from concurrent.futures import ThreadPoolExecutor

import confuse
import six
from beets import config
from beets import plugins
from beets import ui
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand
from beets.ui import print_
from beets.ui.commands import default_commands


class NoOpOptionParser(optparse.OptionParser):
    """A dummy option parser that doesn't do anything."""

    def parse_args(self, args=None, namespace=None):
        """Return the arguments and an empty list."""
        if args is None:
            args = sys.argv[1:]
        return [], args


class AliasPlugin(BeetsPlugin):
    """Support for beets command aliases, not unlike git."""

    def __init__(self):
        super().__init__()

        self.config.add(
            {
                "from_path": True,
                "aliases": {},
            }
        )

    def get_alias_subcommand(self, alias, command, help=None):
        """Create a Subcommand instance for the specified alias."""
        if command.startswith("!"):
            return ExternalCommand(alias, command, log=self._log, help=help)
        else:
            return BeetsCommand(alias, command, log=self._log, help=help)

    def get_path_commands(self):
        """Create subcommands for beet-* scripts in $PATH."""
        for path in os.getenv("PATH", "").split(":"):
            cmds = glob.glob(os.path.join(path, "beet-*"))
            for cmd in cmds:
                if os.access(cmd, os.X_OK):
                    command = os.path.basename(cmd)
                    alias = command[5:]
                    yield (
                        alias,
                        self.get_alias_subcommand(
                            alias, "!" + command, f"Run external command `{command}`"
                        ),
                    )

    def cmd_alias(self, lib, opts, args, commands):
        """Print the available alias commands."""
        for alias, command in sorted(commands.items()):
            print_(f"{alias}: {command}")

    def commands(self):
        """Add the alias commands."""
        if self.config["from_path"].get(bool):
            commands = dict(self.get_path_commands())
        else:
            commands = {}

        for path, subview in [
            ("alias.aliases", self.config["aliases"]),
            ("aliases", config["aliases"]),
        ]:
            for alias in subview.keys():
                if alias in commands:
                    raise confuse.ConfigError(
                        f"alias {alias} was specified multiple times"
                    )

                command = subview[alias].get()
                if isinstance(command, six.text_type):
                    commands[alias] = self.get_alias_subcommand(alias, command)
                elif isinstance(command, abc.Mapping):
                    command_text = command.get("command")
                    if not command_text:
                        raise confuse.ConfigError(f"{path}.{alias}.command not found")
                    help_text = command.get("help", command_text)
                    commands[alias] = self.get_alias_subcommand(
                        alias, command_text, help_text
                    )
                else:
                    raise confuse.ConfigError(
                        f"{path}.{alias} must be a string or single-element mapping"
                    )

        if "alias" in commands:
            raise ui.UserError("alias `alias` is reserved for the alias plugin")

        alias = Subcommand("alias", help="Print the available alias commands.")
        alias_commands = dict((a, c.command) for a, c in commands.items())
        alias.func = lambda lib, opts, args: self.cmd_alias(
            lib, opts, args, alias_commands
        )
        commands["alias"] = alias
        return commands.values()


class AliasCommand(Subcommand):
    """Base class for alias subcommands."""

    def __init__(self, name, command, log=None, help=None):
        super().__init__(
            name,
            help=help or command,
            parser=NoOpOptionParser(add_help_option=False, description=help or command),
        )

        self.name = name
        self.log = log
        self.command = command

    def substitute_parameters(self, args):
        """Replace all occurrences of {X} in command with args[X]."""
        command = self.command

        for i, arg in reversed(list(enumerate(args))):
            token = f"{'{'}{i}{'}'}"
            if token in command:
                command = command.replace(token, arg)
                del args[i]

        split_command = shlex.split(command)
        # search for token {} and replace it with the rest of the arguments,
        # if it exists, or append otherwise
        if "{}" in split_command:
            for i, arg in reversed(list(enumerate(split_command))):
                if arg == "{}":
                    split_command[i : i + 1] = args
        else:
            split_command = split_command + args

        return split_command

    def run_command(self, lib, opts, command):
        """Run the command."""
        raise NotImplementedError

    def func(self, lib, opts, args=None):
        """Run the command with the specified arguments."""
        command = self.substitute_parameters(args)

        if self.log:
            self.log.debug("Running {}", subprocess.list2cmdline(command))

        try:
            self.run_command(lib, opts, command)
        except subprocess.CalledProcessError as exc:
            self.failed(lib, self.name, command, exc.returncode)
            plugins.send("cli_exit", lib=lib)
            lib._close()
            sys.exit(exc.returncode)
        except SystemExit as exc:
            if exc.code not in [None, 0]:
                self.failed(lib, self.name, command, exc.code)
                raise
        except Exception as exc:
            self.failed(lib, self.name, command, message=str(exc))
            raise

        plugins.send(
            "alias_succeeded",
            lib=lib,
            alias=self.name,
            command=command,
            args=args,
        )

    def failed(self, lib, alias, command, exitcode=None, message=""):
        """Log the failure and send a plugin event."""
        plugins.send(
            "alias_failed",
            lib=lib,
            alias=self.name,
            command=command,
            exitcode=exitcode,
            message=message,
        )
        if self.log:
            exitmsg = f" with {exitcode}" if exitcode else ""
            if message:
                message = ": " + message
            self.log.debug(
                "command `{}` failed{}{}",
                subprocess.list2cmdline(command),
                exitmsg,
                message,
            )


class BeetsCommand(AliasCommand):
    """An alias to run a beets command."""

    def run_command(self, lib, opts, command):
        """Run the beets command."""
        cmdname = command[0]

        subcommands = list(default_commands)
        subcommands.extend(plugins.commands())
        for subcommand in subcommands:
            if cmdname == subcommand.name or cmdname in subcommand.aliases:
                break
        else:
            raise ui.UserError(f"unknown command '{cmdname}'")

        suboptions, subargs = subcommand.parse_args(command[1:])

        return subcommand.func(lib, suboptions, subargs)


class ExternalCommand(AliasCommand):
    """An alias to run an external command."""

    def run_command(self, lib, opts, command):
        """Run the external command."""
        if command[0].startswith("!"):
            command[0] = command[0][1:]
        return check_call_redirected(command)


def redirect_output(p, stdfile, log):
    """Redirect data from stdfile to log while waiting for p to finish."""
    while p.poll() is None:
        log.write(stdfile.readline())
        log.flush()

    # Write the rest from the buffer
    log.write(stdfile.read())


def check_call_redirected(*popenargs, **kwargs):
    """Like subprocess.check_call, but redirects the output to sys.stdout/sys.stderr."""
    if "stdout" in kwargs:
        raise ValueError("stdout argument not allowed, it will be overridden.")
    if "stderr" in kwargs:
        raise ValueError("stderr argument not allowed, it will be overridden.")

    with subprocess.Popen(  # noqa: S603
        *popenargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs
    ) as p:
        with ThreadPoolExecutor(2) as pool:
            r1 = pool.submit(redirect_output, p, p.stdout, sys.stdout)
            r2 = pool.submit(redirect_output, p, p.stderr, sys.stderr)
            r1.result()
            r2.result()

    if p.returncode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise subprocess.CalledProcessError(p.returncode, cmd)
    return 0
