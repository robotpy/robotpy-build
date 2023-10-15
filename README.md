robotpy-build
=============

This is a build tool intended to be generally useful for any python project
that has binary dependencies. It is especially designed to meet the needs
of RobotPy's various wrapper libraries, chiefly around:

* Managing upstream binary dependencies
* Autogenerating pybind11 wrappers around those dependencies
* Building wheels from those generated wrappers

Requires Python 3.8+

Documentation
-------------

Documentation can be found at https://robotpy-build.readthedocs.io/

Author
------

Dustin Spicuzza is the primary author of robotpy-build, but it is the
culmination of many years of experimentation with automated wrapper
generation by members of the RobotPy community.

robotpy-build is available under the BSD 3-clause license.
