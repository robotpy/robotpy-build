#pragma once

#include <utility>

struct VirtualComma
{
    struct RVal {};

    virtual ~VirtualComma() {}

    virtual std::pair<int, int> getTwoTwo()
    {
        return std::pair<int, int>{1, 2};
    }

    // ensures that RVal is recognized as VirtualComma::RVal
    virtual RVal getRval() {
        return RVal{};
    }

    int getRval(int) { return 1; }
};