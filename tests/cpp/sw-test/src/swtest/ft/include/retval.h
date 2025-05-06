#pragma once

class RetvalClass {
public:

    enum Retval {
        Val1,
        Val2,
    };

    Retval get() { return Val1; }

    // need an overload to trigger the bug
    Retval get(int i) { return Val2; }

};
