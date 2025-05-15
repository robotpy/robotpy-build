Installation
============

This describes how to install the ``semiwrap`` development tool if you 
need to use the tooling to develop packages that depend on ``semiwrap``.

.. note:: ``semiwrap`` is a build dependency, not a runtime dependency --
          in otherwords, you only need it to build binary wheels. Once you have
          a wheel, the wheel is usable without ``semiwrap``

          When building a wheel that requires ``semiwrap``, you do not need to
          install semiwrap separately unless you have build isolation disabled
          for your build tool. Just make sure that ``semiwrap`` is in the
          ``build-requires`` section of ``pyproject.toml``.

Supported platforms
-------------------

``semiwrap`` requires a minimum of Python 3.8 to be installed, and should
work on Linux, macOS, and Windows. To compile the generated code created by
``semiwrap``, you must have a modern C++ compiler that is supported by pybind11.

Install
-------

To run the semiwrap development tooling, you should install ``semiwrap`` from
pypi using your preferred python installer program.

On Linux/OSX, you can install with the following command:

.. code:: sh

    $ pip3 install semiwrap

On Windows, you can install via:

.. code:: sh

    py -3 -m pip install semiwrap

Once ``semiwrap`` is installed you can run the tools via one of the following:

.. code:: sh

   semiwrap

   python -m semiwrap

pybind11
--------

pybind11 is a header-only C++ library that semiwrap leverages to easily
bind together Python and C++ code. All semiwrap projects are built using
a bundled version of pybind11, which is typically a bleeding edge version of
pybind11 with custom patches that have not been accepted upstream yet.

.. warning:: semiwrap does not currently use the pybind11 package distributed
             on pypi.
