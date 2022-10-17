
#pragma once

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
