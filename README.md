semiwrap
========

semiwrap is a build tool that makes it simpler to wrap C/C++ libraries with
pybind11 by automating large portions of the wrapping process and handling some
of the more complex aspects of creating pybind11 based wrappers (especially with
trampolines to allow inheriting from C++ classes from Python).

semiwrap includes a hatchling plugin that autogenerates `meson.build` files that
can be built using meson, and those build files parse your wrapped headers and
generate/compile pybind11 based wrappers into python extension modules. 

Requires Python 3.8+

Documentation
-------------

Documentation can be found at https://semiwrap.readthedocs.io/

Author
------

Dustin Spicuzza is the primary author of semiwrap.

Semiwrap is a direct decendant of the robotpy-build project, and is culmination
of many years of experimentation with automated wrapper generation by members of
the RobotPy community.

semiwrap is available under the BSD 3-clause license.
