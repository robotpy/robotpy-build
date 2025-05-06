#pragma once

// Base definitions used by all semiwrap projects

#include <pybind11/pybind11.h>

namespace py = pybind11;

// Use this to release the gil
typedef py::call_guard<py::gil_scoped_release> release_gil;

// empty trampoline configuration base
namespace swgen {
struct EmptyTrampolineCfg {};
};

#define SEMIWRAP_BAD_TRAMPOLINE \
    "has an abstract trampoline -- and they must never be abstract! One of " \
    "the generated override methods doesn't match the original class or its " \
    "bases, or is missing. You will need to provide method and/or param " \
    "overrides for that method. It is likely the following compiler error " \
    "messages will tell you which one it is."


// only for use by SEMIWRAP_OVERRIDE_PURE_POST_IMPL
template <class T> py::handle __get_handle(const T *this_ptr) {
    auto this_type = py::detail::get_type_info(typeid(T));
    if (!this_type) return py::handle();
    return py::detail::get_object_handle(this_ptr, this_type);
}

#define SEMIWRAP_OVERRIDE_CUSTOM_IMPL(ret_type, cname, name, ...)                         \
    do {                                                                                  \
        py::gil_scoped_acquire gil;                                                       \
        py::function override = py::get_override(static_cast<const cname *>(this), name); \
        if (override)                                                                     \
        {                                                                                 \
            return custom_fn(override);                                                   \
        }                                                                                 \
    } while (false)

#define SEMIWRAP_OVERRIDE_PURE_POST_IMPL(pyname, cname, name)                                                                          \
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
    {                                                                                                                                  \
        py::gil_scoped_acquire gil;                                                                                                    \
        py::pybind11_fail(__msg);                                                                                                       \
    }

#define SEMIWRAP_OVERRIDE_PURE_CUSTOM_NAME(pyname, ret_type, cname, name, fn, ...)                      \
    {                                                                                                   \
        SEMIWRAP_OVERRIDE_CUSTOM_IMPL(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__);\
        SEMIWRAP_OVERRIDE_PURE_POST_IMPL(pyname, PYBIND11_TYPE(cname), name);                           \
    }

#define SEMIWRAP_OVERRIDE_PURE_NAME(pyname, ret_type, cname, name, fn, ...)                      \
    {                                                                                            \
        PYBIND11_OVERRIDE_IMPL(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__);\
        SEMIWRAP_OVERRIDE_PURE_POST_IMPL(pyname, PYBIND11_TYPE(cname), name);                    \
    }

#define SEMIWRAP_OVERRIDE_CUSTOM_NAME(ret_type, cname, name, fn, ...)                               \
    SEMIWRAP_OVERRIDE_CUSTOM_IMPL(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__);\
    return cname::fn(__VA_ARGS__)

//
// backwards compat
//

#define SEMIWRAP_OVERLOAD_PURE_CUSTOM_NAME(pyname, ret_type, cname, name, fn, ...) \
    SEMIWRAP_OVERRIDE_PURE_CUSTOM_NAME(pyname, PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, fn, __VA_ARGS__)
#define SEMIWRAP_OVERLOAD_CUSTOM_NAME(ret_type, cname, name, fn, ...) \
    SEMIWRAP_OVERRIDE_CUSTOM_NAME(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, fn, __VA_ARGS__)
#define SEMIWRAP_OVERLOAD_PURE_NAME(pyname, ret_type, cname, name, fn, ...) \
    SEMIWRAP_OVERRIDE_PURE_NAME(pyname, PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, fn, __VA_ARGS__)
