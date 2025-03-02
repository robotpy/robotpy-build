semiwrap
========

This is a build tool intended to be generally useful for any python project
that has binary dependencies. It is especially designed to meet the needs
of RobotPy's various wrapper libraries, chiefly around:

* Managing upstream binary dependencies
* Autogenerating pybind11 wrappers around those dependencies
* Building wheels from those generated wrappers

Requires Python 3.8+

Documentation
-------------

Documentation can be found at https://semiwrap.readthedocs.io/

Author
------

Dustin Spicuzza is the primary author of semiwrap.

Semiwrap is a direct decendant of the robotpy-build project, and is
culmination of many years of experimentation with automated wrapper
generation by members of the RobotPy community.

semiwrap is available under the BSD 3-clause license.
