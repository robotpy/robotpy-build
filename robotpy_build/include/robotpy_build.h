#pragma once

// Base definitions used by all roobtpy-build projects

#include <pybind11/pybind11.h>

namespace py = pybind11;

// Use this to release the gil
typedef py::call_guard<py::gil_scoped_release> release_gil;

// Use this to define your module instead of PYBIND11_MODULE
#define RPYBUILD_PYBIND11_MODULE(variable) PYBIND11_MODULE(RPYBUILD_MODULE_NAME, variable)

// only for use by RPYBUILD_OVERLOAD_PURE_POST_INT
template <class T> py::handle __get_handle(const T *this_ptr) {
    auto this_type = py::detail::get_type_info(typeid(T));
    if (!this_type) return py::handle();
    return py::detail::get_object_handle(this_ptr, this_type);
}

#define PYBIND11_OVERLOAD_CUSTOM_INT(ret_type, cname, name, ...)                          \
    {                                                                                     \
        py::gil_scoped_acquire gil;                                                       \
        py::function overload = py::get_overload(static_cast<const cname *>(this), name); \
        if (overload)                                                                     \
        {                                                                                 \
            return custom_fn(overload);                                                   \
        }                                                                                 \
    }

#define RPYBUILD_OVERLOAD_PURE_POST_INT(pyname, cname, name)                                                                           \
    std::string __msg("<unknown> does not override required function \"" PYBIND11_STRINGIFY(pyname) "::" name "\"");                   \
    try                                                                                                                                \
    {                                                                                                                                  \
        py::gil_scoped_acquire gil;                                                                                                    \
        auto self = __get_handle(static_cast<const cname *>(this));                                                                    \
        if (self)                                                                                                                      \
        {                                                                                                                              \
            __msg = std::string(py::repr(self)) + " does not override required function \"" PYBIND11_STRINGIFY(pyname) "::" name "\""; \
        }                                                                                                                              \
    }                                                                                                                                  \
    catch (std::exception &)                                                                                                           \
    {                                                                                                                                  \
    }                                                                                                                                  \
    py::pybind11_fail(__msg);

#define RPYBUILD_OVERLOAD_PURE_CUSTOM_NAME(pyname, ret_type, cname, name, fn, ...)                     \
    {                                                                                                  \
        PYBIND11_OVERLOAD_CUSTOM_INT(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__) \
        RPYBUILD_OVERLOAD_PURE_POST_INT(pyname, cname, name)                                           \
    }

#define RPYBUILD_OVERLOAD_PURE_NAME(pyname, ret_type, cname, name, fn, ...)                     \
    {                                                                                           \
        PYBIND11_OVERLOAD_INT(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__) \
        RPYBUILD_OVERLOAD_PURE_POST_INT(pyname, cname, name)                                    \
    }

#define RPYBUILD_OVERLOAD_CUSTOM_NAME(ret_type, cname, name, fn, ...)                              \
    PYBIND11_OVERLOAD_CUSTOM_INT(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__) \
    return cname::fn(__VA_ARGS__)
