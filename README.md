robotpy-build
=============

This is a build tool designed to meet the needs of RobotPy's various wrapper
libraries build needs, chiefly around:

* Managing upstream binary dependencies
* Autogenerating pybind11 wrappers around those dependencies
* Building wheels from those generated wrappers

Requires Python 3.6+

Workflow
--------

There are two types of generated artifacts from RobotPy wrapper library
projects:

* sdist - This should contain enough information to build a wheel
  * This is NOT intended to be usable offline, because upstream artifacts
    can get to be fairly large
* wheel - Platform specific build installable via pip
  * Should contain headers and libraries necessary for other projects
    to build from it

Eventual goal is to support cross-compilation somehow so we can build
various types of artifacts via CI

Usage
-----

TODO: This tool is still very much under development

See [docs/wrapping.md](docs/wrapping.md) for details on writing your
own wrapped project.