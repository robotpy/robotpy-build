#pragma once

#include "tcrtpfwd.h"

template <typename T>
struct TCrtp : TCrtpFwd<T>
{
    std::string get() override
    {
        return "TCrtp";
    }
};
