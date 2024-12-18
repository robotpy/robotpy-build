#pragma once

namespace n {
    enum class E {
        Item,
    };
};

namespace o {
    struct O {
        O() = default;
        virtual ~O() = default;
    };

    class AnotherC;
};

namespace n::h {
    class C : public o::O {
    public:
        // E is resolved here because it's in the parent namespace but our
        // trampoline was originally in a different namespace and failed
        virtual E fn() { return E::Item; }
    };
};

struct o::AnotherC {
    AnotherC() = default;
    virtual ~AnotherC() = default;
    virtual int fn() { return 1; }
};
