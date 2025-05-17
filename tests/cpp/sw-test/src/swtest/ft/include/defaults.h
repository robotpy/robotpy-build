#pragma once

#include <vector>

int fnSimpleDefaultParam(int i, int j = 3) { return i + j; }

std::vector<int> fnEmptyDefaultParam(std::vector<int> p = {}) { return p; }

struct NotImportant {};

struct HasDefaults {
    static constexpr unsigned int kDefVal = 1234;

    unsigned int getVal(unsigned int v = kDefVal) {
        return v;
    }

    // test a more complex default to ensure stubgen can handle it
    void objectDefault(NotImportant n = NotImportant{}) {}
};