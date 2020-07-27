Developer tips
==============

Over time, we've collected a number of tips and best practices for working
with robotpy-build projects which will save you lots of time -- particularly
when dealing with very large projects. 

Build using develop mode
------------------------

For rapid iteration development, we highly recommend using ``python3 setup.py
develop`` to build your project. This allows in-tree editing of python files
and leads to faster results if you're disciplined.

Use parallel builds
-------------------

While setuptools does not support parallel builds, robotpy-build will compile
things in parallel if you define the environment variable ``RPYBUILD_PARALLEL=1``.

.. code-block:: sh

    $ RPYBUILD_PARALLEL=1 python3 setup.py develop

Partial code generation
-----------------------

When developing wrappers of very large projects, the wrapper regeneration step
can take a very long time. Often you find that you only want to modify a single
file. You can define a YAML file and tell robotpy-build to only regenerate the
output for that single file, instead of scanning all files and regenerating
everything.

Create a filter.yml:

.. code-block:: yaml

    # the names in this list correspond to the keys in your 'generate' section
    only_generate:
    - SendableChooser

Then run your build like so:

.. code-block:: bash

    $ RPYBUILD_GEN_FILTER=filter.yml python setup.py develop


Use ccache
----------

.. note:: ccache does not support Visual Studio

If you create a large robotpy-build based project, you'll notice that your
build times can be *really* long. This occurs because robotpy-build uses
pybind11 for connecting C++ and Python code, and pybind11 relies heaviliy
on C++ templates and other modern C++ techniques which cause build times to
take a really long time.

From ccache's website:

    Ccache (or “ccache”) is a compiler cache. It speeds up recompilation by
    caching previous compilations and detecting when the same compilation is
    being done again. 

This can dramatically improve your compile times if you're just changing
a small portions of your project.

Once you install ccache, define these environment variables:

.. code-block:: bash

    export RPYBUILD_PARALLEL=1
    export CC="ccache gcc"
    export CXX="ccache g++"
    export GCC_COLORS=1

The first one will make robotpy-build compile in parallel. The second tells
setuptools to use ccache, and the third makes error output nice when using
ccache.

