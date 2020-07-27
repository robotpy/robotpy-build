Troubleshooting
===============

Compilation errors
------------------

error: invalid use of incomplete type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pybind11 requires you to use complete types when binding an object. Typically
this means that somewhere in the header there was a forward declaration:

.. code-block:: c++

    class Foo;

Foo is defined in some header, but not the header you're scanning. To fix it,
tell the generator to include the header:

.. code-block:: yaml

    extra_includes:
    - path/to/Foo.h

error: 'SomeEnum' has not been declared
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Often this is referring to a parameter type or a default argument. You can use
the 'param_override' setting for that function to fix it. For example, if you
had the following C++ code:

.. code-block:: c++

    void fnWithEnum(SomeEnum e);

And ``SomeEnum`` was actually ``somens::SomeEnum`` but robotpy-build wasn't
able to automatically determine that. You could fix it like so:

.. code-block:: yaml

    functions:
      fnWithEnum:
        param_override:
          # e is the name of the param
          e:
            # x_type tells the generator to force the type to the specified string
            x_type: "somens::SomeEnum"

error: static assertion failed: Cannot use an alias class with a non-polymorphic type
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pybind11 has a static assert that occurs when an trampoline class is specified
for a class that is a subclass of some other class, but none of its bases have
any virtual functions. This is to prevent 

robotpy-build generates trampoline classes to allow python code to override
virtual functions in C++ classes. robotpy-build isn't always able to detect
when a trampoline isn't appropriate.

When this error occurs, you can force robotpy-build to turn off trampoline classes
for a specific type:

.. code-block:: yaml

   classes:
     X:
       force_no_trampoline: true

Runtime errors
--------------

ImportError: dynamic module does not define module export function (PyInit__XXX)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes this exhibits itself as ``unresolved external symbol PyInit__XXX``.

This error indicates that you compiled a Python C++ module without actually
defining a module. Most likely, you forgot to to add a file which contains
these contents:

.. code-block:: c++

    #include <rpygen_wrapper.hpp>

    RPYBUILD_PYBIND11_MODULE(m) {
        initWrapper(m);
    }

You can of course put other content in here if needed.
