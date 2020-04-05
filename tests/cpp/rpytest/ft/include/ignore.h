#pragma once

//
// Test anything that can be ignored
//

// function
int fnIgnore() { return 0x1; }

// parameter
int fnIgnoredParam(int x) { return x; }

// class
struct IgnoredClass {};

struct ClassWithIgnored {

    // class function
    int fnIgnore() { return 0x2; }

    // class function parameter
    int fnIgnoredParam(int x, int y) { return x + y; }

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

// enums
enum IgnoredEnum {
    Original1 = 1
};

enum EnumWithIgnored {
    NotIgnored = 1,
    Ignored = 2,
};