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
    def parse_args(self, args=None, namespace=None):
        if args is None:
            args = sys.argv[1:]
        return [], args


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

    with subprocess.Popen(
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


class AliasCommand(Subcommand):
    def __init__(self, alias, command, log=None, help=None):
        super().__init__(
            alias,
            help=help or command,
            parser=NoOpOptionParser(add_help_option=False, description=help or command),
        )

        self.alias = alias
        self.log = log
        self.command = command

    def func(self, lib, opts, args=None):
        if args is None:
            args = []

        split_command = shlex.split(self.command)
        command = split_command[0]
        command_args = split_command[1:]

        # loop through beet arguments, starting from behind
        for i in range(len(args) - 1, -1, -1):
            # replace all occurences of token {X} with parameter (if it exists)
            token = "{i}".replace("i", str(i))
            token_replaced = False
            for j in range(0, len(command_args), 1):
                if token in command_args[j]:
                    command_args[j] = command_args[j].replace(token, args[i])
                    token_replaced = True
            # remove parameter if it has been used for a replacement
            if token_replaced:
                del args[i]

        # search for token {} and replace it with the rest of the arguments,
        # if it exists, or append otherwise
        if "{}" in command_args:
            for i in range(len(command_args) - 1, -1, -1):
                if command_args[i] == "{}":
                    command_args[i : i + 1] = args
        else:
            command_args = command_args + args

        args = command_args

        if command.startswith("!"):
            command = command[1:]
            argv = [command, *args]

            def run_func():
                return check_call_redirected(argv)
        else:
            argv = [command, *args]
            cmdname = argv[0]

            subcommands = list(default_commands)
            subcommands.extend(plugins.commands())
            for subcommand in subcommands:
                if cmdname == subcommand.name or cmdname in subcommand.aliases:
                    break
            else:
                raise ui.UserError(f"unknown command '{cmdname}'")

            suboptions, subargs = subcommand.parse_args(argv[1:])

            def run_func():
                return subcommand.func(lib, suboptions, subargs)

        if self.log:
            self.log.debug("Running {}", subprocess.list2cmdline(argv))

        try:
            run_func()
        except subprocess.CalledProcessError as exc:
            self.failed(lib, self.alias, command, args, exc.returncode)
            plugins.send("cli_exit", lib=lib)
            lib._close()
            sys.exit(exc.returncode)
        except SystemExit as exc:
            if exc.code not in [None, 0]:
                self.failed(lib, self.alias, command, args, exc.code)
                raise
        except Exception as exc:
            self.failed(lib, self.alias, command, args, message=str(exc))
            raise

        plugins.send(
            "alias_succeeded", lib=lib, alias=self.alias, command=command, args=args
        )

    def failed(self, lib, alias, command, args, exitcode=None, message=""):
        plugins.send(
            "alias_failed",
            lib=lib,
            alias=self.alias,
            command=command,
            args=args,
            exitcode=exitcode,
            message=message,
        )
        if self.log:
            exitmsg = f" with {exitcode}" if exitcode else ""
            if message:
                message = ": " + message
            self.log.debug(
                "command `{}{}` failed{}{}",
                command,
                " " + subprocess.list2cmdline(args) if args else "",
                exitmsg,
                message,
            )


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

    def get_command(self, alias, command, help=None):
        """Create a Subcommand instance for the specified alias."""
        return AliasCommand(alias, command, log=self._log, help=help)

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
                        self.get_command(
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
                    commands[alias] = self.get_command(alias, command)
                elif isinstance(command, abc.Mapping):
                    command_text = command.get("command")
                    if not command_text:
                        raise confuse.ConfigError(f"{path}.{alias}.command not found")
                    help_text = command.get("help", command_text)
                    commands[alias] = self.get_command(alias, command_text, help_text)
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
