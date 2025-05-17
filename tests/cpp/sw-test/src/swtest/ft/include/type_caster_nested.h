
#pragma once

#include <functional>
#include <vector>

struct NestedTypecaster
{
    // only works if pybind11/stl.h and functional.h is included -- our type
    // caster detection mechanism should include it automatically
    void callWithList(std::function<void(std::vector<int>)> fn)
    {
        std::vector<int> v;
        v.push_back(1);
        v.push_back(2);
        fn(v);
    }
};