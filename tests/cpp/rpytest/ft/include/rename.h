#pragma once

//
// Test anything that can be renamed
//

// function
int fnOriginal() { return 0x1; }

// parameter
int fnRenamedParam(int x) { return x; }

// class
struct OriginalClass {
    // constructor
    OriginalClass() = default;
    explicit OriginalClass(int prop) : originalProp(prop) {};

    // class function
    int fnOriginal() { return 0x2; }

    // class function parameter
    int fnRenamedParam(int x) { return x; }

    int fnAutoRenamed(int from) { return from; }

    int getProp() { return originalProp; }
    void setProp(int p) { originalProp = p; }

    // property
    int originalProp = 8;

    // enums
    enum ClassOriginalEnum {
        Param1 = 1
    };

};

// enums
enum OriginalEnum {
    Original1 = 1
};
