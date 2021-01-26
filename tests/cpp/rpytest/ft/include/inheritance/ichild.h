// clang-format off
#pragma once

#include "ibase.h"

namespace inheritance
{

struct IChild : IBase
{
    IChild() : IBase(), i(42) {}

    std::string baseAndChild() override
    {
        return "child::baseAndChild";
    }

    std::string baseAndChildFinal() final
    {
        return "child::baseAndChildFinal";
    }

    int getI() const
    {
        return i;
    }

protected:
    int i;
};

struct IFinal final
{
};

} // namespace inheritance
