Developer tips
==============

Over time, we've collected a number of tips and best practices for working
with semiwrap projects which will save you lots of time -- particularly
when dealing with very large projects. 

Use editable installation
-------------------------

It is highly recommended to use editable installations when developing your
semiwrap based projects. This allows in-tree editing of python files and can
allow you to take advantage of meson's incremental compilation when making
small modifications.

See the `pypa documentation <https://packaging.python.org/en/latest/guides/distributing-packages-using-setuptools/#working-in-development-mode>`_
for more information.

Use ccache
----------

If you create a large semiwrap based project, you'll notice that your
build times can be *really* long. This occurs because semiwrap uses
pybind11 for connecting C++ and Python code, and pybind11 relies heaviliy
on C++ templates and other modern C++ techniques which cause build times to
take a really long time.

From ccache's website:

    Ccache (or “ccache”) is a compiler cache. It speeds up recompilation by
    caching previous compilations and detecting when the same compilation is
    being done again. 

This can dramatically improve your compile times if you're just changing
a small portions of your project. meson will automatically use ccache if
it is installed.
