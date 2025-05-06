
#pragma once

#include <vector>

// Testcase: using directive that depends on the template parameter
// - but we autodetect it

namespace whatever
{

    template <typename T>
    struct TDependentUsing2
    {
        using VectorType = std::vector<T>;

        T getThird(VectorType t)
        {
            return t.at(2);
        }

        // the overload + template here prevents auto-resolving the parameter
        // without explicit handling of this case
        T getThird(std::function<VectorType()> fn)
        {
            auto v = fn();
            return v.at(2);
        }
    };

}; // namespace whatever
