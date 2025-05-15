
.. _pyproject:

pyproject.toml
==============

Projects that use semiwrap must add a ``pyproject.toml`` to the root of
their project as specified in `PEP 518 <https://www.python.org/dev/peps/pep-0518>`_.

Because semiwrap is a hatchling plugin, you should add semiwrap and hatchling
to your ``build-system.requires``. You need meson to build the project, so we
recommend also using ``hatch-meson`` to do so.

.. code-block:: toml

   [build-system]
   build-backend = "hatchling.build"
   requires = ["semiwrap", "hatch-meson", "hatchling"]

Projects must include semiwrap specific sections in their pyproject.toml.
semiwrap takes ``pyproject.toml`` and converts it to a python dictionary
using ``toml.load``. The resulting dictionary is converted to the dataclasses
described below.

Required sections:

* :class:`.RobotpyBuildConfig` - base project configuration
* :class:`.DistutilsMetadata` - standard python distutils metadata

Optional sections:

* :class:`.WrapperConfig` - per-package configuration 
* :class:`.StaticLibConfig`
* :class:`.MavenLibDownload` - download per-package maven artifacts
* :class:`.PatchInfo` - patch downloaded sources


.. note:: For a complete example pyproject.toml file, see ``tests/cpp/*/pyproject.toml``


Reference
---------

.. automodule:: semiwrap.config.pyproject_toml
   :members:
   :exclude-members: __init__, Config
