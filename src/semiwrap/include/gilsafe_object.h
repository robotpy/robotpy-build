
#pragma once

#include <pybind11/pybind11.h>

namespace py = pybind11;

// Py_IsFinalizing is public API in 3.13
#if PY_VERSION_HEX < 0x030D0000
#define Py_IsFinalizing _Py_IsFinalizing
#endif

namespace semiwrap {

/*
    This object holds a python object, and can be stored in C++ containers that
    aren't pybind11 aware.

    It is very inefficient -- it will acquire and release the GIL each time
    a move/copy operation occurs! You should only use this object type as a
    last resort.

    Assigning, moves, copies, and destruction acquire the GIL; only converting
    this back into a python object requires holding the GIL.
*/
template <typename T>
class gilsafe_t final {
    py::object o;

public:

    //
    // These operations require the caller to hold the GIL
    //

    // copy conversion
    operator py::object() const & {
        return o;
    }

    // move conversion
    operator py::object() const && {
        return std::move(o);
    }

    //
    // These operations do not require the caller to hold the GIL
    //

    gilsafe_t() = default;

    ~gilsafe_t() {
        if (o) {
            // If the interpreter is alive, acquire the GIL, otherwise just leak
            // the object to avoid a crash
            if (!Py_IsFinalizing()) {
                py::gil_scoped_acquire lock;
                o.dec_ref();
            }

            o.release();
        }
    }

    // Copy constructor; always increases the reference count
    gilsafe_t(const gilsafe_t &other) {
        py::gil_scoped_acquire lock;
        o = other.o;
    }

    // Copy constructor; always increases the reference count
    gilsafe_t(const py::object &other) {
        py::gil_scoped_acquire lock;
        o = other;
    }

    gilsafe_t(const py::handle &other) {
        py::gil_scoped_acquire lock;
        o = py::reinterpret_borrow<py::object>(other);
    }

    // Move constructor; steals object from ``other`` and preserves its reference count
    gilsafe_t(gilsafe_t &&other) noexcept : o(std::move(other.o)) {}

    // Move constructor; steals object from ``other`` and preserves its reference count
    gilsafe_t(py::object &&other)  noexcept : o(std::move(other)) {}

    // copy assignment
    gilsafe_t &operator=(const gilsafe_t& other) {
        if (!o.is(other.o)) {
            py::gil_scoped_acquire lock;
            o = other.o;
        }
        return *this;
    }

    // move assignment
    gilsafe_t &operator=(gilsafe_t&& other) noexcept {
        if (this != &other) {
            py::gil_scoped_acquire lock;
            o = std::move(other.o);
        }
        return *this;
    }

    explicit operator bool() const {
        return (bool)o;
    }
};

// convenience alias
using gilsafe_object = gilsafe_t<py::object>;

} // namespace semiwrap



PYBIND11_NAMESPACE_BEGIN(PYBIND11_NAMESPACE)
PYBIND11_NAMESPACE_BEGIN(detail)

template <typename T>
struct type_caster<semiwrap::gilsafe_t<T>> {
    bool load(handle src, bool convert) {
        value = src;
        return true;
    }

    static handle cast(const handle &src, return_value_policy /* policy */, handle /* parent */) {
        return src.inc_ref();
    }

    PYBIND11_TYPE_CASTER(semiwrap::gilsafe_t<T>, handle_type_name<T>::name);
};

template <typename T>
struct handle_type_name<semiwrap::gilsafe_t<T>> {
    static constexpr auto name = handle_type_name<T>::name;
};

PYBIND11_NAMESPACE_END(detail)
PYBIND11_NAMESPACE_END(PYBIND11_NAMESPACE)
