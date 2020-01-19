#pragma once

// Base definitions used by all roobtpy-build projects

#include <pybind11/pybind11.h>

namespace py = pybind11;

// Use this to release the gil
typedef py::call_guard<py::gil_scoped_release> release_gil;

// Use this to define your module instead of PYBIND11_MODULE
#define RPYBUILD_PYBIND11_MODULE(variable) PYBIND11_MODULE(RPYBUILD_MODULE_NAME, variable)

#define RPYBUILD_OVERLOAD_PURE_NAME(pyname, ret_type, cname, name, fn, ...) \
    PYBIND11_OVERLOAD_INT(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__) \
    pybind11::pybind11_fail("Tried to call pure virtual function \"" PYBIND11_STRINGIFY(pyname) "::" name "\"");
