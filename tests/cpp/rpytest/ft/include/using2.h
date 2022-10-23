
#pragma once

namespace u {
template <typename T> struct fancy_list {};

namespace u2 {

struct Using1 {
    using PType = int;

    void fn(PType p1) {}
    void fn(float p2) {}
};

struct Using2 {
    // this would cause an error because of duplicate typename
    // when copied to generated code
    using PType = int;

    void fn(PType p1) {}
    void fn(float p2) {}
};

struct Using3 {
    // this won't compile without a manual typealias insertion
    Using3(fancy_list<int> l) {}
};

} // namespace u2
} // namespace u