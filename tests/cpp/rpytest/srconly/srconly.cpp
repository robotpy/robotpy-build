
#include <robotpy_build.h>

int srconly_fn(int val) {
    return val - 0x42;
}

RPYBUILD_PYBIND11_MODULE(m) {
    m.def("srconly_fn", &srconly_fn);
}