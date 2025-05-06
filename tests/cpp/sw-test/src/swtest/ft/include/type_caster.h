#pragma once

#include <vector>

// only works if pybind11/stl.h is included -- our type caster detection
// mechanism should include it automatically
std::vector<int> get123()
{
    std::vector<int> v{1, 2, 3};
    return v;
}
