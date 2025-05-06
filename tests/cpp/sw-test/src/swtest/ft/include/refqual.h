#pragma once

struct RefQuals {

    virtual ~RefQuals() {}

    // pybind11 can bind this, but we have to specify the right
    // ref-qualifier for the trampoline to compile
    virtual int fn1() & {
        return 1;
    }

    // pybind11 cannot bind this, have to do it manually
    virtual int fn2() && {
        return 2;
    }

    // pybind11 cannot bind this, have to do it manually
    int fn3() && {
        return 3;
    }
};

int refquals_fn1(RefQuals &r) {
    return r.fn1();
}

int refquals_fn2(RefQuals &r) {
    return std::move(r).fn2();
}

int refquals_fn3(RefQuals &r) {
    return std::move(r).fn3();
}
