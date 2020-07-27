Platform-specific considerations
================================

cross-compilation
-----------------

We have successfully used `crossenv <https://github.com/benfogle/crossenv>`_ to
cross-compile python modules. For an example set of dockerfiles used to compile
for the RoboRIO platform, see the `robotpy-cross-docker <https://github.com/robotpy/robotpy-cross-docker>`_
project.

macOS
-----

macOS handles library files differently than Windows or Linux. In particular,
macOS will not automatically find and link libraries at runtime. Rather,
libraries need to be explicitly linked beforehand. On Linux/Windows, if your
dependency is not specified explcitly, but you import the dependency before
importing your package, it often works without complaining. **This is not the
case on OSX**.

This presents a special challenge when repackaging libraries to be shipped
in wheels, particularly when linking to libraries installed by other wheels.
robotpy-build provides automatic relinking support for libraries that are
installed via other robotpy-build created wheels, provided that you specify
your dependencies explcitly.

External libraries required must always be defined by ``depends``, even if
they are indirect dependencies.

.. code:: toml

    [tool.robotpy-build.wrappers."PACKAGENAME"]
    depends = ["ntcore"]

If you forget an external dependency, the library won't load and a linking 
error will occur at runtime when your package is imported.
