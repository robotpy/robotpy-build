
.. _type_casters:

Type Casters
============

Most of the time, pybind11 is able to figure out how to convert C++ to Python
types and back, especially classes that are explicitly wrapped. However, some
types (such as STL containers) are converted indirectly and require special
"type casters" to be included in your wrapper code.

Using type casters
------------------

When parsing a header, robotpy-build will match the types found against its
list of type casters. If found, it will automatically add an include directive
for the header that contains the type caster. robotpy-build contains support
for the STL type casters that come with pybind11 (vector, function, map, etc).

Sometimes the autodetection will fail because a type is hidden in some way. You
can specify the missing types on a per-class basis. For example, if ``std::vector``
is aliased and your class uses it:

.. code-block:: yaml

    classes:
      MyClass:
        force_type_casters:
        - std::vector

Custom type casters
-------------------

In some rare cases, you may need to create your own custom type casters. We
won't cover that here, refer to the :std:doc:`pybind11 documentation for custom type casters <pybind11:advanced/cast/custom>`
instead.

However, once you have a custom type caster, here's what you need to do to
automatically include it in a robotpy-build project.

1. Create a header file and put the type caster in that header file. It should
   be in one of your project's python packages.

2. Add a section to ``pyproject.toml``

   .. code-block:: toml

      [tool.robotpy-build.wrappers."package_name".type_casters]
      "header_name.h" =    ["somens::SomeType"]

   This directive will cause robotpy-build's autogenerator to automatically
   include ``header_name.h`` whenever it notices ``SomeType`` in a file. This
   allows pybind11 to use it. The type specification is a list, so if there 
   are multiple types covered in the same header, just specify all the types.
   However, most of the time it is preferred to put type casters for separate
   types in separate files.

.. warning:: Because type casters are included at compile time, if you change 
             a custom type caster in a project you should recompile all
             dependent projects as well, otherwise undefined behavior may occur.