#pragma once

// Base definitions used by all roobtpy-build projects

#include <pybind11/pybind11.h>

namespace py = pybind11;

// Use this to release the gil
typedef py::call_guard<py::gil_scoped_release> release_gil;

// Use this to define your module instead of PYBIND11_MODULE
#define RPYBUILD_PYBIND11_MODULE(variable) PYBIND11_MODULE(RPYBUILD_MODULE_NAME, variable)

#define RPYBUILD_OVERLOAD_PURE_NAME(pyname, ret_type, cname, name, fn, ...) { \
        PYBIND11_OVERLOAD_INT(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__) \
        std::string __msg("<unknown> does not override required function \"" PYBIND11_STRINGIFY(pyname) "::" name "\""); \
        try { \
            py::gil_scoped_acquire gil; \
            auto obj = py::cast(static_cast<const cname *>(this)); \
            if (obj) { \
                __msg = std::string(py::repr(obj)) + " does not override required function \"" PYBIND11_STRINGIFY(pyname) "::" name "\""; \
            } \
        } catch (std::exception&) {} \
        py::pybind11_fail(__msg); \
    }

