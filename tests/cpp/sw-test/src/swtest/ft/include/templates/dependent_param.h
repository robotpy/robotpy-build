// clang-format off
#pragma once

#include <vector>
#include "dependent_using.h"

// Testcase: template using directive

namespace whatever
{

    template <typename T>
    struct TDependentParam
    {
        T getThird(TDependentUsing<T> t, std::vector<T> v)
        {
            return t.getThird(v);
        }
    };

}; // namespace whatever
