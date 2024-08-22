# Alias Plugin for Beets

[![PyPI](https://img.shields.io/pypi/v/beets-alias.svg)][pypi status]
[![Status](https://img.shields.io/pypi/status/beets-alias.svg)][pypi status]
[![Python Version](https://img.shields.io/pypi/pyversions/beets-alias)][pypi status]
[![License](https://img.shields.io/pypi/l/beets-alias)][license]

[![Read the documentation at https://beets-alias.readthedocs.io/](https://img.shields.io/readthedocs/beets-alias/latest.svg?label=Read%20the%20Docs)][read the docs]
[![Tests](https://github.com/kergoth/beets-alias/workflows/Tests/badge.svg)][tests]
[![Codecov](https://codecov.io/gh/kergoth/beets-alias/branch/main/graph/badge.svg)][codecov]

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)][pre-commit]
[![Ruff codestyle][ruff badge]][ruff project]

[pypi status]: https://pypi.org/project/beets-alias/
[read the docs]: https://beets-alias.readthedocs.io/
[tests]: https://github.com/kergoth/beets-alias/actions?workflow=Tests
[codecov]: https://app.codecov.io/gh/kergoth/beets-alias
[pre-commit]: https://github.com/pre-commit/pre-commit
[ruff badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
[ruff project]: https://github.com/charliermarsh/ruff

The [alias](https://github.com/kergoth/beets-alias) plugin for [beets][] lets you define command aliases, much like git, and also makes available any beet-prefixed commands in your `PATH` as well.

## Installation

As the beets documentation describes in [Other plugins][], to use an external plugin like this one, there are two options for installation:

- Make sure it’s in the Python path (known as `sys.path` to developers). This just means the plugin has to be installed on your system (e.g., with a setup.py script or a command like pip or easy_install). For example, `pip install beets-alias`.
- Set the pluginpath config variable to point to the directory containing the plugin. (See Configuring) This would require cloning or otherwise downloading this [repository](https://github.com/kergoth/beets-stylize) before adding to the pluginpath.

## Configuring

First, enable the `alias` plugin (see [Using Plugins][]).

To configure the plugin, make an `alias:` section in your configuration
file. The available options are:

- **from_path**: Make beet-prefixed commands from `PATH` available.
  Default: `yes`
- **aliases**: Map alias names to beets commands or external shell
  commands. External commands should start with `!`. This mirrors the
  behavior of git. An alias may also be defined in an expanded form
  including help text. An alias may also accept placeholders in the
  form of `{0}`, `{1}` etc. These placeholders will be replaced by the
  provided arguments with the respective index. `{0}` will be replaced
  by parameter 0, `{1}` with parameter 1 and so on. There\'s a special
  placeholder `{}` which is used for parameters without a matching
  placeholder (see examples below). This is necessary to enable
  building aliases for beets commands with a variable number of
  arguments (like modify). If this placeholder does not exist, the
  parameters will be appended to the command.

The **aliases** section may be under `alias:`, or on its own at top-level.

### Example Configuration

```yaml
alias:
  from_path: yes

aliases:
  singletons: ls singleton:true

  # $ beet get-config alias.aliases.singletons
  get-config: '!sh -c "for arg; do beet config | yq -r \".$arg\"; done" -'

  # Red flags
  empty-artist: ls artist::'^$'
  empty-album: ls album::'^$' singleton:false

  # Simple parameter expansion
  list-live: ls artist:{0} album:{1}
  # command: list-live yello live
  # expands to: beet ls artist:yello album:live

  # Expansion: more placeholders than parameters (command will probably fail)
  list-fail: ls artist:{0} album:{1}
  # command: beet list-fail yello
  # expands to: beet ls artist:yello album:{1}

  # Expansion: more parameters than placeholders, parameters appended
  list-live-2017a: ls year:{2}
  # command: beet list-live-2017a yello live 2017
  # expands to: beet ls year:2017 yello live

  # Expansion: more parameters than placeholders, parameters inserted
  list-live-2017b: ls {} year:{2}
  # command: beet list-live-2017b yello live 2017
  # expands to: beet ls yello live year:2017

  # Expansion: real-world example, modify all live albums by Yello
  set-genre-pop: modify -a {} genre={0}
  # command: beet "Synthie Pop" yello live
  # exapands to: beet modify -a yello live genre="Synthie Pop"

  # Mac-specific
  picard:
    command: '!open -A -a "MusicBrainz Picard"'
    help: Open items in MusicBrainz Picard
```

## Using

Run the beet subcommands created by your aliases configuration. You may also run `beet alias` to list the defined aliases.

## Contributing

Contributions are very welcome.
To learn more, see the [Contributor Guide].

## License

Distributed under the terms of the [MIT license][license],
_Alias Plugin for Beets_ is free and open source software.

## Issues

If you encounter any problems,
please [file an issue] along with a detailed description.

## Credits

This project is a plugin for the [beets][] project, and would not exist without that fantastic project.
This project was generated from [@cjolowicz]'s [Hypermodern Python Cookiecutter] template.

[@cjolowicz]: https://github.com/cjolowicz
[hypermodern python cookiecutter]: https://github.com/cjolowicz/cookiecutter-hypermodern-python
[file an issue]: https://github.com/kergoth/beets-alias/issues
[beets]: https://beets.readthedocs.io/en/stable/index.html
[other plugins]: https://beets.readthedocs.io/en/stable/plugins/index.html#other-plugins
[using plugins]: https://beets.readthedocs.io/en/stable/plugins/index.html#using-plugins

<!-- github-only -->

[license]: https://github.com/kergoth/beets-alias/blob/main/LICENSE
[contributor guide]: https://github.com/kergoth/beets-alias/blob/main/CONTRIBUTING.md
