
#pragma once

#include "ibase.h"

namespace inheritance
{

struct IChild : IBase
{
    IChild() : IBase(), i(42) {}

    std::string baseAndChild() final
    {
        return "child::baseAndChild";
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
