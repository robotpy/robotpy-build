
#include <rpygen_wrapper.hpp>

RPYBUILD_PYBIND11_MODULE(m)
{
    initWrapper(m);

    m.def("raise_from", []() {
        PyErr_SetString(PyExc_ValueError, "inner");
        rpybuild_ext::raise_from(PyExc_ValueError, "outer");
        throw py::error_already_set();
    });

    m.def("raise_from_already_set", []() {
        try {
            PyErr_SetString(PyExc_ValueError, "inner");
            throw py::error_already_set();
        } catch (py::error_already_set& e) {
            rpybuild_ext::raise_from(e, PyExc_ValueError, "outer");
            throw py::error_already_set();
        }
    });
}