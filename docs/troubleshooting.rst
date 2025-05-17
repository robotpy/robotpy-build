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

And ``SomeEnum`` was actually ``somens::SomeEnum`` but semiwrap wasn't
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

semiwrap generates trampoline classes to allow python code to override
virtual functions in C++ classes. semiwrap isn't always able to detect
when a trampoline isn't appropriate.

When this error occurs, you can force semiwrap to turn off trampoline classes
for a specific type:

.. code-block:: yaml

   classes:
     X:
       force_no_trampoline: true

error: 'rpygen/__SomeClassName.hpp' file not found
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This occurs when semiwrap has created a trampoline class for a child
class, and it is trying to include the header for the parent trampoline
class. There are several reasons why this might happen.

Sometimes this error occurs because the parent lives in a different package
that you didn't declare a dependency on in ``pyproject.toml``. Add the
dependency and the parent trampoline class should be found.

If the base class is polymorphic in a way that semiwrap wasn't able to
detect, you can force it to be polymorphic:

.. code-block:: yaml

   classes:
     X:
       is_polymorphic: true

Unfortunately, sometimes the base isn't a polymorphic type and you can't
change it. In this case you can turn off the trampoline class for the child
class:

.. code-block:: yaml

   classes:
     X:
       force_no_trampoline: true

build_pyi errors
----------------

Sometimes when running the ``build_pyi`` step, you'll see errors that look
like this.

.. code-block::

    ERROR - def fn(arg: frc::LinearPlantInversionFeedforward<1, 1>) -> None: ...
    ERROR -               ^-- Invalid syntax

What this means is the argument 'arg' is not currently wrapped by pybind11 -- or
if it is, it hasn't been imported by the current python package.

* If it hasn't been wrapped, wrap it
* If it hasn't been imported, import it in your ``__init__.py`` or you can just
  add the other package to the wrapper's ``depends`` list. 


Runtime errors
--------------

ImportError: dynamic module does not define module export function (PyInit__XXX)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes this exhibits itself as ``unresolved external symbol PyInit__XXX``.

This error indicates that you compiled a Python C++ module without actually
defining a module. Most likely, you forgot to to add a file which contains
these contents:

.. code-block:: c++

    #include <semiwrap_init.PACKAGE.NAME.hpp>

    RPYBUILD_PYBIND11_MODULE(m) {
        initWrapper(m);
    }

You can of course put other content in here if needed.
