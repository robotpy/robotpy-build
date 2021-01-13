
.. _pyproject:

setup.py and pyproject.toml
===========================

setup.py
--------

Projects that use robotpy-build must use the setup function provided by
robotpy-build. Your project's setup.py should look like this:

.. code-block:: py

   #!/usr/bin/env python3
   from robotpy_build.setup import setup
   setup()

pyproject.toml
--------------

Projects that use robotpy-build must add a ``pyproject.toml`` to the root of
their project as specified in `PEP 518 <https://www.python.org/dev/peps/pep-0518>`_.

It is recommended that projects include the standard ``build-system`` section to
tell pip to install robotpy-build (and any other dependencies) before starting
a build.

.. code-block:: toml

   [build-system]
   requires = ["robotpy-build>=2020.1.0,<2021.0.0"]

Projects must include robotpy-build specific sections in their pyproject.toml.
robotpy-build takes ``pyproject.toml`` and converts it to a python dictionary
using ``toml.load``. The resulting dictionary is given to pydantic, which
validates the structure of the dictionary against the objects described below.

Required sections:

* :class:`.RobotpyBuildConfig` - base project configuration
* :class:`.DistutilsMetadata` - standard python distutils metadata

Optional sections:

* :class:`.WrapperConfig` - per-package configuration 
* :class:`.StaticLibConfig`
* :class:`.MavenLibDownload` - download per-package maven artifacts
* :class:`.PatchInfo` - patch downloaded sources


.. note:: For a complete example pyproject.toml file, see ``tests/cpp/pyproject.toml.tmpl``

.. _pyproject_overrides:

Overrides
---------

You can define 'override' sections that will be grafted onto the configuration
if they match a particular platform. For example, to change the dependencies
for a wrapper section on Windows:

.. code-block:: toml

   [tool.robotpy-build.wrappers."PACKAGENAME".override.os_windows]
   depends = ["windows-thing"]

Any element in the robotpy-build section of pyproject.toml can be overridden
by specifying the identical section as '.override.KEYNAME'. If the key matches
the current configuration, the override will be written to the original section.
The matched keys are generated at runtime. Current supported platform override
keys are:

* ``arch_{platform_arch}``
* ``os_{platform_os}``
* ``platform_{platform_os}_{platform_arch}``

To get information about the current platform, you can run:

.. code-block:: sh

   robotpy-build platform-info

There is a rudimentary tool that can be used to apply overrides to a TOML
file and print the resulting TOML out:

.. code-block:: sh

   python3 -m robotpy_build.overrides FILENAME KEY

.. _platforms:

Current supported platform/os/arch combinations are:

* OS: windows/osx/linux
* Arch: x86/x86-64/armv7l/aarch64

For ARM linux distributions we support:

* armv7l + nilrt (RoboRIO)
* armv7l + raspbian (Raspbian 10)
* aarch64 + bionic (Ubuntu 18.04)

Reference
---------

.. automodule:: robotpy_build.pyproject_configs
   :members:
   :exclude-members: __init__, Config
