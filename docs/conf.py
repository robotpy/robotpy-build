# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import pkg_resources

os.environ["GENERATING_DOCUMENTATION"] = "True"

__version__ = pkg_resources.get_distribution("robotpy-build").version


# -- RTD configuration ------------------------------------------------

# on_rtd is whether we are on readthedocs.org, this line of code grabbed from docs.readthedocs.org
on_rtd = os.environ.get("READTHEDOCS", None) == "True"

# -- Project information -----------------------------------------------------

project = "robotpy-build"
copyright = "2020, RobotPy Development Team"
author = "RobotPy Development Team"

# The full version, including alpha/beta/rc tags
version = ".".join(__version__.split(".")[:3])
release = __version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
    "sphinx.ext.intersphinx",
]

# For sphinx-autodoc-typehints
always_document_param_types = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

intersphinx_mapping = {
    "pybind11": (
        "https://pybind11.readthedocs.io/en/latest/",
        None,
    )
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme

    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
else:
    html_theme = "default"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []


import inspect
import sphinx
import sphinx_autodoc_typehints

format_annotation_needs_config = (
    "config" in inspect.signature(sphinx_autodoc_typehints.format_annotation).parameters
)


class Processor:
    def process_docstring(self, app, what, name, obj, options, lines):
        if what == "class":
            self.hints = sphinx_autodoc_typehints.get_all_type_hints(obj, name)

        elif what == "attribute":
            name = name.split(".")[-1]
            hint = self.hints.get(name)
            if hint:
                if format_annotation_needs_config:
                    typename = sphinx_autodoc_typehints.format_annotation(
                        hint, app.config
                    )
                else:
                    typename = sphinx_autodoc_typehints.format_annotation(hint)
                lines.append(":type: " + typename)
                lines.append("")


def setup(app):
    p = Processor()
    app.connect("autodoc-process-docstring", p.process_docstring)
