"""Sphinx configuration."""

project = "Alias Plugin for Beets"
author = "Christopher Larson"
copyright = "2024, Christopher Larson"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "myst_parser",
]
autodoc_typehints = "description"
html_theme = "furo"
