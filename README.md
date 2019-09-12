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

The [alias](https://github.com/kergoth/beets-alias) plugin for [beets][] does something useful.

## Installation

As the beets documentation describes in [Other plugins][], to use an external plugin like this one, there are two options for installation:

- Make sure it’s in the Python path (known as `sys.path` to developers). This just means the plugin has to be installed on your system (e.g., with a setup.py script or a command like pip or easy_install). For example, `pip install beets-alias`.
- Set the pluginpath config variable to point to the directory containing the plugin. (See Configuring) This would require cloning or otherwise downloading this [repository](https://github.com/kergoth/beets-stylize) before adding to the pluginpath.

## Configuring

First, enable the `alias` plugin (see [Using Plugins][]).

Describe plugin configuration here.

## Using

Describe plugin usage here. Please see the [Command-line Reference] for the command-line interface.

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
[command-line reference]: https://beets-alias.readthedocs.io/en/latest/usage.html
