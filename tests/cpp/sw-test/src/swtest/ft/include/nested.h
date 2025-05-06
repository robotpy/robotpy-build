
#pragma once

#include <vector>

struct OuterNested {

    struct InnerNested {
        void fn() {}
    };

    struct IgnoredNested {};

    // bug where InnerNested needs to be in binding scope
    OuterNested(std::vector<InnerNested> i) {}

    InnerNested &getInner() {
        return in;
    }

private:

    // lol bug
    struct InnerPrivate {};
    
    InnerNested in;
};
