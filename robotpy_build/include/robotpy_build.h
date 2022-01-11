#pragma once

// Base definitions used by all robotpy-build projects

#include <pybind11/pybind11.h>

namespace py = pybind11;

// Use this to release the gil
typedef py::call_guard<py::gil_scoped_release> release_gil;

// empty trampoline configuration base
namespace rpygen {
struct EmptyTrampolineCfg {};
};

// robotpy-build specific extensions waiting for inclusion into pybind11
namespace rpybuild_ext {

/// Replaces the current Python error indicator with the chosen error, performing a
/// 'raise from' to indicate that the chosen error was caused by the original error
inline void raise_from(PyObject *type, const char *message) {
    // from cpython/errors.c _PyErr_FormatVFromCause
    PyObject *exc, *val, *val2, *tb;
    PyErr_Fetch(&exc, &val, &tb);

    PyErr_NormalizeException(&exc, &val, &tb);
    if (tb != nullptr) {
        PyException_SetTraceback(val, tb);
        Py_DECREF(tb);
    }
    Py_DECREF(exc);

    PyErr_SetString(type, message);
    PyErr_Fetch(&exc, &val2, &tb);
    PyErr_NormalizeException(&exc, &val2, &tb);
    Py_INCREF(val);
    PyException_SetCause(val2, val);
    PyException_SetContext(val2, val);
    PyErr_Restore(exc, val2, tb);
}

/// Sets the current Python error indicator with the chosen error, performing a 'raise from'
/// from the error contained in error_already_set to indicate that the chosen error was
/// caused by the original error. After this function is called error_already_set will
/// no longer contain an error.
inline void raise_from(py::error_already_set& err, PyObject *type, const char *message) {
    err.restore();
    raise_from(type, message);
}

} // namespace rpybuild_ext

// Use this to define your module instead of PYBIND11_MODULE
#define RPYBUILD_PYBIND11_MODULE(variable) PYBIND11_MODULE(RPYBUILD_MODULE_NAME, variable)

// only for use by RPYBUILD_OVERRIDE_PURE_POST_IMPL
template <class T> py::handle __get_handle(const T *this_ptr) {
    auto this_type = py::detail::get_type_info(typeid(T));
    if (!this_type) return py::handle();
    return py::detail::get_object_handle(this_ptr, this_type);
}

#define RPYBUILD_OVERRIDE_CUSTOM_IMPL(ret_type, cname, name, ...)                         \
    do {                                                                                  \
        py::gil_scoped_acquire gil;                                                       \
        py::function override = py::get_override(static_cast<const cname *>(this), name); \
        if (override)                                                                     \
        {                                                                                 \
            return custom_fn(override);                                                   \
        }                                                                                 \
    } while (false)

#define RPYBUILD_OVERRIDE_PURE_POST_IMPL(pyname, cname, name)                                                                          \
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
    py::pybind11_fail(__msg)

#define RPYBUILD_OVERRIDE_PURE_CUSTOM_NAME(pyname, ret_type, cname, name, fn, ...)                      \
    {                                                                                                   \
        RPYBUILD_OVERRIDE_CUSTOM_IMPL(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__);\
        RPYBUILD_OVERRIDE_PURE_POST_IMPL(pyname, PYBIND11_TYPE(cname), name);                           \
    }

#define RPYBUILD_OVERRIDE_PURE_NAME(pyname, ret_type, cname, name, fn, ...)                      \
    {                                                                                            \
        PYBIND11_OVERRIDE_IMPL(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__);\
        RPYBUILD_OVERRIDE_PURE_POST_IMPL(pyname, PYBIND11_TYPE(cname), name);                    \
    }

#define RPYBUILD_OVERRIDE_CUSTOM_NAME(ret_type, cname, name, fn, ...)                               \
    RPYBUILD_OVERRIDE_CUSTOM_IMPL(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__);\
    return cname::fn(__VA_ARGS__)

//
// backwards compat
//

#define RPYBUILD_OVERLOAD_PURE_CUSTOM_NAME(pyname, ret_type, cname, name, fn, ...) \
    RPYBUILD_OVERRIDE_PURE_CUSTOM_NAME(pyname, PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, fn, __VA_ARGS__)
#define RPYBUILD_OVERLOAD_CUSTOM_NAME(ret_type, cname, name, fn, ...) \
    RPYBUILD_OVERRIDE_CUSTOM_NAME(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, fn, __VA_ARGS__)
#define RPYBUILD_OVERLOAD_PURE_NAME(pyname, ret_type, cname, name, fn, ...) \
    RPYBUILD_OVERRIDE_PURE_NAME(pyname, PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, fn, __VA_ARGS__)
