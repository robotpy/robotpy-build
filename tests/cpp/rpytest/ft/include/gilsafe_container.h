
#pragma once

#include <gilsafe_object.h>

class GilsafeContainer {
    rpy::gilsafe_object m_o;
public:
    void assign(rpy::gilsafe_object o) {
        m_o = o;
    }

    static void check() {
        auto c = std::make_unique<GilsafeContainer>();

        py::gil_scoped_acquire a;

        py::object v = py::none();

        {
            py::gil_scoped_release r;
            c->assign(v);
            c.reset();
        }
    }

};
