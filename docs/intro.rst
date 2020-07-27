About this project
==================

The RobotPy project maintains Python wrappers around many different C++
libraries to allow its users to use Python for the FIRST Robotics Competition.
It was much too work to create/maintain handwritten wrappers around these
libraries, and other tools in the python ecosystem did not meet our needs.

robotpy-build was created to automate large parts of the work required
to maintain these wrappers. If you have this problem too, we hope that
robotpy-build will be useful for you as well.

Goals
-----

A primary goal of robotpy-build is to make it really simple to define and build
python wrappers for C++ code using pybind11. To make that possible, it also
bundles these capabilities:

* Manages native/binary C/C++ dependencies via pypi compatible packages
* Autogenerate python wrappers around the native code by parsing C++ header files,
  including those that contain modern C++ features
* Support extensive customization of the wrappers when the autogeneration fails
* Builds normal python wheels from the generated and handwritten code that can
  be installed by pip and imported as a normal python package
* robotpy-build projects can depend on native/binary libraries installed by
  other robotpy-build projects

robotpy-build is intended to be a generally useful tool for any python project
that has C/C++ dependencies. If you find that isn't the case, please report a
bug on github.

Non-goals
---------

* robotpy-build built wheels do not currently conform to the manylinux
  specification as it prohibits dependencies outside of the wheel
* We don't intend to build wrappers around libraries installed on your
  system
