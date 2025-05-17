Tools
=====

semiwrap has some useful command line tools that can be executed via
``python3 -m semiwrap TOOLNAME``. On OSX/Linux, it is also installed
as the ``semiwrap`` script which can be executed directly.

.. _build_dep:

build-dep
---------

Grabs the contents of ``build-system.requires`` from ``pyproject.toml`` and
installs them via pip.

.. _scan_headers:

scan-headers
------------

This will scan all directories in the search path for your extension modules
and output something you can paste into ``[tool.semiwrap.extension_modules."PACKAGE.NAME".headers]``.
By default it will only show files that are not present in ``pyproject.toml``
which makes it useful to determine if your dependencies have added any files.
To show all files use the ``--all`` argument.

Often there are files that you don't want to wrap. You can add them to the
``pyproject.toml`` file in ``scan_headers_ignore`` and they will be ignored.
The list accepts glob patterns supported by the fnmatch module.

.. code-block:: toml

    [tool.semiwrap]
    scan_headers_ignore = [
        "ignored_header.h",
        "ignore_dir/*",
    ]

To output the scanned headers to a list of ignored files, you can use the
``--as-ignore`` option.

.. _create_yaml:

create-yaml
-----------

Once you have added headers to your semiwrap configuration in ``pyproject.toml``,
the ``create-yaml`` tool can be used to create an initial YAML file that describes
the header file. Additionally, if a YAML file is already present, it will print
out elements that are in the header but not in the YAML file.

By default it will just print the file contents to stdout. Use the ``--write`` argument
to write the files, but it won't overwrite existing files.

.. _create_imports:

create-imports
--------------

Given a base package and a compiled module within that package, this will
generate contents that contain all of the things exported by the compiled
module. Often it is useful to put this in the ``__init__.py`` of your 
python package.

.. code-block:: sh

    $ semiwrap create-imports rpydemo rpydemo._rpydemo

Use the ``--write`` argument to write the file.

.. _update_init:

update-init
-----------

This does the same thing as create-imports, but it will automatically update
all modules that are specified in ``pyproject.toml``:

.. code-block:: toml

    [tool.semiwrap]
    update_init = ["rpydemo rpydemo._rpydemo"]
