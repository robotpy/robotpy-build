
#pragma once

#include "rpyint.h"

// taken from the pybind11 docs

namespace pybind11 { namespace detail {
    template <> struct type_caster<rpy::rpyint> {
    public:
        /**
         * This macro establishes the name 'inty' in
         * function signatures and declares a local variable
         * 'value' of type inty
         *
         * BUT if you're using a custom type name that doesn't exist,
         * then you need to add a type alias or pybind11-stubgen gets
         * angry at you -- so this has to be a fully qualified name
         */
        PYBIND11_TYPE_CASTER(rpy::rpyint, const_name("rpytest.ft.rpyint"));

        /**
         * Conversion part 1 (Python->C++): convert a PyObject into a inty
         * instance or return false upon failure. The second argument
         * indicates whether implicit conversions should be applied.
         */
        bool load(handle src, bool) {
            /* Extract PyObject from handle */
            PyObject *source = src.ptr();
            /* Try converting into a Python integer value */
            PyObject *tmp = PyNumber_Long(source);
            if (!tmp)
                return false;
            /* Now try to convert into a C++ int */
            value.set(PyLong_AsLong(tmp));
            Py_DECREF(tmp);
            /* Ensure return code was OK (to avoid out-of-range errors etc) */
            return !(value.get() == -1 && !PyErr_Occurred());
        }

        /**
         * Conversion part 2 (C++ -> Python): convert an inty instance into
         * a Python object. The second and third arguments are used to
         * indicate the return value policy and parent object (for
         * ``return_value_policy::reference_internal``) and are generally
         * ignored by implicit casters.
         */
        static handle cast(rpy::rpyint src, return_value_policy /* policy */, handle /* parent */) {
            return PyLong_FromLong(src.get());
        }
    };

    template <> struct type_caster<rpy::rpyint_plus_5> {
    public:
        /**
         * This macro establishes the name 'inty' in
         * function signatures and declares a local variable
         * 'value' of type inty
         */
        PYBIND11_TYPE_CASTER(rpy::rpyint_plus_5, const_name("rpyint_plus_5"));

        /**
         * Conversion part 1 (Python->C++): convert a PyObject into a inty
         * instance or return false upon failure. The second argument
         * indicates whether implicit conversions should be applied.
         */
        bool load(handle src, bool) {
            /* Extract PyObject from handle */
            PyObject *source = src.ptr();
            /* Try converting into a Python integer value */
            PyObject *tmp = PyNumber_Long(source);
            if (!tmp)
                return false;
            /* Now try to convert into a C++ int */
            value.set(PyLong_AsLong(tmp));
            Py_DECREF(tmp);
            /* Ensure return code was OK (to avoid out-of-range errors etc) */
            return !(value.get() == -1 && !PyErr_Occurred());
        }

        /**
         * Conversion part 2 (C++ -> Python): convert an inty instance into
         * a Python object. The second and third arguments are used to
         * indicate the return value policy and parent object (for
         * ``return_value_policy::reference_internal``) and are generally
         * ignored by implicit casters.
         */
        static handle cast(rpy::rpyint_plus_5 src, return_value_policy /* policy */, handle /* parent */) {
            return PyLong_FromLong(src.get());
        }
    };
}} // namespace pybind11::detail