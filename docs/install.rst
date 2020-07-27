Installation
============

.. note:: ``robotpy-build`` is a build dependency, not a runtime dependency --
          in otherwords, you only need it to build binary wheels. Once you have
          a wheel, the wheel is usable without ``robotpy-build``

Supported platforms
-------------------

``robotpy-build`` requires Python 3.6 to be installed. Our integration tests
are ran on Ubuntu 18.04, OSX, and Windows.

* Linux and Windows are expected to work in almost any case
* OSX should work, but when depending on shared libraries there are some cases
  where relinking doesn't work

To compile the generated code created by ``robotpy-build``, you must have a
modern C++ compiler that is supported by pybind11.

Install
-------

``robotpy-build`` is distributed on pypi and is installable via pip.

On Linux/OSX, you can install with the following command:

.. code:: sh

    $ pip3 install robotpy-build

On Windows, you can install via:

.. code:: sh

    py -3 -m pip install robotpy-build

pybind11
--------

pybind11 is a header-only C++ library that robotpy-build leverages to easily
bind together Python and C++ code. All robotpy-build projects are built using
a bundled version of pybind11, which is typically a bleeding edge version of
pybind11 with custom patches that have not been accepted upstream yet.

.. warning:: robotpy-build does not use the pybind11 package distributed on
             pypi.
