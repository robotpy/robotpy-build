#pragma once

#include <vector>

//
// Test anything that can be ignored
//

// function
int fnIgnore() { return 0x1; }

// parameter
int fnIgnoredParam(int x) { return x; }

// class
struct IgnoredClass {};

template <typename T>
struct IgnoredTemplatedClass {};

struct IgnoredClassWithEnum {
    enum AlsoIgnored { Value = 1 };
};

struct ClassWithIgnored {

    // constructor with ignored param
    ClassWithIgnored(int y) {}

    // class function
    int fnIgnore() { return 0x2; }

    // class function parameter
    int fnIgnoredParam(int x, int y) { return x + y; }

    // function with parameter pack
    template <typename... T>
    void fnParamPack(int x, T&&... t) {}

    // twice to make sure it has to be in overloads
    void fnParamPack() {}

    // property
    int ignoredProp = 8;

    // enums
    enum IgnoredInnerEnum {
        Param
    };

    enum InnerEnumWithIgnored {
        Param1 = 1,
        Param2 = 2
    };
};

struct ClassWithIgnoredBase : IgnoredClass {
};

struct ClassWithIgnoredTemplateBase : IgnoredTemplatedClass<std::vector<int>> {
};

// enums
enum IgnoredEnum {
    Original1 = 1
};

enum EnumWithIgnored {
    NotIgnored = 1,
    Ignored = 2,
};