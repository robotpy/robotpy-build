
Demo Project
============

This walkthrough will take you through all the steps to create a simple
semiwrap project that autogenerates a working wrapper around a C++
class and it's methods.

This demo should work on Linux, OSX, and Windows. Make sure you have
``semiwrap`` installed first!

.. note:: This demo shows building a python wrapper around C++ code that is
          self-contained in this project. However, ``semiwrap`` also 
          supports wrapping externally compiled libraries and inter-package
          shared library dependencies available through ``pypi-pkgconf``

Files + descriptions
--------------------

.. note:: If you're lazy, the files for this demo are checked into the 
          semiwrap repository at ``examples/demo``.

All of the content required for this demo is contained inline below. Let's
start by creating a new directory for your project, and we're going to create
the following files:

pyproject.toml
~~~~~~~~~~~~~~

Projects that use semiwrap must add a ``pyproject.toml`` to the root of
their project as specified in `PEP 518 <https://www.python.org/dev/peps/pep-0518>`_.
This file is used to configure your project. The semiwrap configuration is
in the ``tool.semiwrap`` table, the rest of the file are hatchling configuration
directives to load the semiwrap and hatch-meson plugins.

Comments describing the function of each section can be found inline below.

.. literalinclude:: ../examples/demo/pyproject.toml

.. seealso:: For detailed information about the contents of ``pyproject.toml``
             see :ref:`pyproject`.

meson.build
~~~~~~~~~~~

Semiwrap generates python modules that are built using the ``meson`` build system,
and you must provide your own ``meson.build`` that includes the build files that
semiwrap generates and any other build customizations required for your project.

.. literalinclude:: ../examples/demo/meson.build

swdemo/__init__.py
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # file is empty for now

swdemo/src/demo.cpp
~~~~~~~~~~~~~~~~~~~

This is the (very simple) C++ code that we will wrap so that it can be
called from python.

.. literalinclude:: ../examples/demo/swdemo/src/demo.cpp

swdemo/include/demo.h
~~~~~~~~~~~~~~~~~~~~~~

This is the C++ header file for the code that we're wrapping. In ``pyproject.toml``
we told ``semiwrap`` to parse this file and autogenerate wrappers for it.

For simple C++ code such as this, autogeneration will 'just work' and no other
customization is required. However, certain C++ code (templates and sometimes code
that depends on templated types, and other complex circumstances) will require
providing customization in a YAML file.

.. literalinclude:: ../examples/demo/swdemo/include/demo.h

swdemo/src/main.cpp
~~~~~~~~~~~~~~~~~~~~

Finally, you need to define your pybind11 python module. Custom ``pybind11``
projects would use a ``PYBIND11_MODULE`` macro to define a module, but it's
easier to use the ``SEMIWRAP_PYBIND11_MODULE`` macro which automatically sets
the module name when semiwrap compiles the file.

.. literalinclude:: ../examples/demo/swdemo/src/main.cpp

.. note:: If you wanted to add your own handwritten pybind11 code here, you
          can add it in addition to the ``initWrapper`` call made here. See
          the pybind11 documentation for more details.

Install the project
-------------------

When developing a new project, it's easiest to just install in 'develop' mode
which will build/install everything in the currect directory.

.. code-block:: sh

   $ python3 -m pip install -v -e .

If you've been following our instructions so far, this will fail with an error
similar to this:

.. code-block:: text

   semiwrap.makeplan.PlanError: swdemo._demo failed
   - caused by FileNotFoundError: semiwrap/demo.yml: use `python3 -m semiwrap create-yaml --write` to generate

``semiwrap`` requires all headers listed in ``tool.semiwrap.extension_modules."PACKAGE.NAME".headers``
to have an associated YAML file in the semiwrap directory. You can create them manually,
or just use the following command to autogenerate it.

.. code-block:: sh

   python3 -m semiwrap create-yaml --write

Now there will be a semiwrap generation configuration YAML file at ``semiwrap/demo.yml``:

.. literalinclude:: ../examples/demo/semiwrap/demo.yml

Now if you run the install command again it should build and install the package:

.. code-block:: sh

   $ python3 -m pip install -v -e .

Adjust the project
------------------

As we've currently built the project, the CPython extension will be built 
as ``swdemo._swdemo``. For example:

.. code-block:: pycon

   >>> from swdemo._demo import DemoClass
   >>> DemoClass
   <class 'swdemo._demo.DemoClass'>

While that works, we really would like users to be able to access our module
directly by importing them into ``__init__.py``. The ``semiwrap update-init``
command can automatically add this to specified packages. Ensure that your
``pyproject.toml`` contains the package names in ``update_init``:

.. code-block:: toml

   [tool.semiwrap]
   update_init = ["swdemo swdemo._demo"]

Then run this command:

.. code-block:: sh

   $ python -m semiwrap update-init

This will add the following to your ``__init__.py``:

.. literalinclude:: ../examples/demo/swdemo/__init__.py

Now when we put this in our ``__init__.py``, that allows this to work instead:

.. code-block:: pycon

   >>> from swdemo import DemoClass
   >>> DemoClass
   <class 'swdemo._demo.DemoClass'>

Trying out the project
----------------------

Alright, now that all the pieces are assembled, we can try out our project:

.. code-block:: pycon

    >>> import swdemo
    >>> swdemo.add2(2)
    4
    >>> d = swdemo.DemoClass()
    >>> d.setX(2)
    >>> d.getX()
    2

More Examples
-------------

The integration tests in ``tests/cpp`` contains a several projects that contains
autogenerated wrappers packages and various customizations.
