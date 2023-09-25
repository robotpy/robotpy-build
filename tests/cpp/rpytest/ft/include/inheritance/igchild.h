
#pragma once
#include "ichild.h"

namespace inheritance
{

struct IGrandChild final : IChild
{
    /** doc: grandchild::baseAndGrandchild */
    std::string baseAndGrandchild() override
    {
        return "grandchild::baseAndGrandchild";
    }
};

} // namespace inheritance
