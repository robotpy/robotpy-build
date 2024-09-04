Tools
=====

robotpy-build has some useful command line tools that can be executed via
``python3 -m robotpy_build TOOLNAME``. On OSX/Linux, it is also installed
as the ``robotpy-build`` script which can be executed directly.

.. _scan_headers:

scan-headers
------------

This tool is designed to make it easy to populate the ``generate`` key for
your python package.

This will scan all of your defined includes directories (including those of
downloaded artifacts) and output something you can paste into the ``generate``
key of ``pyproject.toml``. By default it will only show files that are not
present in ``pyproject.toml`` -- to show all files use the ``--all`` argument.

Often there are files that you don't want to wrap. You can add them to the
``pyproject.toml`` file and they will be ignored. The list accepts glob patterns
supported by the fnmatch module.

.. code-block:: toml

    [tool.robotpy-build]
    scan_headers_ignore = [
        "ignored_header.h",
        "ignore_dir/*",
    ]

.. _create_gen:

create-gen
----------

This will parse your defined generate items (``generate`` key of ``pyproject.toml``)
and output yaml for them in the directory defined by ``generation_data``. By default
it will just print the file contents to stdout.

Use the ``--write`` argument to write the files, but it won't overwrite existing
files.

create-imports
--------------

Given a base package and a compiled module within that package, this will
generate contents that contain all of the things exported by the compiled
module. Often it is useful to put this in the ``__init__.py`` of your 
python package.

.. code-block:: sh

    $ python -m robotpy_build create-imports rpydemo rpydemo._rpydemo

Use the ``--write`` argument to write the file.

To write a list of ``__init__.py`` files, you can specify them in the ``pyproject.toml``
file like so:

.. code-block:: toml

    [tool.robotpy-build]
    update_init = ["rpydemo rpydemo._rpydemo"]

To actually update the files, run ``python setup.py update_init``.