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
key of ``pyproject.toml``.

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
