
#pragma once

namespace u {
template <typename T> struct fancy_list {};

// forward declaration
struct FwdDecl;

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

struct Using4 {
    // this won't be resolved because different namespace
    int getX(const FwdDecl&);
};

struct Using5a {
    virtual ~Using5a() {}
    void fn(int arg) {}
};

struct Using5b : Using5a {
    // this collides but isn't picked up without interpreting the using
    using Using5a::fn;
    void fn(bool arg) {}
};

} // namespace u2
} // namespace u