#pragma once

#include <utility>

struct VirtualComma
{
    virtual ~VirtualComma() {}

    virtual std::pair<int, int> getTwoTwo()
    {
        return std::pair<int, int>{1, 2};
    }
};