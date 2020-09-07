
#pragma once

#include <vector>

// Testcase: using directive that depends on the template parameter

namespace whatever
{

    template <typename T>
    struct TDependentUsing
    {
        using VectorType = std::vector<T>;

        T getThird(VectorType t)
        {
            return t.at(2);
        }
    };

}; // namespace whatever
