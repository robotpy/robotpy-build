
#pragma once
#include "ichild.h"

namespace inheritance
{

struct IGrandChild final : IChild
{
    std::string baseAndGrandchild() override
    {
        return "grandchild::baseAndGrandchild";
    }
};

} // namespace inheritance
