# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

_this_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(_this_dir, "../..")))

import sunset  # noqa -- module import not at top of file.


# -- Project information -----------------------------------------------------

project = sunset.__project__
copyright = sunset.__copyright__
author = sunset.__author__

# The full version, including alpha/beta/rc tags

release = sunset.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions: list[str] = [
    # Displays the documentation build time on the command line.
    "sphinx.ext.duration",
    # Provides directives to automatically build documentation using the
    # docstrings of classes and modules.
    "sphinx.ext.autodoc",
    # Enables a friendlier syntax for autodoc docstrings.
    "sphinx.ext.napoleon",
    # Add links to the source from autodoc docstring.
    "sphinx.ext.viewcode",
]

# Add any paths that contain templates here, relative to this directory.
templates_path: list[str] = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns: list[str] = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]
